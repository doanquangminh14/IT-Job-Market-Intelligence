# Hướng Dẫn Sử Dụng & Trình Chiếu Slide Báo Cáo Đồ Án

Tài liệu hướng dẫn mở, trình chiếu, tùy chỉnh nội dung và xuất PDF cho bộ slide báo cáo học thuật:
**`presentation.html`** — *Hệ thống Phân tích Thị trường Tuyển dụng IT & Gợi ý Việc làm Cá nhân hóa (IT Job Market Intelligence & Personalized Job Recommendation System)*.

---

## 1. Số Liệu Kỹ Thuật Thực Tế Đã Đạt Được Của Dự Án

Toàn bộ 12 slide đã được cập nhật **100% bám sát dữ liệu và mã nguồn thực tế** trong kho lưu trữ:

| Chỉ số kỹ thuật | Giá trị thực nghiệm | Vị trí kiểm chứng trong mã nguồn |
| :--- | :---: | :--- |
| **Nguồn dữ liệu thu thập** | **3 Sàn** | TopCV, TopDev, VietnamWorks (`src/crawlers/`) |
| **Dữ liệu Bronze Master** | **3.380 listings** / **3.349 details** | `data/bronze/bronze_*.json` |
| **Tổng số việc làm (PostgreSQL Silver)** | **3.349 việc làm** (3.069 active) | Bảng `jobs` trong PostgreSQL (`sql/schema_silver.sql`) |
| **Doanh nghiệp sau khử trùng lặp** | **1.668 công ty** | Bảng `companies` (Entity Resolution) |
| **Bộ từ điển Kỹ năng IT chuẩn hóa** | **76 Kỹ năng** | Bảng `skills` & Regex Matcher (`job_skills.py`) |
| **Quan hệ Việc làm - Kỹ năng** | **8.366 liên kết** | Bảng quan hệ nhiều-nhiều `job_skills` |
| **Vector nhúng ngữ nghĩa (Embeddings)** | **3.249 vectors (384 chiều)** | `data/embeddings/jobs_embeddings.npy` (MiniLM-L12-v2) |
| **Dữ liệu huấn luyện Collaborative SVD** | **22.053 tương tác** (k=30) | 800 personas, 883 việc làm (`data/interactions/`) |
| **Bộ kiểm thử tự động (Pytest)** | **30/30 Tests PASS (100%)** | `pytest tests -v` (Sandbox output isolation) |
| **Khởi chạy máy chủ Web & API** | **Cổng 8000** | `python run_web.py` (FastAPI + Modern SPA Dashboard) |

---

## 2. Cách Mở & Trình Chiếu Trực Tiếp

### Mở file trên máy tính
- **Cách 1:** Nhấp đúp chuột vào tệp [`presentation.html`](./presentation.html) để mở trên Google Chrome, Microsoft Edge, Brave...
- **Cách 2:** Mở trình duyệt và nhấn `Ctrl + O`, chọn file `presentation.html`.

### Phím tắt điều khiển khi thuyết trình:
- `▶` / `Space` / `Page Down`: Chuyển sang slide tiếp theo.
- `◀` / `Page Up`: Quay lại slide trước đó.
- `F`: Bật / tắt chế độ toàn màn hình (Fullscreen).
- `O` hoặc `ESC`: Mở mục lục nhanh 12 slide để chuyển tức thì.
- `Home` / `End`: Về slide đầu / Đến slide cuối.

---

## 3. Cách Xuất Slide Sang Định Dạng PDF / In Ấn

1. Mở `presentation.html` trên trình duyệt Chrome hoặc Edge.
2. Nhấn tổ hợp phím **`Ctrl + P`** (Print).
3. Mục **Destination (Máy in):** Chọn **Save as PDF (Lưu dưới dạng PDF)**.
4. Mục **Layout (Bố cục):** Chọn **Landscape (Ngang)**.
5. Mục **More settings (Cài đặt khác):**
   - **Paper size:** A4 (hoặc 16:9).
   - **Scale:** Default (Mặc định).
   - **Background graphics (Đồ họa nền):** **Tích chọn (Bắt buộc)** để giữ đầy đủ màu viền và bảng biểu.
   - **Headers and footers:** Bỏ chọn để ẩn ngày giờ/URL của trình duyệt.
6. Nhấn **Save (Lưu)**.

---

## 4. Danh Mục Cấu Trúc 12 Slide Báo Cáo

- **Slide 01 — Cover:** Tên đề tài, 4 chỉ số kỹ thuật thực tế (3.349 jobs, 1.668 công ty, 3.249 vectors 384d, 30/30 tests pass).
- **Slide 02 — Problem Statement:** Thực trạng dữ liệu 3 sàn, độ lệch ngôn ngữ (87.6% vi TopCV vs 100% en TopDev), mập mờ mức lương.
- **Slide 03 — Objectives & Scope:** Cả 3 nhóm Data Engineering, Market Intelligence và Recommendation System đều đã hoàn thành và kiểm chứng 100%.
- **Slide 04 — Data Sources & Fields:** Quy trình 2 tầng, bảng 6 nhóm thuộc tính thực tế trong Bronze JSON (3.380 listings, 3.349 details).
- **Slide 05 — End-to-End Pipeline:** Sơ đồ 5 tầng Medallion đã vận hành (Raw &rarr; Bronze &rarr; Silver PostgreSQL 3NF &rarr; AI NLP &rarr; Serving).
- **Slide 06 — Data Quality & ETL:** Quy trình kiểm định QualityValidator, chuẩn hóa dải lương VNĐ, Entity Resolution 1.668 công ty.
- **Slide 07 — Market Analytics:** Kết quả phân tích thực nghiệm từ CSDL Silver: dải lương theo cấp bậc, top tech stacks trên Chart.js UI.
- **Slide 08 — NLP & Skill Extraction:** 76 IT Skills Taxonomy trích xuất bằng Regex, ma trận (3.249, 384) từ MiniLM-L12-v2 đa ngữ.
- **Slide 09 — Recommendation System:** Thuật toán True Hybrid `0.45*Semantic + 0.30*Skill + 0.25*CF`, mô hình SVD k=30 trên 22k tương tác, xử lý Cold-Start.
- **Slide 10 — Database Design:** Mô hình 8 bảng PostgreSQL 3NF (`jobs`, `companies`, `job_descriptions`, `skills`, `job_skills`, `snapshots`, `source_records`, `dq_results`).
- **Slide 11 — Results & Evaluation:** 30/30 bài test Pytest thành công, tốc độ suy luận &lt; 20ms, truy vấn DB &lt; 30ms, ghi nhận 2 hạn chế khách quan.
- **Slide 12 — Conclusion & Q&A:** Tóm tắt 4 đóng góp kỹ thuật, nút mở Live Demo cổng 8000 và lời cảm ơn Hội đồng trang trọng.
