-- ==============================================================================
-- IT JOB MARKET INTELLIGENCE - POSTGRESQL SILVER LAYER SCHEMA
-- Phiên bản: 1.0 (Production Ready)
-- Tác giả: Data Engineering Team
-- Mô tả: Mô hình dữ liệu chuẩn hóa 3NF kết hợp Dimensional Modeling cho dữ liệu
--        thị trường việc làm IT Việt Nam (TopCV, TopDev, VietnamWorks).
-- ==============================================================================

-- Bật extension mở rộng nếu cần (UUID, Unaccent, Trigram search)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ------------------------------------------------------------------------------
-- 1. BẢNG DIMENSION: companies (Thông Tin Doanh Nghiệp)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS job_skills CASCADE;
DROP TABLE IF EXISTS job_descriptions CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS skills CASCADE;

CREATE TABLE companies (
    company_id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name_raw        TEXT NOT NULL,
    company_name_normalized TEXT NOT NULL,
    website_domain          VARCHAR(255),
    company_url             TEXT,
    company_logo_url        TEXT,
    company_size_raw        TEXT,
    company_size_min        INTEGER,
    company_size_max        INTEGER,
    company_location_raw    TEXT,
    company_city            VARCHAR(100),
    industry_raw            TEXT,
    industry_normalized     VARCHAR(255),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE companies IS 'Bảng chiều thông tin doanh nghiệp (Dimension Company), khử trùng lặp và lưu quy mô, ngành nghề';
COMMENT ON COLUMN companies.company_id IS 'Khóa chính nội bộ tự tăng';
COMMENT ON COLUMN companies.company_name_raw IS 'Tên công ty nguyên bản thu thập từ sàn';
COMMENT ON COLUMN companies.company_name_normalized IS 'Tên công ty đã làm sạch tiền tố pháp lý (Công ty Cổ phần, TNHH...)';
COMMENT ON COLUMN companies.website_domain IS 'Tên miền website trích xuất (ví dụ fpt.com) dùng làm khóa khử trùng lặp tự nhiên';
COMMENT ON COLUMN companies.company_size_min IS 'Quy mô nhân viên tối thiểu sau khi bóc tách số';
COMMENT ON COLUMN companies.company_size_max IS 'Quy mô nhân viên tối đa sau khi bóc tách số';
COMMENT ON COLUMN companies.company_city IS 'Tỉnh/thành phố đặt trụ sở chính chuẩn hóa';

-- Indexes cho companies
CREATE INDEX idx_companies_name_norm ON companies(company_name_normalized);
CREATE INDEX idx_companies_domain ON companies(website_domain);
CREATE INDEX idx_companies_city ON companies(company_city);


-- ------------------------------------------------------------------------------
-- 2. BẢNG FACT/CORE: jobs (Bản Ghi Việc Làm Chuẩn Hóa Cốt Lõi)
-- ------------------------------------------------------------------------------
CREATE TABLE jobs (
    job_id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source                  VARCHAR(50) NOT NULL,
    source_job_id           VARCHAR(100) NOT NULL,
    job_url                 TEXT NOT NULL,
    canonical_job_id        BIGINT,
    company_id              BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- Vị trí & Cấp bậc
    title_raw               TEXT NOT NULL,
    title_normalized        TEXT NOT NULL,
    seniority_level         VARCHAR(50) DEFAULT 'Undetermined',
    
    -- Địa điểm & Hình thức
    location_raw            TEXT,
    city                    VARCHAR(100),
    work_mode_raw           TEXT,
    work_mode               VARCHAR(20) DEFAULT 'unknown',
    employment_type         VARCHAR(50) DEFAULT 'Full-time',
    working_time_raw        TEXT,
    
    -- Lương (Mức lương nguyên bản & Quy đổi chuẩn)
    salary_raw              TEXT,
    salary_min              NUMERIC(14, 2),
    salary_max              NUMERIC(14, 2),
    salary_currency         VARCHAR(10) DEFAULT 'VND',
    salary_period           VARCHAR(20) DEFAULT 'month',
    salary_type             VARCHAR(30) DEFAULT 'negotiable',
    salary_min_vnd          NUMERIC(14, 2),
    salary_max_vnd          NUMERIC(14, 2),
    
    -- Kinh nghiệm & Học vấn
    experience_raw          TEXT,
    experience_min_years    NUMERIC(4, 1),
    experience_max_years    NUMERIC(4, 1),
    education_raw           TEXT,
    education_level         VARCHAR(50) DEFAULT 'Không yêu cầu',
    
    -- Mốc thời gian & Trạng thái hoạt động
    published_at            TIMESTAMPTZ,
    updated_at_source       TIMESTAMPTZ,
    deadline                TIMESTAMPTZ,
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Ràng buộc toàn vẹn
    CONSTRAINT uq_jobs_source_job_id UNIQUE (source, source_job_id),
    CONSTRAINT fk_jobs_canonical FOREIGN KEY (canonical_job_id) REFERENCES jobs(job_id) ON DELETE SET NULL
);

COMMENT ON TABLE jobs IS 'Bảng trung tâm hệ thống (Core Fact Job), chứa mọi thuộc tính đo lường và phân loại chuẩn hóa';
COMMENT ON COLUMN jobs.source IS 'Nguồn tuyển dụng: topcv | topdev | vietnamworks';
COMMENT ON COLUMN jobs.source_job_id IS 'Mã ID bài đăng nguyên bản từ sàn';
COMMENT ON COLUMN jobs.job_url IS 'Đường dẫn liên kết trực tiếp tới tin tuyển dụng';
COMMENT ON COLUMN jobs.canonical_job_id IS 'ID của bài đăng đại diện nếu tin này bị trùng lặp trên sàn khác (Cross-Portal Deduplication)';
COMMENT ON COLUMN jobs.seniority_level IS 'Cấp bậc phân tích: Intern | Fresher | Junior | Middle | Senior | Lead | Manager | Director';
COMMENT ON COLUMN jobs.salary_type IS 'Loại lương: range (khoảng) | fixed (cố định) | min_only | max_only | negotiable (thỏa thuận) | undisclosed';
COMMENT ON COLUMN jobs.salary_min_vnd IS 'Mức lương sàn tối thiểu đã quy đổi thống nhất về VNĐ/tháng để làm Dashboard';
COMMENT ON COLUMN jobs.salary_max_vnd IS 'Mức lương trần tối đa đã quy đổi thống nhất về VNĐ/tháng để làm Dashboard';
COMMENT ON COLUMN jobs.is_active IS 'Trạng thái còn hiển thị hoạt động trên thị trường';

-- Indexes cho jobs
CREATE INDEX idx_jobs_company_id ON jobs(company_id);
CREATE INDEX idx_jobs_city ON jobs(city);
CREATE INDEX idx_jobs_seniority ON jobs(seniority_level);
CREATE INDEX idx_jobs_work_mode ON jobs(work_mode);
CREATE INDEX idx_jobs_is_active ON jobs(is_active);
CREATE INDEX idx_jobs_published_at ON jobs(published_at DESC);
CREATE INDEX idx_jobs_salary_vnd ON jobs(salary_min_vnd, salary_max_vnd) WHERE salary_min_vnd IS NOT NULL;
CREATE INDEX idx_jobs_title_trgm ON jobs USING gin (title_normalized gin_trgm_ops);


-- ------------------------------------------------------------------------------
-- 3. BẢNG HEAVY TEXT / NLP: job_descriptions (Nội Dung Chi Tiết Văn Bản)
-- ------------------------------------------------------------------------------
CREATE TABLE job_descriptions (
    job_id                  BIGINT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
    overview_raw            TEXT,
    responsibilities_raw    TEXT,
    requirements_raw        TEXT,
    benefits_raw            TEXT,
    description_clean       TEXT,
    requirements_clean      TEXT,
    benefits_clean          TEXT,
    language                VARCHAR(10) DEFAULT 'vi',
    text_hash               VARCHAR(64) NOT NULL,
    cleaned_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE job_descriptions IS 'Bảng tách riêng văn bản dài phục vụ NLP, trích xuất thực thể, Embedding và Semantic Search';
COMMENT ON COLUMN job_descriptions.job_id IS 'Khóa chính và khóa ngoại quan hệ 1-1 với bảng jobs';
COMMENT ON COLUMN job_descriptions.description_clean IS 'Văn bản mô tả đã làm sạch thẻ HTML và chuẩn hóa khoảng trắng';
COMMENT ON COLUMN job_descriptions.requirements_clean IS 'Yêu cầu tuyển dụng đã làm sạch phục vụ bóc tách kỹ năng';
COMMENT ON COLUMN job_descriptions.language IS 'Ngôn ngữ của JD: vi (Tiếng Việt) | en (Tiếng Anh) | vi-en (Song ngữ)';
COMMENT ON COLUMN job_descriptions.text_hash IS 'Mã SHA256 nhận diện biến động nội dung bài đăng giữa các lần crawl';

-- Indexes cho job_descriptions
CREATE INDEX idx_job_descriptions_language ON job_descriptions(language);
CREATE INDEX idx_job_descriptions_text_hash ON job_descriptions(text_hash);


-- ------------------------------------------------------------------------------
-- 4. BẢNG DIMENSION: skills (Danh Mục Kỹ Năng Chuẩn Hóa Toàn Hệ Thống)
-- ------------------------------------------------------------------------------
CREATE TABLE skills (
    skill_id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id               BIGINT REFERENCES skills(skill_id) ON DELETE SET NULL,
    skill_name              VARCHAR(100) NOT NULL,
    skill_normalized        VARCHAR(100) NOT NULL UNIQUE,
    skill_category          VARCHAR(100) NOT NULL,
    description             TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE skills IS 'Danh mục kỹ năng CNTT chuẩn hóa dùng chung toàn hệ thống';
COMMENT ON COLUMN skills.parent_id IS 'Khóa tự tham chiếu tạo cây phân cấp kỹ năng (Ví dụ FastAPI -> Python, Next.js -> React)';
COMMENT ON COLUMN skills.skill_name IS 'Tên kỹ năng hiển thị (Python, React, AWS, Docker...)';
COMMENT ON COLUMN skills.skill_normalized IS 'Tên chuẩn hóa chữ thường duy nhất (python, react, aws...)';
COMMENT ON COLUMN skills.skill_category IS 'Nhóm: Programming Language | Database | Cloud & DevOps | AI / ML | Testing | BI...';

-- Indexes cho skills
CREATE INDEX idx_skills_category ON skills(skill_category);
CREATE INDEX idx_skills_parent ON skills(parent_id);


-- ------------------------------------------------------------------------------
-- 5. BẢNG BRIDGE (N - N): job_skills (Mối Liên Kết Việc Làm Và Kỹ Năng)
-- ------------------------------------------------------------------------------
CREATE TABLE job_skills (
    job_id                  BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_id                BIGINT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    skill_type              VARCHAR(20) NOT NULL DEFAULT 'required',
    extraction_method       VARCHAR(50) NOT NULL DEFAULT 'rule_based',
    confidence              NUMERIC(4, 3) NOT NULL DEFAULT 1.000,
    evidence_text           TEXT,
    extracted_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (job_id, skill_id, skill_type)
);

COMMENT ON TABLE job_skills IS 'Bảng liên kết nhiều-nhiều (N-N) giữa tin tuyển dụng và kỹ năng yêu cầu';
COMMENT ON COLUMN job_skills.skill_type IS 'Loại kỹ năng: required (bắt buộc) | preferred (ưu tiên/điểm cộng) | mentioned (nhắc tới)';
COMMENT ON COLUMN job_skills.extraction_method IS 'Phương thức: tag_direct (tag sàn) | rule_based (regex trong JD) | nlp (mô hình AI)';
COMMENT ON COLUMN job_skills.confidence IS 'Độ tin cậy của thuật toán trích xuất (từ 0.000 đến 1.000)';
COMMENT ON COLUMN job_skills.evidence_text IS 'Trích đoạn ngữ cảnh làm bằng chứng (phục vụ giải thích gợi ý - Explainable AI)';

-- Indexes cho job_skills
CREATE INDEX idx_job_skills_job_id ON job_skills(job_id);
CREATE INDEX idx_job_skills_skill_id ON job_skills(skill_id);
CREATE INDEX idx_job_skills_type ON job_skills(skill_type);


-- ------------------------------------------------------------------------------
-- 6. TRIGGER TỰ ĐỘNG CẬP NHẬT updated_at KHI CÓ THAY ĐỔI DỮ LIỆU
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_companies
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp_jobs
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp_skills
BEFORE UPDATE ON skills
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();
