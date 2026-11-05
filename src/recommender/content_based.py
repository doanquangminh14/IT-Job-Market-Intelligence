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

import hashlib

from src.data_cleaning.skill_canonical import (
    CANONICAL_SKILL_MAP,
    extract_skills_from_text,
    normalize_user_skills,
    split_skill_match,
)
from src.data_cleaning.it_filter import is_it_job
from src.recommender.text_utils import normalize_tech_text, TOKEN_PATTERN

DEFAULT_DATA_CANDIDATES = [
    os.path.join(PROJECT_ROOT, "data", "notebook", "content_base", "jobs_clean.csv"),
    os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.parquet"),
    os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.csv"),
    os.path.join(PROJECT_ROOT, "data", "cleaned", "jobs_clean.csv")
]
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "models")
TOKENIZER_VERSION = 3  # tăng khi đổi cách tokenize / dựng content soup để buộc huấn luyện lại model cũ
DEFAULT_WEIGHTS = {'skills': 0.30, 'text': 0.40, 'exp': 0.10, 'loc': 0.10, 'sal': 0.10}
COMPONENTS = ['skills', 'text', 'exp', 'loc', 'sal']
RELATED_SKILL_CREDIT = 0.5  # một kỹ năng gần nhau (PostgreSQL ~ MySQL) = nửa kỹ năng khớp (notebook 05, mục 8.4)


# ==============================================================================
# HÀM BỔ TRỢ TÍNH ĐIỂM THÀNH PHẦN (COMPONENT SCORING HELPERS)
# ==============================================================================

def compute_skill_score(
    user_skills: List[str],
    job_required_skills: List[str],
    job_preferred_skills: Optional[List[str]] = None,
    mode: str = 'v3',
    related_credit: float = RELATED_SKILL_CREDIT
) -> Optional[float]:
    """
    S_skills: mức khớp kỹ năng bắt buộc [0, 1]; trả về None nếu job không liệt kê kỹ năng nào (mode v2, v3).
      - 'v1' (cũ)  : coverage = số kỹ năng khớp / số kỹ năng job yêu cầu  (job yêu cầu 1 kỹ năng bạn có => 100%)
      - 'v2'       : coverage x m/(m+1) với m = số kỹ năng khớp (khớp càng nhiều, bằng chứng càng đáng tin)
      - 'v3' (mới) : như v2 nhưng m = khớp chính xác + related_credit x số kỹ năng gần nhau (PostgreSQL ~ MySQL)
    (preferred_skills đã được loại bỏ do dữ liệu thực tế bị rỗng >99%).
    """
    req_set = set(s.lower() for s in job_required_skills if s and s.lower() != 'nan') if job_required_skills else set()
    if not req_set:
        return None if mode in ('v2', 'v3') else 0.5
    matched, related, _ = split_skill_match(user_skills, list(req_set))
    m = len(matched) + (related_credit * len(related) if mode == 'v3' else 0)
    coverage = m / len(req_set)
    if mode == 'v1':
        return round(coverage, 3)
    return round(coverage * m / (m + 1), 3)


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
    s_skills: Optional[float],
    s_text: float,
    s_exp: float,
    s_loc: float,
    s_sal: Optional[float],
    base_weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Điểm tổng hợp Score(j, u) = 0.30*S_skills + 0.40*S_text + 0.10*S_exp + 0.10*S_loc + 0.10*S_sal.
    Thành phần nào là None (thiếu dữ liệu: lương thỏa thuận, job không liệt kê kỹ năng) bị loại và các
    trọng số còn lại được co giãn về tổng 1.0.
    """
    base = dict(base_weights or DEFAULT_WEIGHTS)
    scores = {'skills': s_skills, 'text': s_text, 'exp': s_exp, 'loc': s_loc, 'sal': s_sal}
    available = {k: w for k, w in base.items() if scores.get(k) is not None}
    total_w = sum(available.values())
    weights = {k: w / total_w for k, w in available.items()}
    total_score = sum(weights[k] * scores[k] for k in weights)
    return round(total_score, 4), weights


def generate_rationale(
    matched_skills: List[str],
    missing_skills: List[str],
    user_exp: float,
    job_min_exp: Optional[float],
    job_mode: str,
    is_salary_fit: Optional[bool],
    related_skills: Optional[List[str]] = None
) -> str:
    """Sinh câu giải thích gợi ý trực quan."""
    reasons = []
    related_skills = related_skills or []
    total_skills = len(matched_skills) + len(related_skills) + len(missing_skills)
    if total_skills > 0:
        matched_str = ', '.join(matched_skills[:3]) if matched_skills else 'Chưa trùng trực tiếp'
        reasons.append(f"Khớp {len(matched_skills)}/{total_skills} kỹ năng ({matched_str})")
        if related_skills:
            reasons.append(f"Gần với {', '.join(related_skills[:3])}")
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
    Hệ thống gợi ý việc làm dựa trên nội dung (Content-Based Filtering V3), đồng bộ với notebook 05:
    - Weighted TF-IDF: Chức danh x3, Kỹ năng x4, Thẻ ngành x1, Mô tả x1; tokenizer giữ C++/C#/.NET/CI-CD và tiếng Việt có dấu.
    - Điểm tổng hợp = 0.30*Skills + 0.40*Text + 0.10*Exp + 0.10*Loc + 0.10*Salary, trong đó:
        * Skills có hệ số tin cậy m/(m+1) và bị loại (co giãn trọng số) khi job không liệt kê kỹ năng;
        * Text được chuẩn hóa theo truy vấn (job giống nhất = 1.0).
    - Tự động sinh Lời giải thích (Rationale), phân tích khoảng cách kỹ năng (Skill Gap) và báo cáo 1:1 dùng chung bộ chấm điểm.
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
        self.signature: Optional[str] = None
        self._loaded_signature: Optional[str] = None
        self._loaded_tokenizer_version: Optional[int] = None

    @staticmethod
    def _split_skills(value: Any) -> List[str]:
        if isinstance(value, (list, tuple, np.ndarray)):
            return [str(x).strip() for x in value if str(x).strip()]
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return []
        return [x.strip() for x in str(value).split(',') if x.strip() and x.strip().lower() != 'nan']

    @classmethod
    def prepare_jobs_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Chuẩn hóa dữ liệu đầu vào: điền giá trị rỗng, thêm cột job_tags nếu thiếu, tách sẵn danh sách kỹ năng."""
        out = df.copy().reset_index(drop=True)
        for col in ('required_skills', 'job_tags', 'description_clean'):
            if col not in out.columns:
                out[col] = ''
            out[col] = out[col].apply(lambda v: ', '.join(v) if isinstance(v, (list, tuple, np.ndarray)) else v).fillna('')
        if 'is_active' not in out.columns:
            out['is_active'] = True
        out['is_active'] = out['is_active'].fillna(True).astype(bool)
        out['req_list'] = out['required_skills'].map(cls._split_skills)
        return out

    @staticmethod
    def build_content_soup(row: pd.Series) -> str:
        """Content soup có trọng số: Title x3 + Required Skills x4 + Job Tags x1 + Description x1."""
        def clean(key):
            v = row.get(key, '')
            return str(v) if pd.notnull(v) else ''
        title, skills, tags, desc = clean('title'), clean('required_skills'), clean('job_tags'), clean('description_clean')
        return f"{title} {title} {title} {skills} {skills} {skills} {skills} {tags} {desc}".strip()

    def fit(self, jobs_df: pd.DataFrame, save_model: bool = True) -> "ContentBasedRecommender":
        """Huấn luyện TF-IDF trên tập dữ liệu việc làm và lưu mô hình vào data/models/."""
        self.jobs_df = self.prepare_jobs_df(jobs_df)
        self.signature = self.compute_signature(self.jobs_df)
        
        if 'content_soup' not in self.jobs_df.columns:
            self.jobs_df['content_soup'] = self.jobs_df.apply(self.build_content_soup, axis=1)
            
        self.job_id_to_idx = {str(jid): idx for idx, jid in enumerate(self.jobs_df['job_id'])}
        self.idx_to_job_id = {idx: str(jid) for idx, jid in enumerate(self.jobs_df['job_id'])}
        
        print(f"Đang huấn luyện TF-IDF ({self.max_features:,} features, n-gram {self.ngram_range}, chuẩn hóa C++/C#/.NET/CI-CD, giữ tiếng Việt có dấu)...")
        self.tfidf_vectorizer = TfidfVectorizer(
            preprocessor=normalize_tech_text,   # C++ -> cpp, C# -> csharp, .NET -> dotnet, CI/CD -> cicd...
            token_pattern=TOKEN_PATTERN,        # \w\w+ : giữ chữ tiếng Việt có dấu
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.jobs_df['content_soup'])
        print(f"Huấn luyện hoàn tất: {self.tfidf_matrix.shape[0]:,} việc làm x {self.tfidf_matrix.shape[1]:,} đặc trưng")
        
        if save_model:
            self.save_model()
            
        return self

    @staticmethod
    def compute_signature(jobs_df: pd.DataFrame) -> str:
        """Chữ ký dữ liệu (job_id, tiêu đề, kỹ năng, thẻ, độ dài mô tả) để phát hiện model cũ."""
        h = hashlib.md5()
        for jid, title, skills, tags, desc in zip(
                jobs_df['job_id'], jobs_df['title'], jobs_df['required_skills'].fillna(''),
                jobs_df['job_tags'].fillna(''), jobs_df['description_clean'].fillna('')):
            h.update(f"{jid}|{title}|{skills}|{tags}|{len(str(desc))}".encode("utf-8"))
        return h.hexdigest()

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
            "ngram_range": self.ngram_range,
            "signature": getattr(self, "signature", None),
            "tokenizer_version": TOKENIZER_VERSION
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
        self._loaded_signature = saved.get("signature")
        self._loaded_tokenizer_version = saved.get("tokenizer_version")
        print("Tải mô hình thành công!")
        return True

    def load_or_train(self, data_path: Optional[str] = None, it_only: bool = True) -> "ContentBasedRecommender":
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

        self.jobs_df = self.prepare_jobs_df(self.jobs_df)
        if it_only:
            if 'is_it' in self.jobs_df.columns:  # cột do JobCleaner/notebook làm sạch gắn sẵn
                mask = self.jobs_df['is_it'].astype(bool)
            else:
                mask = self.jobs_df.apply(lambda r: is_it_job(r.get('title'), r.get('required_skills')), axis=1)
            print(f"Lọc tin ngoài ngành IT: giữ {int(mask.sum()):,}/{len(mask):,} tin.")
            self.jobs_df = self.jobs_df[mask].reset_index(drop=True)
            self.jobs_df['req_list'] = self.jobs_df['required_skills'].map(self._split_skills)

        self.signature = self.compute_signature(self.jobs_df)
        model_path = os.path.join(self.model_dir, "content_based_model.joblib")
        if self.load_model(model_path):
            if (self.tfidf_matrix.shape[0] == len(self.jobs_df)
                    and self._loaded_signature == self.signature
                    and self._loaded_tokenizer_version == TOKENIZER_VERSION):
                return self
            print("Dữ liệu hoặc cách tokenize đã thay đổi so với model cũ, đang huấn luyện lại...")
            
        return self.fit(self.jobs_df, save_model=True)

    def build_user_profile(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None
    ) -> Tuple[List[str], str]:
        """Trả về (danh sách kỹ năng chuẩn hóa của ứng viên, chuỗi 'profile soup' để vector hóa)."""
        all_skills = list(dict.fromkeys(
            normalize_user_skills(skills) + (extract_skills_from_text(cv_text) if cv_text else [])))
        parts = []
        if target_title:
            parts.extend([target_title] * 3)
        if all_skills:
            parts.extend([" ".join(all_skills)] * 4)
        if cv_text:
            parts.append(cv_text)
        return all_skills, " ".join(parts).strip()

    def get_content_similarity_scores(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None
    ) -> np.ndarray:
        """Cosine Similarity THÔ giữa hồ sơ ứng viên và toàn bộ kho việc làm."""
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            raise ValueError("Mô hình chưa được huấn luyện. Vui lòng gọi .load_or_train() trước.")
        _, profile_soup = self.build_user_profile(target_title, cv_text, skills)
        if not profile_soup:
            return np.zeros(self.tfidf_matrix.shape[0])
        return cosine_similarity(self.tfidf_vectorizer.transform([profile_soup]), self.tfidf_matrix).flatten()

    def score_components(
        self,
        target_title: str = "",
        cv_text: str = "",
        skills: Optional[List[str]] = None,
        user_exp: float = 1.0,
        preferred_city: str = "Tất cả",
        preferred_work_modes: Optional[Union[str, List[str]]] = None,
        min_salary: Optional[float] = None,
        skill_mode: str = 'v3',
        normalize_text: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Bước 1: tính 5 điểm thành phần cho TẤT CẢ job. Trả về None nếu hồ sơ rỗng, ngược lại dict gồm:
        user_skills, raw_sim (cosine thô), comps (DataFrame 5 cột, NaN = thiếu dữ liệu), active (mask tin còn hạn).
        skill_mode='v1'/'v2' và normalize_text=False tái hiện các công thức CŨ (dùng cho ablation).
        """
        if self.jobs_df is None or self.tfidf_matrix is None:
            raise ValueError("Chưa nạp dữ liệu hoặc mô hình.")
        user_skills, profile_soup = self.build_user_profile(target_title, cv_text, skills)
        if not profile_soup:
            return None

        raw_sim = cosine_similarity(self.tfidf_vectorizer.transform([profile_soup]), self.tfidf_matrix).flatten()
        # Chuẩn hóa theo truy vấn: job giống nhất đạt 1.0 (cosine thô hiếm khi vượt 0.5 nên sẽ bị các thành phần khác lấn át)
        peak = raw_sim.max()
        text_scores = raw_sim / peak if (normalize_text and peak > 0) else raw_sim

        rows = []
        for idx, row in enumerate(self.jobs_df.itertuples(index=False)):
            s_skill = compute_skill_score(user_skills, row.req_list, mode=skill_mode)
            rows.append((
                np.nan if s_skill is None else s_skill,
                float(text_scores[idx]),
                compute_exp_score(user_exp, row.experience_min, row.experience_max),
                compute_location_mode_score(preferred_city, preferred_work_modes, row.city, row.work_mode),
                (lambda v: np.nan if v is None else v)(compute_salary_score(min_salary, row.salary_min, row.salary_max)),
            ))
        return {
            'user_skills': user_skills,
            'raw_sim': raw_sim,
            'comps': pd.DataFrame(rows, columns=COMPONENTS),
            'active': self.jobs_df['is_active'].values.astype(bool),
        }

    @staticmethod
    def combine_scores(comps: pd.DataFrame, weights: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Bước 2: gộp 5 điểm thành phần thành tổng điểm [0, 1] cho mọi job (vector hóa).
        Thành phần NaN bị loại và trọng số còn lại co giãn về tổng 1.0 (cùng quy tắc compute_composite_score).
        Job không còn thành phần nào có trọng số (vd. chỉ chấm kỹ năng mà job không ghi kỹ năng) được 0 điểm.
        """
        w = np.array([(weights or DEFAULT_WEIGHTS)[k] for k in COMPONENTS], dtype=float)
        M = comps[COMPONENTS].values
        available_weight = (~np.isnan(M) * w).sum(axis=1)
        weighted = np.nansum(M * w, axis=1)
        return np.divide(weighted, available_weight, out=np.zeros_like(weighted), where=available_weight > 0)

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
        weights: Optional[Dict[str, float]] = None,
        skill_mode: str = 'v3',
        normalize_text: bool = True
    ) -> pd.DataFrame:
        """
        Gợi ý việc làm: Kỹ năng + Văn bản + Kinh nghiệm + Vị trí/Hình thức + Lương, kèm lời giải thích và Skill Gap.
        Lời giải thích chỉ được sinh cho top_n job tốt nhất.
        """
        sc = self.score_components(target_title, cv_text, skills, user_exp, preferred_city,
                                   preferred_work_modes, min_salary, skill_mode, normalize_text)
        if sc is None:
            return pd.DataFrame()

        total = np.where(sc['active'], self.combine_scores(sc['comps'], weights), -1.0)   # bỏ tin hết hạn
        top_idx = np.argsort(-total, kind='stable')[:top_n]

        out = []
        for idx in top_idx:
            row, c = self.jobs_df.iloc[idx], sc['comps'].iloc[idx]
            req = row['req_list']
            matched, related, missing = split_skill_match(sc['user_skills'], req)
            coverage_pct = round(len(matched) / len(req) * 100, 1) if req else 100.0
            sal_fit = None if np.isnan(c['sal']) else bool(c['sal'] == 1.0)
            composite = round(float(total[idx]) * 100, 1)
            out.append({
                'job_id': row.get('job_id', ''),
                'Tiêu đề': row.get('title', ''),
                'Công ty': row.get('company_name', ''),
                'Tổng điểm (%)': composite,
                'Độ phù hợp (%)': composite,  # Alias tương thích UI
                'Điểm kỹ năng (%)': None if np.isnan(c['skills']) else round(c['skills'] * 100, 1),
                'Điểm văn bản (%)': round(c['text'] * 100, 1),
                'Cosine gốc (%)': round(float(sc['raw_sim'][idx]) * 100, 1),
                'Điểm kinh nghiệm (%)': round(c['exp'] * 100, 1),
                'Điểm vị trí/hình thức (%)': round(c['loc'] * 100, 1),
                'Lời giải thích': generate_rationale(matched, missing, user_exp, row.get('experience_min'),
                                                     row.get('work_mode', 'Onsite'), sal_fit, related),
                'Độ phủ kỹ năng (%)': f"{coverage_pct}% ({len(matched)}/{len(req)})",
                'Kỹ năng đã có (Điểm mạnh)': ', '.join(matched[:4]) if matched else 'Khớp theo vị trí/mô tả',
                'Kỹ năng gần nhau': ', '.join(related[:4]),
                'Kỹ năng còn thiếu (Gap)': ', '.join(missing[:4]) if missing else 'Đầy đủ',
                'Kinh nghiệm yêu cầu': f"{row.get('experience_min')} năm" if pd.notnull(row.get('experience_min')) else 'Không yêu cầu',
                'Hình thức': row.get('work_mode', 'Onsite'),
                'Thành phố': row.get('city', 'Không rõ'),
                'Mức lương': format_salary_display(row.get('salary_min'), row.get('salary_max')),
                'job_url': row.get('job_url', ''),
                'company_logo_url': row.get('company_logo_url', ''),
            })
        return pd.DataFrame(out)

    def analyze_cv_fit_for_job(
        self,
        job_identifier: Union[int, str],
        cv_text: str = "",
        skills: Optional[List[str]] = None,
        user_exp: float = 1.0,
        target_title: str = "",
        preferred_city: str = "Tất cả",
        preferred_work_modes: Optional[Union[str, List[str]]] = None,
        min_salary: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Báo cáo 1:1 giữa hồ sơ và một job. Dùng chung score_components/combine_scores với recommend()
        nên Tổng điểm và thứ hạng khớp với bảng gợi ý khi truyền cùng tham số hồ sơ.
        job_identifier: job_id (khuyên dùng), chỉ số dòng, hoặc một đoạn của tiêu đề.
        """
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

        sc = self.score_components(target_title, cv_text, skills, user_exp, preferred_city, preferred_work_modes, min_salary)
        if sc is None:
            return "Vui lòng cung cấp ít nhất một thông tin: tiêu đề, kỹ năng hoặc văn bản CV."
        total = self.combine_scores(sc['comps'], weights)
        rank = int((np.where(sc['active'], total, -1.0) > total[idx]).sum()) + 1

        job, c = self.jobs_df.iloc[idx], sc['comps'].iloc[idx]
        req = job['req_list']
        matched, related, missing = split_skill_match(sc['user_skills'], req)
        fmt = lambda v: "không có dữ liệu (bỏ qua)" if np.isnan(v) else f"{v * 100:.1f}%"
        exp_req = job.get('experience_min') if pd.notnull(job.get('experience_min')) else 0.0
        exp_status = (f"Đạt yêu cầu ({user_exp} năm >= {exp_req} năm)" if user_exp >= exp_req
                      else f"Chưa đủ kinh nghiệm ({user_exp} năm < yêu cầu {exp_req} năm)")
        coverage = (f"{len(matched)}/{len(req)} kỹ năng, thêm {len(related)} kỹ năng gần nhau tính 0,5" if req
                    else "job không liệt kê kỹ năng")

        return f"""================================================================================
BÁO CÁO ĐÁNH GIÁ ĐỘ PHÙ HỢP HỒ SƠ VỚI CÔNG VIỆC (1:1 FIT REPORT)
================================================================================
Công việc mục tiêu: {job.get('title')}
Công ty:             {job.get('company_name')}
Địa điểm:            {job.get('city')} ({job.get('work_mode', 'Tại văn phòng')})
Mức lương:           {format_salary_display(job.get('salary_min'), job.get('salary_max'))}

--- 1. TỔNG ĐIỂM ---
• Tổng điểm: {total[idx] * 100:.1f}%   |   Xếp hạng: {rank}/{int(sc['active'].sum())} tin còn hạn

--- 2. CÁC ĐIỂM THÀNH PHẦN (cùng công thức với recommend) ---
• Kỹ năng         : {fmt(c['skills'])}   (khớp {coverage})
• Văn bản         : {fmt(c['text'])}   (cosine gốc {sc['raw_sim'][idx] * 100:.1f}%, đã chuẩn hóa theo job giống nhất)
• Kinh nghiệm     : {fmt(c['exp'])}   ({exp_status})
• Vị trí/hình thức: {fmt(c['loc'])}
• Lương           : {fmt(c['sal'])}

--- 3. CHI TIẾT KỸ NĂNG ---
Kỹ năng bạn đã có ({len(matched)}):
   {', '.join(matched) if matched else 'Chưa trùng trực tiếp kỹ năng công nghệ'}
Kỹ năng gần với kỹ năng bạn có, học thêm nhanh ({len(related)}):
   {', '.join(related) if related else 'Không có'}
Kỹ năng còn thiếu mà công ty yêu cầu ({len(missing)}):
   {', '.join(missing) if missing else 'Tuyệt vời! Bạn đáp ứng đầy đủ tất cả kỹ năng'}
================================================================================"""


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
