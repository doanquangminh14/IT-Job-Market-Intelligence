# 📊 Module Data Profiling & Inventory (`src/profiling/`)

Module chịu trách nhiệm khảo sát, kiểm kê toàn diện và đánh giá "sức khỏe" dữ liệu thô (Raw Data Profiling) trước khi đưa vào các tầng xử lý làm sạch (Silver / Bronze Layer).

---

## 1. Cấu Trúc Thư Mục

```text
src/profiling/
├── __init__.py                # Export DataProfiler, ReportGenerator, detect_job_language
├── language.py                # Thuật toán heuristic nhận diện ngôn ngữ bài đăng (vi / en / mixed)
├── profiler.py                # Lõi tính toán kiểm kê, missing values, duplicates, schema diff
└── reporter.py                # Xuất báo cáo Console, Markdown và cập nhật metrics CSV
```

---

## 2. 6 Câu Hỏi Kiểm Kê Cốt Lõi Được Giải Quyết

Module được thiết kế nhằm trả lời trực diện 6 câu hỏi nghiệp vụ quan trọng:

1. **Có bao nhiêu listing đã thu thập?**
   - Thống kê tổng số lượng tin cào được từ trang tìm kiếm theo từng nguồn và toàn hệ thống.
2. **Bao nhiêu tin đã crawl detail thành công?**
   - Phân loại rõ: `success` (chi tiết hoàn tất), `failed` (lỗi cần cào bù), `pending` (nằm trong hàng đợi chờ cào).
3. **Có bao nhiêu URL hoặc tin bị trùng lặp?**
   - Trùng lặp nội bộ sàn: Đếm các URL hoặc Job ID xuất hiện nhiều hơn 1 lần trên cùng 1 web.
   - Trùng chéo sàn (Cross-portal): Nhận diện các tin cùng công ty và tiêu đề tuyển dụng được đăng chéo trên các trang khác nhau.
4. **Những trường nào thường bị thiếu (Completeness Rate)?**
   - Đo lường % thiếu của từng trường: `title`, `company`, `location`, `salary`, `experience`, `skills`, `responsibilities`, `requirements`, `benefits`, `deadline`.
   - Phân biệt rõ: Lương *"Thương lượng/Thoả thuận"* là thông tin nghiệp vụ hợp lệ, không phải dữ liệu thiếu.
5. **Có bao nhiêu nguồn và phân bố ngôn ngữ tuyển dụng?**
   - Phân loại tỷ lệ tin đăng bằng **Tiếng Việt (`vi`)**, **Tiếng Anh (`en`)**, và **Song ngữ (`mixed`)**.
6. **Cấu trúc JSON giữa các nguồn có đồng nhất hay không (Schema Consistency)?**
   - So sánh danh sách các key trong file JSON detail của TopCV, TopDev, VietnamWorks xem có lệch trường hay thiếu trường so với Pydantic schema chuẩn hay không.

---

## 3. Hệ Thống Báo Cáo Cập Nhật (Dual-Reporting System)

Hệ thống lưu trữ báo cáo tại thư mục [`reports/profiling/`](../../reports/profiling/) theo mô hình kép:

```text
reports/profiling/
├── latest_summary.md         # Báo cáo Master: Luôn phản ánh bức tranh TOÀN BỘ kho dữ liệu hiện tại
├── history_metrics.csv       # File lịch sử: Nối thêm (append) chỉ số sau mỗi lần chạy để theo dõi xu hướng
└── daily/                    # Báo cáo Snapshot chi tiết cho từng ngày cụ thể (YYYY-MM-DD.md)
```

---

## 4. Hướng Dẫn Sử Dụng & Lệnh Chạy (CLI)

Bộ profiling được thực thi thông qua CLI [`main_profile.py`](../../main_profile.py) ở thư mục gốc:

```powershell
# 1. Kiểm kê toàn bộ kho dữ liệu từ ngày đầu đến nay (Mặc định)
python main_profile.py

# 2. Tự động kiểm kê ngày cào mới nhất có trong data/raw/
python main_profile.py --latest

# 3. Kiểm kê riêng một ngày cụ thể
python main_profile.py --date 2026-10-11

# 4. Chỉ kiểm kê riêng một nguồn cụ thể
python main_profile.py --source topcv
python main_profile.py --source topdev
python main_profile.py --source vietnamworks

# 5. Chỉ định thư mục lưu báo cáo tùy chọn
python main_profile.py --report-dir reports/custom_dir
```
