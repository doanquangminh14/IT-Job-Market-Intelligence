import os
import sys
import math
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

def format_salary_display(min_vnd, max_vnd, sal_type):
    try:
        min_v = float(min_vnd) if min_vnd is not None and pd.notna(min_vnd) else 0.0
    except Exception:
        min_v = 0.0
    try:
        max_v = float(max_vnd) if max_vnd is not None and pd.notna(max_vnd) else 0.0
    except Exception:
        max_v = 0.0

    has_min = min_v > 0
    has_max = max_v > 0

    def _fmt_mil(val):
        v = val / 1e6
        return f"{int(round(v))}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"

    if has_min and has_max:
        if round(min_v / 1e6, 1) == round(max_v / 1e6, 1):
            return f"{_fmt_mil(min_v)} triệu VNĐ"
        return f"{_fmt_mil(min_v)} - {_fmt_mil(max_v)} triệu VNĐ"
    elif has_max:
        return f"Lên tới {_fmt_mil(max_v)} triệu VNĐ"
    elif has_min:
        return f"Từ {_fmt_mil(min_v)} triệu VNĐ"
    elif sal_type == "negotiable":
        return "Thỏa thuận"
    return "Cạnh tranh"

@router.get("/filter-options")
def get_filter_options():
    """Lấy danh sách các giá trị phân loại để hiển thị lên bộ lọc phía Client."""
    query = """
        SELECT 
            DISTINCT city, seniority_level, work_mode
        FROM jobs
        WHERE is_active = TRUE;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    cities = set()
    seniorities = set()
    work_modes = set()

    for r in rows:
        if r[0]: cities.add(r[0])
        if r[1]: seniorities.add(r[1])
        if r[2]: work_modes.add(r[2])

    sorted_cities = ["Tất cả"] + sorted([c for c in cities if c != "Khác"]) + (["Khác"] if "Khác" in cities else [])
    sorted_seniorities = ["Tất cả"] + sorted(list(seniorities))
    sorted_modes = ["Tất cả"] + sorted(list(work_modes))

    return {
        "cities": sorted_cities,
        "seniorities": sorted_seniorities,
        "work_modes": sorted_modes
    }

@router.get("/search")
def search_jobs(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    city: Optional[str] = Query("Tất cả", description="Thành phố"),
    seniority: Optional[str] = Query("Tất cả", description="Cấp bậc"),
    work_mode: Optional[str] = Query("Tất cả", description="Hình thức làm việc"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(15, ge=1, le=50, description="Số tin mỗi trang")
):
    """
    Tìm kiếm và lọc tin tuyển dụng kèm phân trang và nạp đầy đủ logo công ty và kỹ năng.
    """
    # Trích xuất giá trị nguyên thủy an toàn khi gọi trực tiếp hoặc qua FastAPI
    kw_str = str(keyword.default if hasattr(keyword, "default") else (keyword or "")).strip()
    city_str = str(city.default if hasattr(city, "default") else (city or "Tất cả")).strip()
    seniority_str = str(seniority.default if hasattr(seniority, "default") else (seniority or "Tất cả")).strip()
    work_mode_str = str(work_mode.default if hasattr(work_mode, "default") else (work_mode or "Tất cả")).strip()
    page_num = int(page.default if hasattr(page, "default") else page)
    size_num = int(page_size.default if hasattr(page_size, "default") else page_size)

    where_clauses = ["j.is_active = TRUE"]
    params = []

    if kw_str:
        kw = f"%{kw_str}%"
        where_clauses.append("(j.title_normalized ILIKE %s OR c.company_name_normalized ILIKE %s OR j.location_raw ILIKE %s)")
        params.extend([kw, kw, kw])

    if city_str and city_str != "Tất cả":
        where_clauses.append("j.city = %s")
        params.append(city_str)

    if seniority_str and seniority_str != "Tất cả":
        where_clauses.append("j.seniority_level = %s")
        params.append(seniority_str)

    if work_mode_str and work_mode_str != "Tất cả":
        where_clauses.append("j.work_mode = %s")
        params.append(work_mode_str)

    where_sql = " AND ".join(where_clauses)
    offset = (page_num - 1) * size_num

    count_query = f"""
        SELECT COUNT(DISTINCT j.job_id)
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.company_id
        WHERE {where_sql};
    """

    data_query = f"""
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
            sr.source_job_url,
            COALESCE(STRING_AGG(DISTINCT s.skill_name, ', '), '') AS skills_str,
            LEFT(d.description_clean, 200) AS desc_snippet
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.company_id
        LEFT JOIN job_descriptions d ON j.job_id = d.job_id
        LEFT JOIN job_source_records sr ON j.job_id = sr.job_id
        LEFT JOIN job_skills js ON j.job_id = js.job_id
        LEFT JOIN skills s ON js.skill_id = s.skill_id
        WHERE {where_sql}
        GROUP BY 
            j.job_id, j.title_normalized, j.seniority_level, j.city, j.work_mode,
            j.salary_type, j.salary_min_vnd, j.salary_max_vnd, j.experience_raw, j.deadline,
            c.company_name_normalized, c.company_logo_url, sr.source_job_url, d.description_clean
        ORDER BY j.job_id DESC
        LIMIT %s OFFSET %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(count_query, params)
            total_records = cur.fetchone()[0]

            data_params = params + [size_num, offset]
            cur.execute(data_query, data_params)
            rows = cur.fetchall()

    jobs_list = []
    for r in rows:
        job_id = r[0]
        title = r[1] or ""
        seniority_level = r[2] or "Chưa xác định"
        job_city = r[3] or "Khác"
        mode = r[4] or "Onsite"
        sal_type = r[5]
        min_sal = r[6]
        max_sal = r[7]
        exp_raw = (r[8] or "Không yêu cầu").strip()
        deadline_val = r[9]
        comp_name = r[10] or "Doanh nghiệp IT"
        comp_logo = (r[11] or "").strip()
        job_url = r[12] or ""
        skills_str = r[13] or ""
        desc_snippet = (r[14] or "").strip()

        salary_display = format_salary_display(min_sal, max_sal, sal_type)
        deadline_str = deadline_val.strftime("%d/%m/%Y") if deadline_val and hasattr(deadline_val, "strftime") else ""
        skills = [s.strip() for s in skills_str.split(",") if s.strip()]

        jobs_list.append({
            "job_id": job_id,
            "title": title,
            "company_name": comp_name,
            "company_logo_url": comp_logo,
            "city": job_city,
            "work_mode": mode,
            "seniority_level": seniority_level,
            "salary_display": salary_display,
            "experience_str": exp_raw,
            "deadline_str": deadline_str,
            "skills": skills,
            "description_snippet": desc_snippet + ("..." if len(desc_snippet) >= 190 else ""),
            "url": job_url
        })

    total_pages = math.ceil(total_records / size_num) if total_records > 0 else 1

    return {
        "total": total_records,
        "page": page_num,
        "page_size": size_num,
        "total_pages": total_pages,
        "jobs": jobs_list
    }

@router.get("/{job_id}")
def get_job_detail(job_id: int):
    """Lấy chi tiết tin việc làm phục vụ hiển thị Modal chi tiết."""
    query = """
        SELECT 
            j.job_id,
            j.title_normalized,
            j.seniority_level,
            j.city,
            j.location_raw,
            j.work_mode,
            j.salary_type,
            j.salary_min_vnd,
            j.salary_max_vnd,
            j.experience_raw,
            j.deadline,
            j.published_at,
            c.company_name_normalized AS company_name,
            c.company_logo_url,
            c.company_url,
            sr.source_job_url,
            d.description_clean,
            d.requirements_clean,
            d.benefits_raw,
            d.overview_raw,
            COALESCE(STRING_AGG(DISTINCT s.skill_name, ', '), '') AS skills_str
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.company_id
        LEFT JOIN job_descriptions d ON j.job_id = d.job_id
        LEFT JOIN job_source_records sr ON j.job_id = sr.job_id
        LEFT JOIN job_skills js ON j.job_id = js.job_id
        LEFT JOIN skills s ON js.skill_id = s.skill_id
        WHERE j.job_id = %s
        GROUP BY 
            j.job_id, j.title_normalized, j.seniority_level, j.city, j.location_raw,
            j.work_mode, j.salary_type, j.salary_min_vnd, j.salary_max_vnd,
            j.experience_raw, j.deadline, j.published_at,
            c.company_name_normalized, c.company_logo_url, c.company_url,
            sr.source_job_url, d.description_clean, d.requirements_clean, d.benefits_raw, d.overview_raw;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [job_id])
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy việc làm này")

    skills_str = row[20] or ""
    skills = [s.strip() for s in skills_str.split(",") if s.strip()]

    return {
        "job_id": row[0],
        "title": row[1] or "",
        "seniority_level": row[2] or "Chưa xác định",
        "city": row[3] or "Khác",
        "location_raw": row[4] or "",
        "work_mode": row[5] or "Onsite",
        "salary_display": format_salary_display(row[7], row[8], row[6]),
        "experience_str": (row[9] or "Không yêu cầu").strip(),
        "deadline_str": row[10].strftime("%d/%m/%Y") if row[10] and hasattr(row[10], "strftime") else "Đang nhận hồ sơ",
        "published_str": row[11].strftime("%d/%m/%Y") if row[11] and hasattr(row[11], "strftime") else "",
        "company_name": row[12] or "Doanh nghiệp IT",
        "company_logo_url": (row[13] or "").strip(),
        "company_url": row[14] or "",
        "source_job_url": row[15] or "",
        "description": row[16] or "Đang cập nhật nội dung mô tả công việc.",
        "requirements": row[17] or "Đang cập nhật yêu cầu chuyên môn.",
        "benefits": row[18] or "Đang cập nhật chế độ đãi ngộ.",
        "company_overview": (row[19] or "").strip(),
        "skills": skills
    }
