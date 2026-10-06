# IT Job Market Intelligence & Job Recommender System

## 1. Executive Summary

Hệ thống gồm 3 khối chạy trên cùng một PostgreSQL:

- **Data platform**: thu thập job IT → Raw → ETL → Silver (PostgreSQL) → Gold.
- **Market intelligence**: SQL analytics + NLP trích xuất skill → insight về role, skill, lương, xu hướng.
- **Recommender**: Content-Based → Collaborative Filtering → Hybrid, có hard filter, skill gap và explanation.

Kết quả hiển thị qua **Streamlit**. Thứ tự triển khai: MVP trước (ingestion → ETL → PostgreSQL → DQ → analytics → skill extraction → content-based → dashboard), sau đó đến CF, Hybrid, Evaluation. Docker, pgvector và Airflow làm sau cùng.

---

## 2. Problem Definition

| Mục | Nội dung |
| :--- | :--- |
| **Problem** | Sinh viên IT khó biết thị trường cần skill gì, lương bao nhiêu, job nào hợp với mình, và còn thiếu gì. Tin tuyển dụng thì rời rạc, không chuẩn hóa (lương, địa điểm, tên skill mỗi nơi một kiểu). |
| **Primary users** | Sinh viên IT, người tìm việc |
| **Secondary users** | Recruiter, HR, market researcher |
| **Input** | Job posting: title, company, location, salary, experience, employment type, work mode, description, requirements, responsibilities, skills, dates, URL, source. Cộng thêm hồ sơ ứng viên (role, skills, kinh nghiệm, địa điểm, lương, work mode). |
| **Output** | Market insights, skill demand, salary analytics, job search, top-N recommendation kèm matched/missing skills, skill gap, explanation. |

---

## 3. Architecture

```text
 JOB SOURCES (API / public dataset / board được phép)
        │
        ▼
 INGESTION  (retry, timeout, rate limit, incremental)
        │
        ▼
 RAW  data/raw/<source>/<YYYY-MM-DD>/   ← bất biến, JSON nguyên bản
        │
        ▼
 BRONZE data/bronze/  ← Parquet, chỉ flatten + thêm metadata (chưa sửa nội dung)
        │
        ▼
 ETL: profiling → cleaning → normalization → dedup → validation → enrichment
        │                     │
        ▼                     ▼
 DATA QUALITY report     SILVER data/silver/ (Parquet sạch)
        │
        ▼
 POSTGRESQL (16 bảng, nguồn sự thật cho app)
        │
   ┌────┼──────────────┐
   ▼    ▼              ▼
 ANALYTICS  NLP      RECOMMENDATION
 (SQL)   (skills,   Content / CF / Hybrid
          embeddings)  → Skill Gap → Explanation
   └────┴──────────────┘
        ▼
 GOLD data/gold/  (market/, recommendation/, features/)
        ▼
 STREAMLIT (6 trang)
```

| Tầng | Ý nghĩa | Quy tắc |
| :--- | :--- | :--- |
| **Raw** | Response nguyên bản từ nguồn | Không sửa, không ghi đè, mỗi lần chạy một file mới |
| **Bronze** | Raw đã đưa về dạng bảng (Parquet) + metadata (source, run_id, fetched_at, hash) | Chưa clean nội dung |
| **Silver** | Đã clean, chuẩn hóa, dedup, validate | Là thứ nạp vào PostgreSQL |
| **PostgreSQL** | Lưu quan hệ chuẩn hóa, có ràng buộc | App/analytics đọc từ đây |
| **Gold** | Bảng tổng hợp/feature phục vụ dashboard và recommender | Tạo lại được từ Silver/DB |