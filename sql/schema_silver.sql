-- ==============================================================================
-- IT JOB MARKET INTELLIGENCE - POSTGRESQL SILVER LAYER SCHEMA
-- Phiên bản: 2.0 (Enterprise Architecture: Core Business + Data Engineering)
-- Tác giả: Data Engineering Team
-- Mô tả: Mô hình dữ liệu chuẩn hóa 3NF kết hợp Dimensional Modeling, hỗ trợ
--        Master Data Management (Golden Records), Time-series Snapshots,
--        và Data Quality Observability Audit.
-- ==============================================================================

-- Bật extension mở rộng cần thiết
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Dọn dẹp schema cũ nếu tạo lại
DROP TABLE IF EXISTS dq_results CASCADE;
DROP TABLE IF EXISTS job_snapshots CASCADE;
DROP TABLE IF EXISTS job_source_records CASCADE;
DROP TABLE IF EXISTS job_skills CASCADE;
DROP TABLE IF EXISTS job_descriptions CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS job_sources CASCADE;


-- ==============================================================================
-- PHÂN VÙNG 1: QUẢN LÝ NGUỒN CÀO & TRUY VẾT (DATA SOURCES & LINEAGE)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. BẢNG DIMENSION: job_sources (Danh Mục Nền Tảng Tuyển Dụng)
-- ------------------------------------------------------------------------------
CREATE TABLE job_sources (
    source_id               INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_code             VARCHAR(50) NOT NULL UNIQUE,
    source_name             VARCHAR(100) NOT NULL,
    base_url                TEXT NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE job_sources IS 'Bảng danh mục các nguồn/sàn tuyển dụng thu thập dữ liệu (TopCV, TopDev, VietnamWorks...)';
COMMENT ON COLUMN job_sources.source_code IS 'Mã định danh viết thường duy nhất của sàn: topcv | topdev | vietnamworks';
COMMENT ON COLUMN job_sources.source_name IS 'Tên hiển thị đầy đủ của sàn';

-- Khởi tạo sẵn 4 nguồn tuyển dụng của hệ thống
INSERT INTO job_sources (source_code, source_name, base_url, is_active) VALUES
('topcv', 'TopCV', 'https://www.topcv.vn', TRUE),
('topdev', 'TopDev', 'https://topdev.vn', TRUE),
('vietnamworks', 'VietnamWorks', 'https://www.vietnamworks.com', TRUE),
('itviec', 'ITViec', 'https://itviec.com', FALSE);


-- ------------------------------------------------------------------------------
-- 2. BẢNG DIMENSION: companies (Thông Tin Doanh Nghiệp)
-- ------------------------------------------------------------------------------
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

CREATE INDEX idx_companies_name_norm ON companies(company_name_normalized);
CREATE INDEX idx_companies_domain ON companies(website_domain);
CREATE INDEX idx_companies_city ON companies(company_city);


-- ==============================================================================
-- PHÂN VÙNG 2: THỰC THỂ VIỆC LÀM CỐT LÕI (CORE BUSINESS & AI ENTITIES)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 3. BẢNG FACT/CORE: jobs (Bản Ghi Chuẩn - Golden Record)
-- ------------------------------------------------------------------------------
CREATE TABLE jobs (
    job_id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    primary_source_id       INT REFERENCES job_sources(source_id) ON DELETE SET NULL,
    company_id              BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    canonical_job_id        BIGINT,
    
    -- Vị trí & Cấp bậc
    title_raw               TEXT NOT NULL,
    title_normalized        TEXT NOT NULL,
    seniority_level         VARCHAR(50) DEFAULT 'Undetermined',
    
    -- Địa điểm & Hình thức làm việc
    location_raw            TEXT,
    city                    VARCHAR(100),
    work_mode_raw           TEXT,
    work_mode               VARCHAR(20) DEFAULT 'unknown',
    employment_type         VARCHAR(50) DEFAULT 'Full-time',
    working_time_raw        TEXT,
    
    -- Mức lương (Nguyên bản & Quy đổi chuẩn)
    salary_raw              TEXT,
    salary_min              NUMERIC(14, 2),
    salary_max              NUMERIC(14, 2),
    salary_currency         VARCHAR(10) DEFAULT 'VND',
    salary_period           VARCHAR(20) DEFAULT 'month',
    salary_type             VARCHAR(30) DEFAULT 'negotiable',
    salary_min_vnd          NUMERIC(14, 2),
    salary_max_vnd          NUMERIC(14, 2),
    
    -- Kinh nghiệm & Trình độ học vấn
    experience_raw          TEXT,
    experience_min_years    NUMERIC(4, 1),
    experience_max_years    NUMERIC(4, 1),
    education_raw           TEXT,
    education_level         VARCHAR(50) DEFAULT 'Không yêu cầu',
    
    -- Mốc thời gian & Vòng đời tin
    published_at            TIMESTAMPTZ,
    updated_at_source       TIMESTAMPTZ,
    deadline                TIMESTAMPTZ,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_jobs_canonical FOREIGN KEY (canonical_job_id) REFERENCES jobs(job_id) ON DELETE SET NULL
);

COMMENT ON TABLE jobs IS 'Bảng tin tuyển dụng chuẩn hóa trung tâm (Golden Record Entity), độc lập với từng sàn riêng lẻ';
COMMENT ON COLUMN jobs.primary_source_id IS 'Nguồn đầu tiên hoặc nguồn chính phát hiện tin này';
COMMENT ON COLUMN jobs.canonical_job_id IS 'ID của công việc gốc nếu công việc này bị đăng chéo trên sàn khác (Cross-Portal Deduplication)';
COMMENT ON COLUMN jobs.seniority_level IS 'Cấp bậc phân tích: Intern | Fresher | Junior | Middle | Senior | Lead | Manager | Director';
COMMENT ON COLUMN jobs.salary_type IS 'Loại lương: range (khoảng) | fixed (cố định) | min_only | max_only | negotiable (thỏa thuận) | undisclosed';
COMMENT ON COLUMN jobs.salary_min_vnd IS 'Mức lương sàn tối thiểu đã quy đổi thống nhất về VNĐ/tháng để làm Dashboard';
COMMENT ON COLUMN jobs.salary_max_vnd IS 'Mức lương trần tối đa đã quy đổi thống nhất về VNĐ/tháng để làm Dashboard';
COMMENT ON COLUMN jobs.is_active IS 'Trạng thái còn hiển thị hoạt động trên thị trường';

CREATE INDEX idx_jobs_company_id ON jobs(company_id);
CREATE INDEX idx_jobs_city ON jobs(city);
CREATE INDEX idx_jobs_seniority ON jobs(seniority_level);
CREATE INDEX idx_jobs_work_mode ON jobs(work_mode);
CREATE INDEX idx_jobs_is_active ON jobs(is_active);
CREATE INDEX idx_jobs_published_at ON jobs(published_at DESC);
CREATE INDEX idx_jobs_salary_vnd ON jobs(salary_min_vnd, salary_max_vnd) WHERE salary_min_vnd IS NOT NULL;
CREATE INDEX idx_jobs_title_trgm ON jobs USING gin (title_normalized gin_trgm_ops);


-- ------------------------------------------------------------------------------
-- 4. BẢNG HEAVY TEXT / NLP: job_descriptions (Nội Dung Chi Tiết Văn Bản)
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

CREATE INDEX idx_job_descriptions_language ON job_descriptions(language);
CREATE INDEX idx_job_descriptions_text_hash ON job_descriptions(text_hash);


-- ------------------------------------------------------------------------------
-- 5. BẢNG DIMENSION: skills (Danh Mục Kỹ Năng Chuẩn Hóa Toàn Hệ Thống)
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

CREATE INDEX idx_skills_category ON skills(skill_category);
CREATE INDEX idx_skills_parent ON skills(parent_id);


-- ------------------------------------------------------------------------------
-- 6. BẢNG BRIDGE (N - N): job_skills (Mối Liên Kết Việc Làm Và Kỹ Năng)
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

CREATE INDEX idx_job_skills_job_id ON job_skills(job_id);
CREATE INDEX idx_job_skills_skill_id ON job_skills(skill_id);
CREATE INDEX idx_job_skills_type ON job_skills(skill_type);


-- ==============================================================================
-- PHÂN VÙNG 3: HỖ TRỢ KỸ NGHỆ DỮ LIỆU & QUAN SÁT (DATA ENGINEERING & OBSERVABILITY)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 7. BẢNG MAPPING ĐA NGUỒN: job_source_records (Bản Ghi Nguồn Trên Từng Website)
-- ------------------------------------------------------------------------------
CREATE TABLE job_source_records (
    source_record_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id                  BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    source_id               INT NOT NULL REFERENCES job_sources(source_id) ON DELETE RESTRICT,
    source_job_id           VARCHAR(100) NOT NULL,
    source_job_url          TEXT NOT NULL,
    batch_id                VARCHAR(100),
    crawled_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_source_record UNIQUE (source_id, source_job_id)
);

COMMENT ON TABLE job_source_records IS 'Lưu liên kết 1 tin chuẩn với các bản ghi gốc trên từng website cào được (Tránh trùng lặp khi 1 tin đăng nhiều sàn)';
COMMENT ON COLUMN job_source_records.job_id IS 'Khóa ngoại trỏ về Golden Record trong bảng jobs';
COMMENT ON COLUMN job_source_records.source_id IS 'Khóa ngoại trỏ về website nguồn (TopCV, TopDev, VietnamWorks)';
COMMENT ON COLUMN job_source_records.source_job_id IS 'Mã tin gốc trên sàn đó';
COMMENT ON COLUMN job_source_records.source_job_url IS 'URL trực tiếp trên website đó';
COMMENT ON COLUMN job_source_records.crawled_at IS 'Thời điểm crawler thu thập bản ghi này';

CREATE INDEX idx_source_records_job_id ON job_source_records(job_id);
CREATE INDEX idx_source_records_source_job ON job_source_records(source_id, source_job_id);
CREATE INDEX idx_source_records_batch ON job_source_records(batch_id);


-- ------------------------------------------------------------------------------
-- 8. BẢNG CHUỖI THỜI GIAN: job_snapshots (Lịch Sử Biến Động Theo Thời Gian)
-- ------------------------------------------------------------------------------
CREATE TABLE job_snapshots (
    snapshot_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id                  BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    observed_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    batch_id                VARCHAR(100),
    
    -- Thuộc tính quan sát tại thời điểm đó
    title_normalized        TEXT NOT NULL,
    city                    VARCHAR(100),
    salary_min              NUMERIC(14, 2),
    salary_max              NUMERIC(14, 2),
    salary_min_vnd          NUMERIC(14, 2),
    salary_max_vnd          NUMERIC(14, 2),
    salary_type             VARCHAR(30),
    is_active               BOOLEAN NOT NULL,
    content_hash            VARCHAR(64) NOT NULL
);

COMMENT ON TABLE job_snapshots IS 'Bảng chụp ảnh định kỳ (Periodic Snapshot Fact Table) phục vụ phân tích biến động thị trường, xu hướng lương và vòng đời tin';
COMMENT ON COLUMN job_snapshots.job_id IS 'Khóa ngoại trỏ về tin tuyển dụng đang quan sát';
COMMENT ON COLUMN job_snapshots.observed_at IS 'Thời điểm crawler quét qua thấy tin này';
COMMENT ON COLUMN job_snapshots.content_hash IS 'Mã hash nội dung để kiểm tra tin có bị nhà tuyển dụng chỉnh sửa mô tả hay không';

CREATE INDEX idx_snapshots_job_id ON job_snapshots(job_id);
CREATE INDEX idx_snapshots_observed_at ON job_snapshots(observed_at DESC);
CREATE INDEX idx_snapshots_salary_vnd ON job_snapshots(salary_min_vnd, salary_max_vnd);
CREATE INDEX idx_snapshots_batch ON job_snapshots(batch_id);


-- ------------------------------------------------------------------------------
-- 9. BẢNG AUDIT CHẤT LƯỢNG: dq_results (Nhật Ký Kiểm Định Data Quality)
-- ------------------------------------------------------------------------------
CREATE TABLE dq_results (
    dq_result_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id                VARCHAR(100) NOT NULL,
    source_id               INT REFERENCES job_sources(source_id) ON DELETE SET NULL,
    entity_type             VARCHAR(50) NOT NULL,
    entity_id               VARCHAR(100) NOT NULL,
    rule_name               VARCHAR(100) NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'ERROR',
    status                  VARCHAR(20) NOT NULL DEFAULT 'FAILED',
    error_message           TEXT,
    checked_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dq_results IS 'Nhật ký kiểm định chất lượng dữ liệu (Data Observability), ghi nhận các vi phạm quy tắc DQ để theo dõi trên Dashboard';
COMMENT ON COLUMN dq_results.batch_id IS 'Mã batch ETL / Crawler liên quan';
COMMENT ON COLUMN dq_results.entity_type IS 'Loại đối tượng kiểm tra: job | company | job_description | listing';
COMMENT ON COLUMN dq_results.entity_id IS 'ID của bản ghi bị kiểm tra';
COMMENT ON COLUMN dq_results.rule_name IS 'Mã quy tắc kiểm tra (ví dụ: MISSING_TITLE, INVALID_SALARY_RANGE, SUSPICIOUS_SPAM)';
COMMENT ON COLUMN dq_results.severity IS 'Mức độ nghiêm trọng: CRITICAL | ERROR | WARNING | INFO';
COMMENT ON COLUMN dq_results.status IS 'Trạng thái kiểm tra: PASSED | FAILED | WARNING';

CREATE INDEX idx_dq_results_batch_id ON dq_results(batch_id);
CREATE INDEX idx_dq_results_entity ON dq_results(entity_type, entity_id);
CREATE INDEX idx_dq_results_rule ON dq_results(rule_name);
CREATE INDEX idx_dq_results_status ON dq_results(status);
CREATE INDEX idx_dq_results_checked_at ON dq_results(checked_at DESC);


-- ==============================================================================
-- PHÂN VÙNG 4: TRIGGERS TỰ ĐỘNG CẬP NHẬT UPDATED_AT
-- ==============================================================================
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
