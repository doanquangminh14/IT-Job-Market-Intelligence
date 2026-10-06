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