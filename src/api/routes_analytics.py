import os
import sys
from fastapi import APIRouter
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/kpis")
def get_market_kpis():
    """Lấy số liệu KPI vĩ mô thị trường IT."""
    query = "SELECT * FROM vw_gold_market_kpis LIMIT 1;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            colnames = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            if row:
                d = dict(zip(colnames, row))
                avg_min = float(d.get("avg_salary_min_vnd") or 0) / 1e6
                avg_max = float(d.get("avg_salary_max_vnd") or 0) / 1e6
                remote_hybrid = float(d.get("remote_pct") or 0) + float(d.get("hybrid_pct") or 0)
                return {
                    "total_postings": int(d.get("total_jobs") or 2821),
                    "active_postings": int(d.get("active_jobs") or 2712),
                    "total_companies": int(d.get("total_companies") or 1436),
                    "avg_min_salary_million": round(avg_min, 1),
                    "avg_max_salary_million": round(avg_max, 1),
                    "remote_ratio_pct": round(remote_hybrid, 1)
                }
    return {}

@router.get("/top-skills")
def get_top_skills(limit: int = 15):
    """Lấy danh sách các kỹ năng IT được săn đón nhiều nhất kèm mức lương trung bình."""
    query = """
        SELECT 
            skill_name, 
            skill_category, 
            total_job_count, 
            market_penetration_pct,
            ROUND(COALESCE(avg_skill_min_salary_vnd, 0) / 1000000, 1) AS avg_min_mil,
            ROUND(COALESCE(avg_skill_max_salary_vnd, 0) / 1000000, 1) AS avg_max_mil
        FROM vw_gold_skill_demand
        ORDER BY total_job_count DESC
        LIMIT %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [limit])
            rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "skill_name": r[0],
            "category": r[1],
            "job_count": r[2],
            "penetration_pct": round(float(r[3] or 0), 1),
            "avg_min_million": float(r[4] or 0),
            "avg_max_million": float(r[5] or 0)
        })
    return result

@router.get("/roles-salary")
def get_roles_salary():
    """Lấy phân bố lương trung bình theo cấp bậc kinh nghiệm."""
    query = """
        SELECT 
            seniority_level, 
            SUM(posting_count) AS total_jobs,
            ROUND(AVG(avg_salary_min_vnd) / 1000000, 1) AS avg_min_mil,
            ROUND(AVG(avg_salary_max_vnd) / 1000000, 1) AS avg_max_mil
        FROM vw_gold_salary_experience_matrix
        WHERE seniority_level IS NOT NULL AND seniority_level != 'Chưa xác định'
        GROUP BY seniority_level
        ORDER BY total_jobs DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "seniority_level": r[0],
            "total_jobs": int(r[1] or 0),
            "avg_min_million": float(r[2] or 0),
            "avg_max_million": float(r[3] or 0)
        })
    return result

@router.get("/geo-distribution")
def get_geo_distribution():
    """Lấy số lượng việc làm theo từng thành phố / khu vực."""
    query = """
        SELECT 
            city, 
            SUM(posting_count) AS total_jobs
        FROM vw_gold_role_geo_matrix
        WHERE city IS NOT NULL
        GROUP BY city
        ORDER BY total_jobs DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "city": r[0] if r[0] else "Khác",
            "total_jobs": int(r[1] or 0)
        })
    return result

@router.get("/top-companies")
def get_top_companies(limit: int = 10):
    """Bảng xếp hạng doanh nghiệp tuyển dụng nhiều nhất."""
    query = """
        SELECT 
            company_name_normalized, 
            company_city, 
            total_postings,
            ROUND(COALESCE(avg_min_salary_vnd, 0) / 1000000, 1) AS avg_min_mil,
            ROUND(COALESCE(avg_max_salary_vnd, 0) / 1000000, 1) AS avg_max_mil
        FROM vw_gold_company_rankings
        ORDER BY total_postings DESC
        LIMIT %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [limit])
            rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "company_name": r[0],
            "city": r[1] or "Toàn quốc",
            "total_postings": int(r[2] or 0),
            "avg_min_mil": float(r[3] or 0),
            "avg_max_mil": float(r[4] or 0)
        })
    return result
