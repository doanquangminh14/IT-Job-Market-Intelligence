import os
import sys
import json
import time
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo đường dẫn gốc dự án
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDINGS_DIR = os.path.join(PROJECT_ROOT, "data", "embeddings")
EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "jobs_embeddings.npy")
METADATA_FILE = os.path.join(EMBEDDINGS_DIR, "jobs_metadata.json")

_CACHED_MODEL = None
_CACHED_EMBEDDINGS = None
_CACHED_METADATA = None

def get_embedding_model():
    """Nạp mô hình nhúng đa ngữ SentenceTransformer (cache trong RAM)."""
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        _CACHED_MODEL = SentenceTransformer(MODEL_NAME)
    return _CACHED_MODEL

def fetch_jobs_for_embedding(conn):
    """
    Truy vấn dữ liệu văn bản đã làm sạch của toàn bộ việc làm từ PostgreSQL Silver Layer.
    Bao gồm chức danh, cấp bậc, thành phố, yêu cầu, mô tả và danh sách kỹ năng liên kết.
    """
    query = """
        SELECT 
            j.job_id,
            j.title_normalized,
            j.seniority_level,
            j.city,
            j.work_mode,
            j.salary_type,
            j.salary_min_vnd,
            j.salary_max_vnd,
            j.experience_raw,
            j.deadline,
            c.company_name_normalized AS company_name,
            c.company_logo_url,
            d.requirements_clean,
            d.description_clean,
            sr.source_job_url,
            COALESCE(
                STRING_AGG(DISTINCT s.skill_name, ', '), ''
            ) AS skills_str
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.company_id
        LEFT JOIN job_descriptions d ON j.job_id = d.job_id
        LEFT JOIN job_source_records sr ON j.job_id = sr.job_id
        LEFT JOIN job_skills js ON j.job_id = js.job_id
        LEFT JOIN skills s ON js.skill_id = s.skill_id
        GROUP BY 
            j.job_id, j.title_normalized, j.seniority_level, j.city, j.work_mode,
            j.salary_type, j.salary_min_vnd, j.salary_max_vnd,
            j.experience_raw, j.deadline,
            c.company_name_normalized, c.company_logo_url,
            d.requirements_clean, d.description_clean,
            sr.source_job_url
        ORDER BY j.job_id;
    """
    return pd.read_sql_query(query, conn)

def build_job_text_representation(row):
    """
    Kết hợp các trường thông tin thành một đoạn văn bản ngữ nghĩa giàu thông tin kỹ thuật:
    Chức danh + Cấp bậc + Kỹ năng chuyên môn + Đoạn trích yêu cầu + Đoạn trích mô tả.
    """
    title = str(row.get("title_normalized", "") or "")
    seniority = str(row.get("seniority_level", "") or "")
    skills = str(row.get("skills_str", "") or "")
    req = str(row.get("requirements_clean", "") or "")[:450]
    desc = str(row.get("description_clean", "") or "")[:350]

    parts = [f"Vị trí: {title}."]
    if seniority and seniority != "Chưa xác định":
        parts.append(f"Cấp bậc: {seniority}.")
    if skills:
        parts.append(f"Kỹ năng công nghệ: {skills}.")
    if req:
        parts.append(f"Yêu cầu chuyên môn: {req}.")
    if desc:
        parts.append(f"Mô tả công việc: {desc}.")

    return " ".join(parts)

def generate_and_save_embeddings(force_recompute=False):
    """
    Sinh ma trận vector nhúng cho toàn bộ tin việc làm và lưu vào thư mục data/embeddings/.
    Nếu tệp đã tồn tại và không bật cờ force_recompute, bỏ qua bước tính toán.
    """
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

    if not force_recompute and os.path.exists(EMBEDDINGS_FILE) and os.path.exists(METADATA_FILE):
        print(f"-> Tệp embedding đã tồn tại tại {EMBEDDINGS_FILE}. Bỏ qua bước tính lại.")
        return load_embeddings_and_metadata()

    print(f"-> Bắt đầu tiến trình sinh Semantic Embedding cho toàn bộ việc làm...")
    start_time = time.time()

    with get_db_connection() as conn:
        df_jobs = fetch_jobs_for_embedding(conn)

    print(f"   Đã nạp {len(df_jobs):,} việc làm từ cơ sở dữ liệu.")

    texts_to_embed = []
    metadata_list = []

    for _, row in df_jobs.iterrows():
        text_repr = build_job_text_representation(row)
        texts_to_embed.append(text_repr)

        # Định dạng chuỗi lương chuẩn
        min_v = row.get("salary_min_vnd")
        max_v = row.get("salary_max_vnd")
        sal_type = row.get("salary_type")
        has_min = pd.notna(min_v) and min_v > 0
        has_max = pd.notna(max_v) and max_v > 0

        if has_min and has_max:
            if min_v == max_v:
                sal_str = f"{min_v/1e6:.1f} triệu VNĐ"
            else:
                sal_str = f"{min_v/1e6:.1f} - {max_v/1e6:.1f} triệu VNĐ"
        elif has_max:
            sal_str = f"Lên tới {max_v/1e6:.1f} triệu VNĐ"
        elif has_min:
            sal_str = f"Từ {min_v/1e6:.1f} triệu VNĐ"
        elif sal_type == "negotiable":
            sal_str = "Thỏa thuận"
        else:
            sal_str = "Cạnh tranh"

        # Tách danh sách kỹ năng thành list
        skills_raw = str(row.get("skills_str", "") or "")
        skills_arr = [s.strip() for s in skills_raw.split(",") if s.strip()]

        # Định dạng ngày hết hạn
        deadline_raw = row.get("deadline")
        deadline_str = ""
        if pd.notna(deadline_raw) and hasattr(deadline_raw, "strftime"):
            deadline_str = deadline_raw.strftime("%d/%m/%Y")

        # Đoạn trích mô tả công việc
        desc_raw = str(row.get("description_clean", "") or "")
        if not desc_raw:
            desc_raw = str(row.get("requirements_clean", "") or "")
        desc_snippet = desc_raw[:220].strip()
        if len(desc_raw) > 220:
            desc_snippet += "..."

        metadata_list.append({
            "job_id": int(row["job_id"]),
            "title": str(row.get("title_normalized", "") or ""),
            "seniority_level": str(row.get("seniority_level", "") or "Chưa xác định"),
            "company": str(row.get("company_name", "") or "Doanh nghiệp IT"),
            "company_logo_url": str(row.get("company_logo_url", "") or "").strip(),
            "experience_str": str(row.get("experience_raw", "") or "Không yêu cầu").strip(),
            "deadline_str": deadline_str,
            "city": str(row.get("city", "") or "Khác"),
            "work_mode": str(row.get("work_mode", "") or "Onsite"),
            "salary_str": sal_str,
            "url": str(row.get("source_job_url", "") or ""),
            "skills": skills_arr,
            "description_snippet": desc_snippet,
            "text_summary": text_repr[:250] + "..."
        })

    model = get_embedding_model()
    print(f"   Đang mã hóa {len(texts_to_embed):,} việc làm sang vector 384 chiều...")
    embeddings_matrix = model.encode(
        texts_to_embed,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # Lưu trữ ra đĩa
    np.save(EMBEDDINGS_FILE, embeddings_matrix)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"-> Hoàn thành sinh Semantic Embedding trong {elapsed:.1f} giây!")
    print(f"   Ma trận kích thước: {embeddings_matrix.shape}")
    print(f"   Đã lưu tại: {EMBEDDINGS_FILE} và {METADATA_FILE}")

    return embeddings_matrix, metadata_list

def load_embeddings_and_metadata(force_reload=False):
    """Nạp nhanh ma trận embeddings và metadata từ đĩa (có cache bộ nhớ RAM)."""
    global _CACHED_EMBEDDINGS, _CACHED_METADATA
    if not force_reload and _CACHED_EMBEDDINGS is not None and _CACHED_METADATA is not None:
        # Nếu RAM cache tồn tại nhưng thiếu các trường mở rộng mới, tự động nạp lại từ đĩa
        if len(_CACHED_METADATA) > 0 and "experience_str" in _CACHED_METADATA[0]:
            return _CACHED_EMBEDDINGS, _CACHED_METADATA

    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return generate_and_save_embeddings(force_recompute=False)

    _CACHED_EMBEDDINGS = np.load(EMBEDDINGS_FILE)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        _CACHED_METADATA = json.load(f)

    return _CACHED_EMBEDDINGS, _CACHED_METADATA

def refresh_metadata_file():
    """Làm mới lại tệp jobs_metadata.json từ cơ sở dữ liệu mà không cần tính lại vector embeddings."""
    with get_db_connection() as conn:
        df_jobs = fetch_jobs_for_embedding(conn)

    metadata_list = []
    for _, row in df_jobs.iterrows():
        text_repr = build_job_text_representation(row)

        min_v = row.get("salary_min_vnd")
        max_v = row.get("salary_max_vnd")
        sal_type = row.get("salary_type")
        has_min = pd.notna(min_v) and min_v > 0
        has_max = pd.notna(max_v) and max_v > 0

        if has_min and has_max:
            if min_v == max_v:
                sal_str = f"{min_v/1e6:.1f} triệu VNĐ"
            else:
                sal_str = f"{min_v/1e6:.1f} - {max_v/1e6:.1f} triệu VNĐ"
        elif has_max:
            sal_str = f"Lên tới {max_v/1e6:.1f} triệu VNĐ"
        elif has_min:
            sal_str = f"Từ {min_v/1e6:.1f} triệu VNĐ"
        elif sal_type == "negotiable":
            sal_str = "Thỏa thuận"
        else:
            sal_str = "Cạnh tranh"

        skills_raw = str(row.get("skills_str", "") or "")
        skills_arr = [s.strip() for s in skills_raw.split(",") if s.strip()]

        deadline_raw = row.get("deadline")
        deadline_str = ""
        if pd.notna(deadline_raw) and hasattr(deadline_raw, "strftime"):
            deadline_str = deadline_raw.strftime("%d/%m/%Y")

        desc_raw = str(row.get("description_clean", "") or "")
        if not desc_raw:
            desc_raw = str(row.get("requirements_clean", "") or "")
        desc_snippet = desc_raw[:220].strip()
        if len(desc_raw) > 220:
            desc_snippet += "..."

        metadata_list.append({
            "job_id": int(row["job_id"]),
            "title": str(row.get("title_normalized", "") or ""),
            "seniority_level": str(row.get("seniority_level", "") or "Chưa xác định"),
            "company": str(row.get("company_name", "") or "Doanh nghiệp IT"),
            "company_logo_url": str(row.get("company_logo_url", "") or "").strip(),
            "experience_str": str(row.get("experience_raw", "") or "Không yêu cầu").strip(),
            "deadline_str": deadline_str,
            "city": str(row.get("city", "") or "Khác"),
            "work_mode": str(row.get("work_mode", "") or "Onsite"),
            "salary_str": sal_str,
            "url": str(row.get("source_job_url", "") or ""),
            "skills": skills_arr,
            "description_snippet": desc_snippet,
            "text_summary": text_repr[:250] + "..."
        })

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    print(f"-> Đã làm mới {len(metadata_list):,} bản ghi metadata tại {METADATA_FILE}")
    return metadata_list

if __name__ == "__main__":
    refresh_metadata_file()
