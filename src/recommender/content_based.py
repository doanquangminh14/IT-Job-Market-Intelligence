import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
import joblib
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data_cleaning.skill_canonical import (
    CANONICAL_SKILL_MAP,
    extract_skills_from_text
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.parquet")
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "models")


class ContentBasedRecommender:
    """
    Hệ thống gợi ý việc làm dựa trên nội dung (Content-Based Filtering):
    - Sử dụng Weighted TF-IDF (Chức danh x3, Kỹ năng x4, Mô tả x1).
    - Đo độ tương đồng qua Cosine Similarity.
    - Two-Stage Filtering: Lọc theo Kinh nghiệm, Thành phố, Mức lương.
    - Phân tích khoảng cách kỹ năng (Skill Gap Analysis: Đã có vs Còn thiếu).
    - So khớp chuyên sâu 1:1 giữa CV và Công việc cụ thể.
    """

    def __init__(
        self,
        max_features: int = 10000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
        model_dir: str = DEFAULT_MODEL_DIR
    ):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.model_dir = model_dir
        
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[Any] = None
        self.jobs_df: Optional[pd.DataFrame] = None
        self.job_id_to_idx: Dict[str, int] = {}
        self.idx_to_job_id: Dict[int, str] = {}

    @staticmethod
    def build_content_soup(row: pd.Series) -> str:
        """Tạo chuỗi văn bản tổng hợp có gán trọng số cho từng công việc."""
        title = str(row.get('title', '')) if pd.notnull(row.get('title')) else ''
        skills = str(row.get('required_skills', '')) if pd.notnull(row.get('required_skills')) else ''
        desc = str(row.get('description_clean', '')) if pd.notnull(row.get('description_clean')) else ''
        # Trọng số: Title x3, Skills x4, Description x1
        soup = f"{title} {title} {title} {skills} {skills} {skills} {skills} {desc}"
        return soup.strip()

    def fit(self, jobs_df: pd.DataFrame, save_model: bool = True) -> "ContentBasedRecommender":
        """
        Huấn luyện TF-IDF trên tập dữ liệu việc làm và lưu mô hình vào data/models/.
        """
        self.jobs_df = jobs_df.copy().reset_index(drop=True)
        
        # Đảm bảo có content_soup
        if 'content_soup' not in self.jobs_df.columns:
            self.jobs_df['content_soup'] = self.jobs_df.apply(self.build_content_soup, axis=1)
            
        # Ánh xạ index <-> job_id
        self.job_id_to_idx = {str(jid): idx for idx, jid in enumerate(self.jobs_df['job_id'])}
        self.idx_to_job_id = {idx: str(jid) for idx, jid in enumerate(self.jobs_df['job_id'])}
        
        print(f" Đang huấn luyện TF-IDF ({self.max_features:,} features, n-gram {self.ngram_range})...")
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.jobs_df['content_soup'])
        print(f" Huấn luyện hoàn tất: {self.tfidf_matrix.shape[0]:,} việc làm x {self.tfidf_matrix.shape[1]:,} đặc trưng")
        
        if save_model:
            self.save_model()
            
        return self

    def save_model(self):
        """Lưu TF-IDF vectorizer và ma trận đặc trưng vào đĩa."""
        os.makedirs(self.model_dir, exist_ok=True)
        model_path = os.path.join(self.model_dir, "content_based_model.joblib")
        
        data_to_save = {
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "tfidf_matrix": self.tfidf_matrix,
            "job_id_to_idx": self.job_id_to_idx,
            "idx_to_job_id": self.idx_to_job_id,
            "max_features": self.max_features,
            "ngram_range": self.ngram_range
        }
        joblib.dump(data_to_save, model_path, compress=3)
        print(f" Đã lưu mô hình Content-Based ra: {model_path}")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Nạp mô hình TF-IDF đã huấn luyện từ đĩa."""
        target_path = model_path or os.path.join(self.model_dir, "content_based_model.joblib")
        if not os.path.exists(target_path):
            return False
            
        print(f" Đang tải mô hình Content-Based từ: {target_path}")
        saved = joblib.load(target_path)
        self.tfidf_vectorizer = saved["tfidf_vectorizer"]
        self.tfidf_matrix = saved["tfidf_matrix"]
        self.job_id_to_idx = saved["job_id_to_idx"]
        self.idx_to_job_id = saved["idx_to_job_id"]
        self.max_features = saved.get("max_features", self.max_features)
        self.ngram_range = saved.get("ngram_range", self.ngram_range)
        print(" Tải mô hình thành công!")
        return True

    def load_or_train(self, data_path: str = DEFAULT_DATA_PATH) -> "ContentBasedRecommender":
        """
        Nạp dữ liệu sạch, tải mô hình có sẵn hoặc tự động huấn luyện nếu chưa có.
        """
        # 1. Đọc dữ liệu việc làm sạch
        if data_path.endswith(".parquet"):
            if not os.path.exists(data_path):
                # Fallback CSV nếu chưa có parquet
                data_path = data_path.replace(".parquet", ".csv")
            self.jobs_df = pd.read_parquet(data_path) if data_path.endswith(".parquet") else pd.read_csv(data_path)
        else:
            self.jobs_df = pd.read_csv(data_path)
            
        print(f" Đã nạp {len(self.jobs_df):,} công việc sạch từ: {data_path}")
        
        # 2. Thử load model có sẵn, nếu không có hoặc lệch số lượng thì train lại
        model_path = os.path.join(self.model_dir, "content_based_model.joblib")
        if self.load_model(model_path):
            if self.tfidf_matrix.shape[0] == len(self.jobs_df):
                return self
            print(" Số lượng việc làm thay đổi so với model cũ, đang huấn luyện lại...")
            
        return self.fit(self.jobs_df, save_model=True)

    def get_content_similarity_scores(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Tính mảng điểm Cosine Similarity (shape: [num_jobs,]) giữa hồ sơ ứng viên và toàn bộ kho việc làm.
        Hàm này là cốt lõi phục vụ tích hợp Hybrid Recommender sau này.
        """
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            raise ValueError("Mô hình chưa được huấn luyện. Vui lòng gọi .load_or_train() trước.")
            
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        
        all_skills = []
        seen = set()
        for s in manual_skills + extracted_skills:
            if s.lower() not in seen:
                seen.add(s.lower())
                all_skills.append(s)
                
        skills_soup = " ".join(all_skills)
        parts = []
        if target_title:
            parts.extend([target_title, target_title, target_title])
        if skills_soup:
            parts.extend([skills_soup, skills_soup, skills_soup, skills_soup])
        if cv_text:
            parts.append(cv_text)
            
        profile_soup = " ".join(parts).strip()
        if not profile_soup:
            return np.zeros(self.tfidf_matrix.shape[0])
            
        profile_vec = self.tfidf_vectorizer.transform([profile_soup])
        scores = cosine_similarity(profile_vec, self.tfidf_matrix).flatten()
        return scores

    def recommend(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None,
        user_exp: float = 1.0,
        preferred_city: str = "Tất cả",
        min_salary: Optional[float] = None,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Hàm gợi ý việc làm thông minh kết hợp: Vị trí + CV Text + Kỹ năng chọn tay + Two-Stage Filtering.
        """
        if self.jobs_df is None:
            raise ValueError("Chưa nạp dữ liệu jobs_df.")
            
        scores = self.get_content_similarity_scores(target_title, cv_text, skills)
        
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        seen_skills = set(s.lower() for s in manual_skills + extracted_skills)
        
        results = []
        for idx, score in enumerate(scores):
            row = self.jobs_df.iloc[idx]
            
            # Lọc cứng 1: Trạng thái tin tuyển dụng
            if 'is_active' in row and not row['is_active']:
                continue
                
            # Lọc cứng 2: Địa điểm (nếu chọn thành phố cụ thể, chấp nhận thành phố đó hoặc Remote)
            if preferred_city != 'Tất cả':
                if row['city'] != preferred_city and row['work_mode'] != 'Remote':
                    continue
                    
            # Lọc cứng 3: Số năm kinh nghiệm (không gợi ý job đòi hỏi exp > user_exp + 1.0)
            job_min_exp = row.get('experience_min')
            if pd.notnull(job_min_exp) and job_min_exp > (user_exp + 1.0):
                continue
                
            # Lọc cứng 4: Mức lương tối thiểu (nếu job có công khai lương)
            job_sal_max = row.get('salary_max')
            if min_salary is not None and pd.notnull(job_sal_max) and job_sal_max < min_salary:
                continue
                
            # Phân tích kỹ năng đáp ứng vs còn thiếu
            job_skills = [s.strip() for s in str(row.get('required_skills', '')).split(',') if s.strip()]
            job_skills_lower = [s.lower() for s in job_skills]
            
            matched = [s for s, sl in zip(job_skills, job_skills_lower) if sl in seen_skills]
            missing = [s for s, sl in zip(job_skills, job_skills_lower) if sl not in seen_skills]
            coverage_pct = round(len(matched) / len(job_skills) * 100, 1) if job_skills else 100.0
            
            salary_str = "Thoả thuận"
            s_min, s_max = row.get('salary_min'), row.get('salary_max')
            if pd.notnull(s_min) and pd.notnull(s_max):
                if s_min == s_max:
                    salary_str = f"{s_min/1e6:.0f} tr"
                else:
                    salary_str = f"{s_min/1e6:.0f} - {s_max/1e6:.0f} tr"
            elif pd.notnull(s_max):
                salary_str = f"Lên đến {s_max/1e6:.0f} tr"
            elif pd.notnull(s_min):
                salary_str = f"Từ {s_min/1e6:.0f} tr"
                
            results.append({
                'job_id': row.get('job_id', ''),
                'Tiêu đề': row.get('title', ''),
                'Công ty': row.get('company_name', ''),
                'Độ phù hợp (%)': round(score * 100, 1),
                'Độ phủ kỹ năng (%)': f"{coverage_pct}% ({len(matched)}/{len(job_skills)})",
                'Kỹ năng đã có (Điểm mạnh)': ', '.join(matched[:4]) if matched else 'Khớp theo vị trí/mô tả',
                'Kỹ năng còn thiếu (Gap)': ', '.join(missing[:4]) if missing else 'Đầy đủ',
                'Kinh nghiệm yêu cầu': f"{row.get('experience_min')} năm" if pd.notnull(row.get('experience_min')) else 'Không yêu cầu',
                'Thành phố': row.get('city', ''),
                'Hình thức': row.get('work_mode', ''),
                'Mức lương': salary_str,
                'job_url': row.get('job_url', ''),
                'company_logo_url': row.get('company_logo_url', '')
            })
            
        df_res = pd.DataFrame(results).sort_values(by='Độ phù hợp (%)', ascending=False)
        return df_res.head(top_n)

    def recommend_similar_jobs(
        self,
        job_identifier: Union[int, str],
        top_n: int = 5,
        same_city_only: bool = False
    ) -> pd.DataFrame:
        """Gợi ý các công việc tương đồng với một công việc cho trước (Job-to-Job Recommender)."""
        if self.jobs_df is None or self.tfidf_matrix is None:
            raise ValueError("Mô hình chưa sẵn sàng.")
            
        if isinstance(job_identifier, (int, np.integer)):
            idx = int(job_identifier)
        elif str(job_identifier) in self.job_id_to_idx:
            idx = self.job_id_to_idx[str(job_identifier)]
        else:
            match = self.jobs_df[self.jobs_df['title'].str.contains(str(job_identifier), case=False, na=False, regex=False)]
            if match.empty:
                print(f" Không tìm thấy công việc: {job_identifier}")
                return pd.DataFrame()
            idx = match.index[0]
            
        target_job = self.jobs_df.iloc[idx]
        target_vec = self.tfidf_matrix[idx]
        sim_scores = cosine_similarity(target_vec, self.tfidf_matrix).flatten()
        sorted_indices = np.argsort(sim_scores)[::-1]
        
        target_skills = set(s.strip().lower() for s in str(target_job.get('required_skills', '')).split(',') if s.strip())
        results = []
        
        for j_idx in sorted_indices:
            if j_idx == idx:
                continue  # Bỏ qua chính nó
            cand = self.jobs_df.iloc[j_idx]
            if same_city_only and cand['city'] != target_job['city'] and cand['work_mode'] != 'Remote':
                continue
                
            cand_skills = set(s.strip().lower() for s in str(cand.get('required_skills', '')).split(',') if s.strip())
            common = target_skills & cand_skills
            common_display = [s.strip() for s in str(cand.get('required_skills', '')).split(',') if s.strip().lower() in common]
            
            salary_str = "Thoả thuận"
            c_min, c_max = cand.get('salary_min'), cand.get('salary_max')
            if pd.notnull(c_min) and pd.notnull(c_max):
                if c_min == c_max:
                    salary_str = f"{c_min/1e6:.0f} tr"
                else:
                    salary_str = f"{c_min/1e6:.0f} - {c_max/1e6:.0f} tr"
            elif pd.notnull(c_max):
                salary_str = f"Lên đến {c_max/1e6:.0f} tr"
            elif pd.notnull(c_min):
                salary_str = f"Từ {c_min/1e6:.0f} tr"
                
            results.append({
                'job_id': cand.get('job_id', ''),
                'Tiêu đề': cand.get('title', ''),
                'Công ty': cand.get('company_name', ''),
                'Độ tương đồng (%)': round(sim_scores[j_idx] * 100, 1),
                'Địa điểm': cand.get('city', ''),
                'Kinh nghiệm': f"{cand.get('experience_min')} năm" if pd.notnull(cand.get('experience_min')) else 'Không yêu cầu',
                'Mức lương': salary_str,
                'Kỹ năng trùng khớp': ', '.join(common_display[:4]) if common_display else 'Khớp theo mô tả',
                'job_url': cand.get('job_url', ''),
                'company_logo_url': cand.get('company_logo_url', '')
            })
            if len(results) >= top_n:
                break
                
        return pd.DataFrame(results)

    def analyze_cv_fit_for_job(
        self,
        job_identifier: Union[int, str],
        cv_text: str = "",
        skills: Optional[List[str]] = None,
        user_exp: float = 1.0
    ) -> str:
        """Xuất báo cáo phân tích so khớp chi tiết 1:1 giữa hồ sơ ứng viên và một công việc cụ thể."""
        if self.jobs_df is None or self.tfidf_vectorizer is None:
            raise ValueError("Mô hình chưa sẵn sàng.")
            
        if isinstance(job_identifier, (int, np.integer)):
            idx = int(job_identifier)
        elif str(job_identifier) in self.job_id_to_idx:
            idx = self.job_id_to_idx[str(job_identifier)]
        else:
            match = self.jobs_df[self.jobs_df['title'].str.contains(str(job_identifier), case=False, na=False, regex=False)]
            if match.empty:
                return f" Không tìm thấy công việc: {job_identifier}"
            idx = match.index[0]
            
        job = self.jobs_df.iloc[idx]
        
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        all_user_skills = []
        seen_skills = set()
        for s in manual_skills + extracted_skills:
            if s.lower() not in seen_skills:
                seen_skills.add(s.lower())
                all_user_skills.append(s)
                
        input_text = f"{' '.join(all_user_skills)} {cv_text}".strip()
        user_vec = self.tfidf_vectorizer.transform([input_text])
        job_vec = self.tfidf_matrix[idx]
        sim_score = cosine_similarity(user_vec, job_vec)[0][0]
        
        job_skills = [s.strip() for s in str(job.get('required_skills', '')).split(',') if s.strip()]
        job_skills_lower = [s.lower() for s in job_skills]
        
        matched = [s for s, sl in zip(job_skills, job_skills_lower) if sl in seen_skills]
        missing = [s for s, sl in zip(job_skills, job_skills_lower) if sl not in seen_skills]
        
        exp_required = job.get('experience_min') if pd.notnull(job.get('experience_min')) else 0.0
        if user_exp >= exp_required:
            exp_status = f" Đạt yêu cầu ({user_exp} năm >= {exp_required} năm)"
        elif user_exp + 1.0 >= exp_required:
            exp_status = f" Chấp nhận được ({user_exp} năm xấp xỉ yêu cầu {exp_required} năm)"
        else:
            exp_status = f" Chưa đủ kinh nghiệm ({user_exp} năm < yêu cầu {exp_required} năm)"
            
        coverage_pct = round(len(matched) / len(job_skills) * 100, 1) if job_skills else 100.0
        
        sal_str = "Thoả thuận"
        s_min, s_max = job.get('salary_min'), job.get('salary_max')
        if pd.notnull(s_min) and pd.notnull(s_max):
            sal_str = f"{s_min/1e6:.0f} - {s_max/1e6:.0f} triệu"
        elif pd.notnull(s_max):
            sal_str = f"Lên đến {s_max/1e6:.0f} triệu"
            
        report = f"""================================================================================
 BÁO CÁO ĐÁNH GIÁ ĐỘ PHÙ HỢP HỒ SƠ VỚI CÔNG VIỆC (FIT REPORT)
================================================================================
Công việc mục tiêu: {job.get('title')}
Công ty:             {job.get('company_name')}
Địa điểm:            {job.get('city')} ({job.get('work_mode')})
Mức lương:           {sal_str}

--- 1. ĐIỂM SỐ TỔNG QUAN ---
• Điểm tương đồng nội dung (Content Similarity): {sim_score * 100:.1f}%
• Tỷ lệ đáp ứng kỹ năng (Skill Coverage):         {coverage_pct}% ({len(matched)}/{len(job_skills)} kỹ năng)
• Đánh giá số năm kinh nghiệm:                   {exp_status}

--- 2. CHI TIẾT KỸ NĂNG ---
 Kỹ năng bạn đã có ({len(matched)}):
   {', '.join(matched) if matched else 'Không có kỹ năng trùng khớp trực tiếp'}
 Kỹ năng còn thiếu mà công ty yêu cầu ({len(missing)}):
   {', '.join(missing) if missing else 'Tuyệt vời! Bạn đáp ứng đầy đủ tất cả kỹ năng cốt lõi'}

--- 3. LỜI KHUYÊN DÀNH CHO BẠN ---
"""
        if missing:
            report += f" Để tăng cơ hội trúng tuyển, bạn nên bổ sung thêm kinh nghiệm hoặc học thêm về: {', '.join(missing)}.\n"
        else:
            report += " Hồ sơ của bạn rất mạnh cho vị trí này! Hãy tự tin nộp đơn ứng tuyển ngay.\n"
        report += "================================================================================"
        return report


_CACHED_CB_ENGINE: Optional[ContentBasedRecommender] = None

def get_content_based_recommender(data_path: str = DEFAULT_DATA_PATH) -> ContentBasedRecommender:
    """Singleton getter để dùng chung một thể hiện mô hình Content-Based trên toàn dự án."""
    global _CACHED_CB_ENGINE
    if _CACHED_CB_ENGINE is None:
        engine = ContentBasedRecommender()
        engine.load_or_train(data_path)
        _CACHED_CB_ENGINE = engine
    return _CACHED_CB_ENGINE


if __name__ == "__main__":
    print("=== KIỂM THỬ MODULE CONTENT-BASED RECOMMENDER ===")
    recommender = get_content_based_recommender()
    
    print("\n1. Test gợi ý theo CV:")
    sample_cv = """
    Kỹ sư Backend với 2 năm kinh nghiệm.
    Thành thạo lập trình Python (Django, FastAPI), làm việc với cơ sở dữ liệu PostgreSQL và MySQL.
    Có kinh nghiệm Docker, CI/CD và triển khai ứng dụng trên Linux AWS.
    """
    df_recs = recommender.recommend(
        target_title="Backend Developer",
        cv_text=sample_cv,
        user_exp=2.0,
        preferred_city="Hà Nội",
        top_n=3
    )
    print(df_recs[['Tiêu đề', 'Công ty', 'Độ phù hợp (%)', 'Độ phủ kỹ năng (%)', 'Kỹ năng đã có (Điểm mạnh)']])
    
    print("\n2. Test Báo cáo So khớp 1:1:")
    top1_id = df_recs.iloc[0]['job_id']
    rep = recommender.analyze_cv_fit_for_job(top1_id, cv_text=sample_cv, user_exp=2.0)
    print(rep)
