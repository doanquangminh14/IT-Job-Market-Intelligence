# Notebooks — IT Job Market Intelligence

Thư mục chứa toàn bộ Jupyter Notebooks thử nghiệm, phân tích và khám phá dữ liệu của dự án.  
Các notebook được tổ chức thành **5 nhóm** theo chức năng:

---

## 📁 Cấu trúc thư mục

```
notebook/
│
├── 01_crawling/                        # Thu thập & kiểm tra dữ liệu thô
│   ├── crawl_data.ipynb                → Crawl tổng hợp tất cả nguồn
│   ├── crawl_topdev.ipynb              → Crawl riêng TopDev (HTML parser)
│   └── crawl_vietnamworks.ipynb        → Crawl riêng VietnamWorks (API)
│
├── 02_data_pipeline/                   # Làm sạch & biến đổi dữ liệu Silver
│   ├── experiment_silver_cleaning.ipynb  → Thử nghiệm chuẩn hóa & dedup
│   └── view_history_metrics.ipynb        → Xem lịch sử & chỉ số pipeline
│
├── 03_nlp_embeddings/                  # NLP & Vector Embeddings
│   ├── nlp_pipeline_deepdive.ipynb     → Phân tích chi tiết NLP pipeline
│   └── semantic_embedding_experiment.ipynb → Thử nghiệm SentenceTransformer 384d
│
├── 04_recommender/                     # Hệ thống gợi ý việc làm
│   ├── collaborative_filtering_experiment.ipynb  → Item-to-Item CF & SVD
│   └── true_hybrid_recommender_experiment.ipynb  → True Hybrid (NLP + Skill + CF)
│
└── silver_tables/                      # Kiểm tra từng bảng Silver trong DB
    ├── 01_companies.ipynb
    ├── 02_jobs.ipynb
    ├── 03_job_descriptions.ipynb
    ├── 04_skills.ipynb
    ├── 05_job_skills.ipynb
    ├── 06_job_sources.ipynb
    ├── 07_job_source_records.ipynb
    ├── 08_job_snapshots.ipynb
    └── 09_dq_results.ipynb
```

---

## Hướng dẫn chạy

1. Kích hoạt môi trường ảo:
   ```bash
   .venv\Scripts\activate
   ```
2. Mở Jupyter Lab:
   ```bash
   jupyter lab
   ```
3. Chọn kernel: **`.venv (Python 3.11)`**
4. Chạy notebook từ trên xuống (Run All Cells)

> **Lưu ý:**  
> - Các notebook nhóm `01_crawling` cần kết nối internet  
> - Các notebook nhóm `02_data_pipeline`, `silver_tables` cần kết nối PostgreSQL (xem `.env`)  
> - Các notebook nhóm `04_recommender` cần có file `data/models/cf_*.npz` (chạy `src/recommender/collaborative.py` trước)

---

## Kiến trúc True Hybrid Recommender

```
CV / Mô tả nghề nghiệp
         │
         ├──[45%]── SentenceTransformer (384d)  ──→ Semantic Score
         │
         ├──[30%]── Skill Overlap (Jaccard)     ──→ Skill Score
         │
         └──[25%]── TruncatedSVD Persona CF     ──→ CF Score
                              │
                     Final Hybrid Score = 0.45×Sem + 0.30×Skill + 0.25×CF
```
