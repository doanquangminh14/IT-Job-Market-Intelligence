# IT Job Market Intelligence 🚀

Hệ thống thu thập, xử lý và phân tích dữ liệu thị trường việc làm Công nghệ Thông tin (IT) tại Việt Nam theo kiến trúc **Data Pipeline & Market Intelligence**.

Dự án hiện đã hoàn thiện **Tầng thu thập dữ liệu thô (Raw Data Ingestion Layer)** với độ tin cậy cao, hỗ trợ 3 cổng tuyển dụng IT lớn nhất: **TopDev**, **VietnamWorks** và **TopCV**.

---

## 📑 Mục lục
1. [Tổng quan & Kiến trúc dữ liệu](#1-tổng-quan--kiến-trúc-dữ-liệu)
2. [Các nguồn dữ liệu đã tích hợp](#2-các-nguồn-dữ-liệu-đã-tích-hợp)
3. [Các cơ chế kỹ thuật cốt lõi](#3-các-cơ-chế-kỹ-thuật-cốt-lõi)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Hướng dẫn cài đặt & Sử dụng](#5-hướng-dẫn-cài-đặt--sử-dụng)
6. [Kế hoạch phát triển tiếp theo](#6-kế-hoạch-phát-triển-tiếp-theo)

---

## 1. Tổng quan & Kiến trúc dữ liệu

Hệ thống được thiết kế theo tư duy **Data Engineering chuyên nghiệp (Medallion Architecture)**:
* **Tầng Raw (Hiện tại)**: Thu thập và bảo tồn dữ liệu gốc bất biến (Immutable Raw JSON) từ các nền tảng, có đầy đủ audit logs và metadata.
* **Tầng Bronze / Silver (Tiếp theo)**: Làm sạch, chuẩn hóa kiểu dữ liệu, khử trùng lặp chéo giữa các web (Entity Resolution).
* **Tầng Gold (Phân tích & AI)**: Bảng dữ liệu chiều (Dimensional Modeling), phân tích xu hướng kỹ năng, mức lương và trực quan hóa Dashboard.

---

## 2. Các nguồn dữ liệu đã tích hợp

| Nguồn | Cơ chế cào | Điểm đặc thù được tối ưu |
| :--- | :--- | :--- |
| **TopDev** | Next.js RSC Stream | Bóc tách trực tiếp luồng dữ liệu Server Components, lấy đầy đủ skill tags, mô tả công ty và mức lương. |
| **VietnamWorks** | Direct Internal JSON API | Giả lập TLS Chrome 124, gọi trực tiếp Search API nội bộ cực nhanh, bóc tách chính xác hệ thống ID ngành nghề và cấp bậc. |
| **TopCV** | HTML DOM & JSON-LD Hybrid | Tự động bóc tách Sidebar thông tin công ty (Quy mô, Trụ sở) và bóc tách trang hồ sơ công ty thật (`company_url`) để lấy `overview_raw` chuẩn xác (khắc phục lỗi lặp JD của TopCV). |

---

## 3. Các cơ chế kỹ thuật cốt lõi

### 3.1. Lưu trữ 2 tầng phân tách (Two-Tier Storage Architecture)
Dữ liệu mỗi ngày (`YYYY-MM-DD`) được tổ chức tách bạch rõ ràng:
* **Thư mục Listings (`data/raw/<source>/listings/YYYY-MM-DD/page_XXX.json`)**:
  * Đóng vai trò là "Sổ điểm danh" và Audit Log.
  * Ghi nhận tất cả các thẻ công việc tìm thấy, kèm trạng thái chi tiết:
    * `detail_status`: `"success"` | `"failed"` | `"pending"` | `"expired"`
    * `detail_attempts`: Số lần thử cào (1, 2, 3)
    * `detail_http_status`: Mã phản hồi HTTP (200, 429, 404,...)
    * `detail_error`: Chi tiết nguyên nhân lỗi (nếu có).
* **Thư mục Details (`data/raw/<source>/details/YYYY-MM-DD/<Prefix>XXX.json`)**:
  * Đóng vai trò là "Kho dữ liệu sạch 100%".
  * **Chỉ lưu các job cào thành công** và đã vượt qua kiểm định schema Pydantic `JobDetailRaw` (24 trường thông tin). Job lỗi tuyệt đối không được đưa vào đây.

### 3.2. Chống cào trùng lịch sử (Historical Deduplication)
* Mỗi khi khởi động, crawler tự động quét toàn bộ các file detail trong quá khứ (`_get_all_crawled_job_ids()`) để nạp danh sách `source_job_id` đã có vào bộ nhớ `Set[str]`.
* Khi quét danh sách web, hễ gặp job đã cào từ trước (dù là hôm nay hay nhiều ngày trước), crawler **tự động bỏ qua ngay lập tức**, không tốn tài nguyên request lại.

### 3.3. Tự động thử lại với độ trễ tăng dần (Retry with Exponential Backoff)
* Khi gặp sự cố mạng hoặc phản hồi `HTTP 429 (Too Many Requests)`:
  * Crawler tự động thử lại tối đa **3 lần** với thời gian nghỉ giãn cách:
    * TopCV: 10s ➔ 20s ➔ 30s
    * VietnamWorks: 10s ➔ 20s ➔ 30s
    * TopDev: 15s ➔ 30s ➔ 45s
  * Nếu sau 3 lần vẫn thất bại, crawler tự động bỏ qua để chuyển sang job tiếp theo, **tuyệt đối không bao giờ bị treo cứng hệ thống**.
  * Nếu gặp `HTTP 404` (Tin đã hết hạn), crawler nhận diện ngay là `expired` và bỏ qua không retry vô ích.

### 3.4. Chế độ Cào bù thông minh (`--retry-failed`)
* Cho phép quét lại riêng các job bị đánh dấu `"failed"` trong các file listing để cào bù (khi server tuyển dụng đã hết nghẽn rate-limit).
* Khi cào bù thành công, dữ liệu tự động được bổ sung vào file detail và trạng thái trong listing tự động đổi sang `"success"`.

### 3.5. Bộ nhớ đệm thông tin công ty (Company Profile In-Memory Cache)
* Đối với các nền tảng cần cào trang giới thiệu công ty riêng (như TopCV):
* Crawler sử dụng `company_cache: Dict[str, str]` để lưu tạm mô tả công ty theo URL. Nếu trong phiên có 10 jobs thuộc cùng một công ty, crawler chỉ cần tải trang công ty **đúng 1 lần duy nhất**, giảm 90% tải request thừa.

### 3.6. Ghi log tập trung (Centralized Logging)
* Toàn bộ log của các crawler và bộ điều phối được gom về thư mục `logs/` ở thư mục gốc:
  * `logs/topdev.log`
  * `logs/vietnamworks.log`
  * `logs/topcv.log`
* Thư mục `data/` được giữ sạch 100% chỉ chứa dữ liệu. Thư mục `logs/` đã được cấu hình trong `.gitignore` để không bị commit file log nặng lên GitHub.

---

## 4. Cấu trúc thư mục

```text
IT-Job-Market-Intelligence/
├── configs/
│   └── sources.yaml              # Cấu hình tham số cào, URL, headers, rate-limit từng web
├── data/
│   └── raw/                      # Kho dữ liệu thô (Raw Layer)
│       ├── topdev/
│       │   ├── listings/YYYY-MM-DD/page_001.json
│       │   └── details/YYYY-MM-DD/TC001.json
│       ├── vietnamworks/
│       │   ├── listings/YYYY-MM-DD/page_001.json
│       │   └── details/YYYY-MM-DD/VNW001.json
│       └── topcv/
│           ├── listings/YYYY-MM-DD/page_001.json
│           └── details/YYYY-MM-DD/TCV001.json
├── logs/                         # Nhật ký tập trung (Ignored by Git)
│   ├── topdev.log
│   ├── vietnamworks.log
│   └── topcv.log
├── src/
│   ├── crawlers/                 # Mã nguồn các bộ cào
│   │   ├── base.py               # Lớp cơ sở BaseCrawler
│   │   ├── topdev.py             # Crawler TopDev
│   │   ├── vietnamworks.py       # Crawler VietnamWorks
│   │   └── topcv.py              # Crawler TopCV
│   └── schemas/
│       └── job.py                # Pydantic schema chuẩn hóa dữ liệu Job
├── main_crawl.py                 # Bộ điều phối thực thi cào dữ liệu CLI
├── requirements.txt              # Danh sách thư viện phụ thuộc
└── README.md
```

---

## 5. Hướng dẫn cài đặt & Sử dụng

### 5.1. Cài đặt môi trường
Khuyến nghị sử dụng Python 3.11+.

```powershell
# 1. Tạo môi trường ảo
python -m venv .venv

# 2. Kích hoạt môi trường ảo (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### 5.2. Các lệnh chạy cào dữ liệu (`main_crawl.py`)

```powershell
# 1. Xem trợ giúp các tham số dòng lệnh
python main_crawl.py --help

# 2. Tự động cào cả 3 nguồn (mỗi nguồn 100 jobs thành công - Mặc định)
python main_crawl.py --source all --target 100

# 3. Cào từng nguồn riêng biệt
python main_crawl.py --source topcv --target 50
python main_crawl.py --source vietnamworks --target 50
python main_crawl.py --source topdev --target 50

# 4. Chạy chế độ cào bù các job bị lỗi (Retry Failed)
python main_crawl.py --source topcv --retry-failed
python main_crawl.py --source all --retry-failed
```

---

## 6. Kế hoạch phát triển tiếp theo

- [ ] **Data Quality & Profiling (`src/profiling/`)**:
  - Đánh giá tỉ lệ hoàn thiện dữ liệu (Completeness Rate), tỷ lệ trường bị thiếu.
  - Phân tích phân phối lương (Thương lượng vs Khoảng lương cụ thể).
  - Thống kê tỷ lệ ngôn ngữ tuyển dụng (Tiếng Anh vs Tiếng Việt).
  - Tự động xuất báo cáo chất lượng dữ liệu dạng Markdown / JSON.
- [ ] **Silver Processing Layer (`src/processing/`)**:
  - Chuẩn hóa mức lương về VNĐ (Min / Max / Currency).
  - Entity Resolution / Cross-portal Deduplication: Khử trùng lặp các tin cùng công ty được đăng chéo trên nhiều sàn.
- [ ] **Market Analytics & Dashboard (`src/analytics/`)**:
  - Phân tích Top kỹ năng công nghệ được săn đón nhất theo từng cấp bậc (Junior, Senior, Lead).
  - Xuất báo cáo trực quan hóa Insight thị trường IT.
