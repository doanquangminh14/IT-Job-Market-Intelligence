import os
import sys
import pandas as pd
import streamlit as st

# Đảm bảo đường dẫn import tới module nguồn src/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.pipelines.silver.db import get_db_connection

@st.cache_data(ttl=3600)
def load_market_kpis():
    """Truy vấn KPI tổng quan thị trường từ View vw_gold_market_kpis."""
    query = "SELECT * FROM vw_gold_market_kpis LIMIT 1;"
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn).iloc[0].to_dict()

@st.cache_data(ttl=3600)
def load_role_geo_matrix():
    """Truy vấn phân bố chức danh và vị trí địa lý."""
    query = """
        SELECT title_normalized, seniority_level, city, work_mode,
               posting_count, avg_min_salary_vnd, avg_max_salary_vnd
        FROM vw_gold_role_geo_matrix
        ORDER BY posting_count DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_company_rankings():
    """Truy vấn bảng xếp hạng công ty tuyển dụng nhiều nhất."""
    query = """
        SELECT company_name_normalized, company_city, industry,
               total_postings, active_postings, avg_min_salary_vnd, avg_max_salary_vnd
        FROM vw_gold_company_rankings
        ORDER BY total_postings DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_skill_demand():
    """Truy vấn nhu cầu 76 kỹ năng IT chuẩn hóa."""
    query = """
        SELECT skill_name, skill_category, total_job_count,
               required_count, preferred_count, market_penetration_pct,
               avg_skill_min_salary_vnd, avg_skill_max_salary_vnd
        FROM vw_gold_skill_demand
        ORDER BY total_job_count DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_skill_cooccurrence():
    """Truy vấn ma trận đồng xuất hiện giữa các kỹ năng."""
    query = """
        SELECT skill_a, skill_b, category_a, category_b, cooccurrence_count
        FROM vw_gold_skill_cooccurrence
        ORDER BY cooccurrence_count DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_salary_experience_matrix():
    """Truy vấn ma trận lương theo số năm kinh nghiệm và cấp bậc."""
    query = """
        SELECT seniority_level, experience_bucket, city, salary_type,
               posting_count, avg_salary_min_vnd, avg_salary_max_vnd,
               median_salary_min_vnd, median_salary_max_vnd
        FROM vw_gold_salary_experience_matrix
        ORDER BY posting_count DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_student_career_jobs():
    """Truy vấn các tin tuyển dụng dành riêng cho Thực tập sinh / Fresher."""
    query = """
        SELECT job_id, title_normalized, company_name_normalized,
               city, work_mode, seniority_level, salary_type,
               salary_min_vnd, salary_max_vnd, deadline, is_active, source_job_url
        FROM vw_gold_student_career
        ORDER BY is_active DESC, job_id ASC;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=3600)
def load_jobs_with_skills_for_comparison():
    """Truy vấn chi tiết jobs kèm danh sách kỹ năng phục vụ so sánh vai trò."""
    query = """
        SELECT j.job_id, j.title_normalized, j.seniority_level, j.city,
               j.salary_min_vnd, j.salary_max_vnd, s.skill_name, s.skill_category, js.skill_type
        FROM jobs j
        JOIN job_skills js ON j.job_id = js.job_id
        JOIN skills s ON js.skill_id = s.skill_id;
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)
