import os
import sys

# Đảm bảo đường dẫn gốc dự án luôn nằm trong sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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

DEFAULT_DATA_CANDIDATES = [
    os.path.join(PROJECT_ROOT, "data", "notebook", "content_base", "jobs_clean.csv"),
    os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.parquet"),
    os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.csv"),
    os.path.join(PROJECT_ROOT, "data", "cleaned", "jobs_clean.csv")
]
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "models")


# ==============================================================================
# HÀM BỔ TRỢ TÍNH ĐIỂM THÀNH PHẦN (COMPONENT SCORING HELPERS)
# ==============================================================================

def compute_skill_score(
    user_skills: List[str],
    job_required_skills: List[str],
    job_preferred_skills: Optional[List[str]] = None
) -> float:
    """
    S_skills: Tỷ lệ khớp kỹ năng bắt buộc cốt lõi [0, 1].
    (Trường preferred_skills đã được loại bỏ khỏi công thức do dữ liệu thực tế bị rỗng >99.4%).
    """
    user_set = set(s.lower() for s in user_skills if s and s.lower() != 'nan')
    req_set = set(s.lower() for s in job_required_skills if s and s.lower() != 'nan') if job_required_skills else set()
    
    if not req_set:
        return 0.5
    
    req_matched = len(user_set.intersection(req_set))
    return round(req_matched / len(req_set), 3)


def compute_exp_score(
    user_exp: float,
    job_min_exp: Optional[float],
    job_max_exp: Optional[float] = None
) -> float:
    """S_experience: Điểm phù hợp số năm kinh nghiệm [0, 1]."""
    if pd.isna(job_min_exp) or job_min_exp == 0:
        return 1.0
    diff = user_exp - job_min_exp
    if diff >= 0:
        if pd.notna(job_max_exp) and user_exp > job_max_exp + 3:
            return 0.85
        return 1.0
    elif diff >= -1.0:
        return 0.7
    elif diff >= -2.0:
        return 0.4
    else:
        return 0.1


def compute_location_mode_score(
    user_city: str,
    user_modes: Optional[Union[str, List[str]]],
    job_city: Any,
    job_mode: Any
) -> float:
    """S_location/mode: Điểm kết hợp địa điểm và mô hình làm việc."""
    score_mode = 0.5
    score_city = 0.5
    job_mode_str = str(job_mode).lower()
    
    if isinstance(user_modes, str):
        user_modes = [user_modes]
    user_modes_lower = [m.lower() for m in user_modes] if user_modes else ['tất cả']
    
    if 'tất cả' in user_modes_lower or not user_modes:
        score_mode = 1.0
    elif any(m in job_mode_str for m in user_modes_lower):
        score_mode = 1.0
    elif 'remote' in job_mode_str:
        score_mode = 0.9
    elif 'hybrid' in job_mode_str and any('remote' in m for m in user_modes_lower):
        score_mode = 0.8
    else:
        score_mode = 0.2
        
    if user_city == 'Tất cả' or not user_city:
        score_city = 1.0
    elif str(job_city).lower() == str(user_city).lower():
        score_city = 1.0
    elif 'remote' in job_mode_str:
        score_city = 1.0
    else:
        score_city = 0.1
        
    return round(0.5 * score_city + 0.5 * score_mode, 3)


def compute_salary_score(
    user_min_salary: Optional[float],
    job_salary_min: Optional[float],
    job_salary_max: Optional[float]
) -> Optional[float]:
    """S_salary: Trả về None nếu bài đăng không có số liệu lương cụ thể."""
    if pd.isna(job_salary_max) and pd.isna(job_salary_min):
        return None
    max_sal = job_salary_max if pd.notna(job_salary_max) else job_salary_min
    if not user_min_salary or user_min_salary == 0:
        return 1.0
    if max_sal >= user_min_salary:
        return 1.0
    else:
        ratio = max_sal / user_min_salary
        return round(max(0.0, float(ratio)), 3)


def compute_composite_score(
    s_skills: float,
    s_text: float,
    s_exp: float,
    s_loc: float,
    s_sal: Optional[float],
    base_weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Tính điểm tổng hợp Score(j, u) và tự động chuẩn hóa lại trọng số khi thiếu lương.
    Score = 0.40*S_skills + 0.30*S_text + 0.10*S_exp + 0.10*S_loc + 0.10*S_sal
    """
    if base_weights is None:
        base_weights = {
            'skills': 0.40,
            'text': 0.30,
            'exp': 0.10,
            'loc': 0.10,
            'sal': 0.10
        }
    weights = base_weights.copy()
    scores = {
        'skills': s_skills,
        'text': s_text,
        'exp': s_exp,
        'loc': s_loc,
        'sal': s_sal
    }
    if s_sal is None:
        del weights['sal']
        del scores['sal']
        total_w = sum(weights.values())
        weights = {k: v / total_w for k, v in weights.items()}
        
    total_score = sum(weights[k] * scores[k] for k in weights)
    return round(total_score, 4), weights


def generate_rationale(
    matched_skills: List[str],
    missing_skills: List[str],
    user_exp: float,
    job_min_exp: Optional[float],
    job_mode: str,
    is_salary_fit: Optional[bool]
) -> str:
    """Sinh câu giải thích gợi ý trực quan."""
    reasons = []
    total_skills = len(matched_skills) + len(missing_skills)
    if total_skills > 0:
        matched_str = ', '.join(matched_skills[:3]) if matched_skills else 'Chưa trùng trực tiếp'
        reasons.append(f"Khớp {len(matched_skills)}/{total_skills} kỹ năng ({matched_str})")
    if pd.isna(job_min_exp) or job_min_exp == 0:
        reasons.append("Không đòi hỏi số năm kinh nghiệm")
    elif user_exp >= job_min_exp:
        reasons.append(f"Kinh nghiệm phù hợp ({user_exp:.0f} năm >= yêu cầu {job_min_exp:.0f} năm)")
    else:
        reasons.append(f"Yêu cầu {job_min_exp:.0f} năm (bạn có {user_exp:.0f} năm)")
    reasons.append(f"Hình thức {job_mode}")
    if is_salary_fit is True:
        reasons.append("Đạt kỳ vọng lương")
    elif is_salary_fit is None:
        reasons.append("Lương thỏa thuận")
    else:
        reasons.append("Thấp hơn kỳ vọng lương")
    return "; ".join(reasons)


def format_salary_display(s_min: Optional[float], s_max: Optional[float]) -> str:
    """Định dạng hiển thị mức lương trực quan."""
    if pd.notnull(s_min) and pd.notnull(s_max):
        if s_min == s_max:
            return f"{s_min/1e6:.0f} tr"
        return f"{s_min/1e6:.0f} - {s_max/1e6:.0f} tr"
    elif pd.notnull(s_max):
        return f"Lên đến {s_max/1e6:.0f} tr"
    elif pd.notnull(s_min):
        return f"Từ {s_min/1e6:.0f} tr"
    return "Thoả thuận"


# ==============================================================================
# LỚP CONTENT-BASED RECOMMENDER
# ==============================================================================

class ContentBasedRecommender:
    """
    Hệ thống gợi ý việc làm dựa trên nội dung (Content-Based Filtering V2):
    - Sử dụng Weighted TF-IDF (Chức danh x3, Kỹ năng x4, Mô tả x1).
    - Cấu hình token_pattern bảo tồn nguyên vẹn các ký tự IT đặc thù (C++, C#, .NET, CI/CD).
    - Công thức chấm điểm tổng hợp đa thành phần: Score = 0.40*Skills + 0.30*Text + 0.10*Exp + 0.10*Loc + 0.10*Salary.
    - Cơ chế co giãn trọng số linh hoạt (Dynamic Re-weighting) khi bài đăng khuyết thông tin lương.
    - Tự động sinh Lời giải thích gợi ý (Rationale) minh bạch.
    - Phân tích khoảng cách kỹ năng (Skill Gap Analysis).
    - Báo cáo đánh giá so khớp chi tiết 1:1 giữa CV và Công việc.
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
        soup = f"{title} {title} {title} {skills} {skills} {skills} {skills} {desc}"
        return soup.strip()

    def fit(self, jobs_df: pd.DataFrame, save_model: bool = True) -> "ContentBasedRecommender":
        """Huấn luyện TF-IDF trên tập dữ liệu việc làm và lưu mô hình vào data/models/."""
        self.jobs_df = jobs_df.copy().reset_index(drop=True)
        
        if 'content_soup' not in self.jobs_df.columns:
            self.jobs_df['content_soup'] = self.jobs_df.apply(self.build_content_soup, axis=1)
            
        self.job_id_to_idx = {str(jid): idx for idx, jid in enumerate(self.jobs_df['job_id'])}
        self.idx_to_job_id = {idx: str(jid) for idx, jid in enumerate(self.jobs_df['job_id'])}
        
        print(f"Đang huấn luyện TF-IDF ({self.max_features:,} features, n-gram {self.ngram_range}, token_pattern bảo tồn C++/C#/.NET)...")
        self.tfidf_vectorizer = TfidfVectorizer(
            token_pattern=r"(?u)\b[a-zA-Z0-9_+#\.]+\b",
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.jobs_df['content_soup'])
        print(f"Huấn luyện hoàn tất: {self.tfidf_matrix.shape[0]:,} việc làm x {self.tfidf_matrix.shape[1]:,} đặc trưng")
        
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
        print(f"Đã lưu mô hình Content-Based ra: {model_path}")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Nạp mô hình TF-IDF đã huấn luyện từ đĩa."""
        target_path = model_path or os.path.join(self.model_dir, "content_based_model.joblib")
        if not os.path.exists(target_path):
            return False
            
        print(f"Đang tải mô hình Content-Based từ: {target_path}")
        saved = joblib.load(target_path)
        self.tfidf_vectorizer = saved["tfidf_vectorizer"]
        self.tfidf_matrix = saved["tfidf_matrix"]
        self.job_id_to_idx = saved["job_id_to_idx"]
        self.idx_to_job_id = saved["idx_to_job_id"]
        self.max_features = saved.get("max_features", self.max_features)
        self.ngram_range = saved.get("ngram_range", self.ngram_range)
        print("Tải mô hình thành công!")
        return True

    def load_or_train(self, data_path: Optional[str] = None) -> "ContentBasedRecommender":
        """Nạp dữ liệu sạch, tải mô hình có sẵn hoặc tự động huấn luyện nếu chưa có."""
        resolved_path = None
        if data_path and os.path.exists(data_path):
            resolved_path = data_path
        else:
            for p in DEFAULT_DATA_CANDIDATES:
                if os.path.exists(p):
                    resolved_path = p
                    break
                    
        if not resolved_path:
            raise FileNotFoundError(f"Không tìm thấy tập dữ liệu việc làm sạch tại bất kỳ đường dẫn nào: {DEFAULT_DATA_CANDIDATES}")
            
        if resolved_path.endswith(".parquet"):
            self.jobs_df = pd.read_parquet(resolved_path)
        else:
            self.jobs_df = pd.read_csv(resolved_path)
            
        print(f"Đã nạp {len(self.jobs_df):,} công việc sạch từ: {resolved_path}")
        
        model_path = os.path.join(self.model_dir, "content_based_model.joblib")
        if self.load_model(model_path):
            if self.tfidf_matrix.shape[0] == len(self.jobs_df):
                return self
            print("Số lượng việc làm thay đổi so với model cũ, đang huấn luyện lại...")
            
        return self.fit(self.jobs_df, save_model=True)

    def get_content_similarity_scores(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None
    ) -> np.ndarray:
        """Tính mảng điểm Cosine Similarity văn bản giữa hồ sơ ứng viên và toàn bộ kho việc làm."""
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            raise ValueError("Mô hình chưa được huấn luyện. Vui lòng gọi .load_or_train() trước.")
            
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        all_skills = list(dict.fromkeys(manual_skills + extracted_skills))
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
        preferred_work_modes: Optional[Union[str, List[str]]] = None,
        min_salary: Optional[float] = None,
        top_n: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Hàm gợi ý việc làm toàn diện chuẩn hóa đồng bộ với Notebook 05:
        Kết hợp 5 yếu tố: Kỹ năng (40%) + Văn bản (30%) + Kinh nghiệm (10%) + Vị trí/Hình thức (10%) + Lương (10%).
        Kèm cơ chế Dynamic Re-weighting và tự động sinh Lời giải thích (Rationale).
        """
        if self.jobs_df is None or self.tfidf_matrix is None:
            raise ValueError("Chưa nạp dữ liệu hoặc mô hình.")
            
        text_similarities = self.get_content_similarity_scores(target_title, cv_text, skills)
        
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        all_user_skills = list(dict.fromkeys(manual_skills + extracted_skills))
        user_skills_lower = set(s.lower() for s in all_user_skills)
        
        candidates = []
        for idx in range(len(self.jobs_df)):
            row = self.jobs_df.iloc[idx]
            
            # Bỏ qua tin không còn hoạt động
            if 'is_active' in row and not row['is_active']:
                continue
                
            raw_req = row.get('required_skills', '')
            req_skills = [s.strip() for s in str(raw_req).split(',') if s.strip() and s.strip().lower() != 'nan'] if pd.notna(raw_req) else []
            
            # 1. Tính 5 điểm thành phần (không dùng preferred_skills do >99.4% rỗng)
            s_skills = compute_skill_score(all_user_skills, req_skills)
            s_text = round(float(text_similarities[idx]), 4)
            s_exp = compute_exp_score(user_exp, row.get('experience_min'), row.get('experience_max'))
            s_loc = compute_location_mode_score(preferred_city, preferred_work_modes, row.get('city'), row.get('work_mode'))
            s_sal = compute_salary_score(min_salary, row.get('salary_min'), row.get('salary_max'))
            
            # 2. Tính điểm tổng hợp Composite Score
            composite_score, _ = compute_composite_score(s_skills, s_text, s_exp, s_loc, s_sal, base_weights=weights)
            
            # 3. Kỹ năng khớp và thiếu
            matched = [s for s in req_skills if s.lower() in user_skills_lower]
            missing = [s for s in req_skills if s.lower() not in user_skills_lower]
            coverage_pct = round(len(matched) / len(req_skills) * 100, 1) if req_skills else 100.0
            
            is_sal_fit = True if s_sal == 1.0 else (None if s_sal is None else False)
            rationale = generate_rationale(
                matched, missing, user_exp, row.get('experience_min'),
                row.get('work_mode', 'Onsite'), is_sal_fit
            )
            
            salary_display = format_salary_display(row.get('salary_min'), row.get('salary_max'))
            
            candidates.append({
                'job_id': row.get('job_id', ''),
                'Tiêu đề': row.get('title', ''),
                'Công ty': row.get('company_name', ''),
                'Tổng điểm (%)': round(composite_score * 100, 1),
                'Độ phù hợp (%)': round(composite_score * 100, 1), # Alias tương thích UI
                'Điểm kỹ năng (%)': round(s_skills * 100, 1),
                'Điểm văn bản (%)': round(s_text * 100, 1),
                'Điểm kinh nghiệm (%)': round(s_exp * 100, 1),
                'Điểm vị trí/hình thức (%)': round(s_loc * 100, 1),
                'Lời giải thích': rationale,
                'Độ phủ kỹ năng (%)': f"{coverage_pct}% ({len(matched)}/{len(req_skills)})",
                'Kỹ năng đã có (Điểm mạnh)': ', '.join(matched[:4]) if matched else 'Khớp theo vị trí/mô tả',
                'Kỹ năng còn thiếu (Gap)': ', '.join(missing[:4]) if missing else 'Đầy đủ',
                'Kinh nghiệm yêu cầu': f"{row.get('experience_min')} năm" if pd.notnull(row.get('experience_min')) else 'Không yêu cầu',
                'Hình thức': row.get('work_mode', 'Onsite'),
                'Thành phố': row.get('city', 'Không rõ'),
                'Mức lương': salary_display,
                'job_url': row.get('job_url', ''),
                'company_logo_url': row.get('company_logo_url', '')
            })
            
        df_res = pd.DataFrame(candidates).sort_values(by='Tổng điểm (%)', ascending=False)
        return df_res.head(top_n)

    def analyze_cv_fit_for_job(
        self,
        job_identifier: Union[int, str],
        cv_text: str = "",
        skills: Optional[List[str]] = None,
        user_exp: float = 1.0
    ) -> str:
        """Báo cáo đánh giá chi tiết 1:1 giữa hồ sơ ứng viên và một công việc cụ thể."""
        if self.jobs_df is None or self.tfidf_vectorizer is None:
            raise ValueError("Mô hình chưa sẵn sàng.")
            
        if isinstance(job_identifier, (int, np.integer)):
            idx = int(job_identifier)
        elif str(job_identifier) in self.job_id_to_idx:
            idx = self.job_id_to_idx[str(job_identifier)]
        else:
            match = self.jobs_df[self.jobs_df['title'].str.contains(str(job_identifier), case=False, na=False, regex=False)]
            if match.empty:
                return f"Không tìm thấy công việc: {job_identifier}"
            idx = match.index[0]
            
        job = self.jobs_df.iloc[idx]
        
        manual_skills = skills or []
        extracted_skills = extract_skills_from_text(cv_text) if cv_text else []
        all_user_skills = list(dict.fromkeys(manual_skills + extracted_skills))
        user_skills_lower = set(s.lower() for s in all_user_skills)
        
        input_text = f"{' '.join(all_user_skills)} {cv_text}".strip()
        user_vec = self.tfidf_vectorizer.transform([input_text])
        job_vec = self.tfidf_matrix[idx]
        sim_score = cosine_similarity(user_vec, job_vec)[0][0]
        
        job_skills = [s.strip() for s in str(job.get('required_skills', '')).split(',') if s.strip()]
        matched = [s for s in job_skills if s.lower() in user_skills_lower]
        missing = [s for s in job_skills if s.lower() not in user_skills_lower]
        
        exp_required = job.get('experience_min') if pd.notnull(job.get('experience_min')) else 0.0
        exp_status = f"Đạt yêu cầu ({user_exp} năm >= {exp_required} năm)" if user_exp >= exp_required else f"Chưa đủ kinh nghiệm ({user_exp} năm < yêu cầu {exp_required} năm)"
        coverage_pct = round(len(matched) / len(job_skills) * 100, 1) if job_skills else 100.0
        
        salary_str = format_salary_display(job.get('salary_min'), job.get('salary_max'))
        
        report = f"""================================================================================
BÁO CÁO ĐÁNH GIÁ ĐỘ PHÙ HỢP HỒ SƠ VỚI CÔNG VIỆC (1:1 FIT REPORT)
================================================================================
Công việc mục tiêu: {job.get('title')}
Công ty:             {job.get('company_name')}
Địa điểm:            {job.get('city')} ({job.get('work_mode', 'Tại văn phòng')})
Mức lương:           {salary_str}

--- 1. ĐIỂM SỐ TỔNG QUAN ---
• Điểm tương đồng nội dung (Text Similarity):    {sim_score * 100:.1f}%
• Tỷ lệ đáp ứng kỹ năng (Skill Coverage):         {coverage_pct}% ({len(matched)}/{len(job_skills)} kỹ năng)
• Đánh giá số năm kinh nghiệm:                   {exp_status}

--- 2. CHI TIẾT KỸ NĂNG ---
Kỹ năng bạn đã có ({len(matched)}):
   {', '.join(matched) if matched else 'Chưa trùng trực tiếp kỹ năng công nghệ'}
Kỹ năng còn thiếu mà công ty yêu cầu ({len(missing)}):
   {', '.join(missing) if missing else 'Tuyệt vời! Bạn đáp ứng đầy đủ tất cả kỹ năng'}
================================================================================"""
        return report


_CACHED_CB_ENGINE: Optional[ContentBasedRecommender] = None

def get_content_based_recommender(data_path: Optional[str] = None) -> ContentBasedRecommender:
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
    
    print("\n1. Test Case 1 chuẩn (Python, SQL, ML | 1 năm | Hà Nội | Remote/Hybrid | Lương >= 20tr):")
    df_recs = recommender.recommend(
        target_title="Python Developer Machine Learning",
        skills=["Python", "SQL", "Machine Learning"],
        user_exp=1.0,
        preferred_city="Hà Nội",
        preferred_work_modes=["Remote", "Hybrid"],
        min_salary=20000000,
        top_n=5
    )
    print(df_recs[['Tiêu đề', 'Công ty', 'Tổng điểm (%)', 'Điểm kỹ năng (%)', 'Điểm văn bản (%)', 'Lời giải thích', 'Mức lương']])
    
    print("\n2. Test Báo cáo So khớp 1:1:")
    top1_id = df_recs.iloc[0]['job_id']
    rep = recommender.analyze_cv_fit_for_job(top1_id, skills=["Python", "SQL", "Machine Learning"], user_exp=1.0)
    print(rep)
