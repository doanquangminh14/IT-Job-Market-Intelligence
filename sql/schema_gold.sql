-- ==============================================================================
-- DỰ ÁN: IT JOB MARKET INTELLIGENCE
-- PHÂN TẦNG: GOLD LAYER (ANALYTICAL VIEWS & DATA MARTS)
-- MỤC TIÊU: TỐI ƯU HÓA TRUY VẤN CHO STREAMLIT DASHBOARD VÀ BÁO CÁO BI
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. VIEW TỔNG QUAN CHỈ SỐ TOÀN THỊ TRƯỜNG (MARKET OVERVIEW KPIS)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_market_kpis AS
SELECT
    (SELECT COUNT(*) FROM jobs) AS total_jobs,
    (SELECT COUNT(*) FROM jobs WHERE is_active) AS active_jobs,
    (SELECT COUNT(*) FROM companies) AS total_companies,
    (SELECT COUNT(DISTINCT skill_id) FROM job_skills) AS total_unique_skills,
    (SELECT ROUND(AVG(salary_min_vnd), 0) FROM jobs WHERE salary_min_vnd IS NOT NULL) AS avg_salary_min_vnd,
    (SELECT ROUND(AVG(salary_max_vnd), 0) FROM jobs WHERE salary_max_vnd IS NOT NULL) AS avg_salary_max_vnd,
    (SELECT ROUND(COUNT(CASE WHEN work_mode = 'Remote' THEN 1 END)::numeric / COUNT(*) * 100, 2) FROM jobs) AS remote_pct,
    (SELECT ROUND(COUNT(CASE WHEN work_mode = 'Hybrid' THEN 1 END)::numeric / COUNT(*) * 100, 2) FROM jobs) AS hybrid_pct,
    (SELECT ROUND(COUNT(CASE WHEN work_mode = 'Onsite' THEN 1 END)::numeric / COUNT(*) * 100, 2) FROM jobs) AS onsite_pct;


-- ------------------------------------------------------------------------------
-- 2. VIEW PHÂN BỐ VỊ TRÍ VIỆC LÀM & ĐỊA ĐIỂM (ROLE & GEOGRAPHY MATRIX)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_role_geo_matrix AS
SELECT
    j.title_normalized,
    j.seniority_level,
    j.city,
    j.work_mode,
    j.employment_type,
    COUNT(j.job_id) AS posting_count,
    ROUND(AVG(j.salary_min_vnd), 0) AS avg_min_salary_vnd,
    ROUND(AVG(j.salary_max_vnd), 0) AS avg_max_salary_vnd
FROM jobs j
GROUP BY j.title_normalized, j.seniority_level, j.city, j.work_mode, j.employment_type;


-- ------------------------------------------------------------------------------
-- 3. VIEW BẢNG XẾP HẠNG DOANH NGHIỆP TUYỂN DỤNG (TOP HIRING COMPANIES)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_company_rankings AS
SELECT
    c.company_id,
    c.company_name_normalized,
    COALESCE(c.company_city, 'Chưa xác định') AS company_city,
    COALESCE(c.industry_normalized, 'Công nghệ thông tin') AS industry,
    c.company_size_min,
    c.company_size_max,
    COUNT(j.job_id) AS total_postings,
    COUNT(CASE WHEN j.is_active THEN 1 END) AS active_postings,
    ROUND(AVG(j.salary_min_vnd), 0) AS avg_min_salary_vnd,
    ROUND(AVG(j.salary_max_vnd), 0) AS avg_max_salary_vnd
FROM companies c
JOIN jobs j ON c.company_id = j.company_id
GROUP BY c.company_id, c.company_name_normalized, c.company_city, c.industry_normalized, c.company_size_min, c.company_size_max;


-- ------------------------------------------------------------------------------
-- 4. VIEW NHU CẦU KỸ NĂNG VÀ PHÂN LOẠI BẮT BUỘC / ƯU TIÊN (SKILL DEMAND)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_skill_demand AS
SELECT
    s.skill_id,
    s.skill_name,
    s.skill_category,
    COUNT(js.job_id) AS total_job_count,
    COUNT(CASE WHEN js.skill_type = 'required' THEN 1 END) AS required_count,
    COUNT(CASE WHEN js.skill_type = 'preferred' THEN 1 END) AS preferred_count,
    ROUND(COUNT(js.job_id)::numeric / 2509 * 100, 2) AS market_penetration_pct,
    ROUND(AVG(j.salary_min_vnd), 0) AS avg_skill_min_salary_vnd,
    ROUND(AVG(j.salary_max_vnd), 0) AS avg_skill_max_salary_vnd
FROM skills s
JOIN job_skills js ON s.skill_id = js.skill_id
JOIN jobs j ON js.job_id = j.job_id
GROUP BY s.skill_id, s.skill_name, s.skill_category;


-- ------------------------------------------------------------------------------
-- 5. VIEW MA TRẬN ĐỒNG XUẤT HIỆN KỸ NĂNG (SKILL CO-OCCURRENCE)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_skill_cooccurrence AS
SELECT
    s1.skill_name AS skill_a,
    s2.skill_name AS skill_b,
    s1.skill_category AS category_a,
    s2.skill_category AS category_b,
    COUNT(*) AS cooccurrence_count
FROM job_skills js1
JOIN job_skills js2 ON js1.job_id = js2.job_id AND js1.skill_id < js2.skill_id
JOIN skills s1 ON js1.skill_id = s1.skill_id
JOIN skills s2 ON js2.skill_id = s2.skill_id
GROUP BY s1.skill_name, s2.skill_name, s1.skill_category, s2.skill_category
HAVING COUNT(*) >= 5;


-- ------------------------------------------------------------------------------
-- 6. VIEW PHÂN BỐ LƯƠNG THEO KINH NGHIỆM VÀ CẤP BẬC (SALARY BENCHMARK)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_salary_experience_matrix AS
SELECT
    j.seniority_level,
    CASE
        WHEN j.experience_min_years = 0 AND (j.experience_max_years IS NULL OR j.experience_max_years <= 1) THEN '0 năm (Fresher/Intern)'
        WHEN j.experience_min_years = 1 OR j.experience_max_years = 1 THEN '1 năm'
        WHEN j.experience_min_years >= 2 AND j.experience_min_years <= 3 THEN '2 - 3 năm'
        WHEN j.experience_min_years > 3 AND j.experience_min_years <= 5 THEN '3 - 5 năm'
        WHEN j.experience_min_years > 5 THEN 'Trên 5 năm'
        ELSE 'Không yêu cầu / Chưa rõ'
    END AS experience_bucket,
    j.city,
    j.salary_type,
    COUNT(j.job_id) AS posting_count,
    ROUND(AVG(j.salary_min_vnd), 0) AS avg_salary_min_vnd,
    ROUND(AVG(j.salary_max_vnd), 0) AS avg_salary_max_vnd,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY j.salary_min_vnd)::numeric, 0) AS median_salary_min_vnd,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY j.salary_max_vnd)::numeric, 0) AS median_salary_max_vnd
FROM jobs j
GROUP BY j.seniority_level, experience_bucket, j.city, j.salary_type;


-- ------------------------------------------------------------------------------
-- 7. VIEW GÓC ĐỊNH HƯỚNG CHO SINH VIÊN & FRESHER (STUDENT CAREER PATH)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_student_career AS
SELECT
    j.job_id,
    j.title_normalized,
    c.company_name_normalized,
    j.city,
    j.work_mode,
    j.seniority_level,
    j.salary_type,
    j.salary_min_vnd,
    j.salary_max_vnd,
    j.deadline,
    j.is_active,
    jsr.source_job_url
FROM jobs j
JOIN companies c ON j.company_id = c.company_id
LEFT JOIN job_source_records jsr ON j.job_id = jsr.job_id
WHERE j.seniority_level IN ('Intern', 'Fresher')
   OR j.experience_min_years = 0
   OR j.title_normalized ILIKE '%intern%'
   OR j.title_normalized ILIKE '%fresher%'
   OR j.title_normalized ILIKE '%thực tập%';
