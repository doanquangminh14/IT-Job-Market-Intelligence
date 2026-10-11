# 🕷️ Module Ingestion & Web Scraping (`src/crawlers/`)

Module chịu trách nhiệm thu thập tự động dữ liệu tuyển dụng việc làm IT từ các nền tảng tuyển dụng lớn tại Việt Nam (**TopCV**, **TopDev**, **VietnamWorks**), hỗ trợ vượt tường lửa Cloudflare/WAF, chống trùng lặp và tự động phân tách dữ liệu thô (Raw Layer).

---

## 1. Cấu Trúc Thư Mục

```text
src/crawlers/
├── __init__.py                # Export BaseCrawler và các crawler con
├── base.py                    # Class trừu tượng BaseCrawler & các hàm tiện ích chung
│
├── topcv/
│   ├── __init__.py            # Expose TopCVCrawler
│   ├── crawler.py             # Điều phối request WAF, quản lý pending queue, Smart Stop
│   └── parser.py              # Bóc tách HTML Job card, Company page và Job detail
│
├── topdev/
│   ├── __init__.py            # Expose TopDevCrawler
│   ├── crawler.py             # Điều phối gọi Next.js RSC, rate-limit, retry-failed
│   └── parser.py              # Decode Next.js stream payload, bóc tách listing & detail
│
└── vietnamworks/
    ├── __init__.py            # Expose VietnamWorksCrawler
    ├── crawler.py             # Điều phối gọi Search API với pagination hits_per_page
    └── parser.py              # Validate schema & chuẩn hóa JSON record sang Pydantic
```

---

## 2. Các Tính Năng & Cơ Chế Kỹ Thuật Nổi Bật

### 2.1. Tách biệt vai trò (Separation of Concerns)
* **`crawler.py`**: Chuyên trách tầng mạng (networking), Session TLS fingerprint impersonation (`curl_cffi`), rate-limiting, cơ chế thử lại (exponential backoff) và lưu file.
* **`parser.py`**: Chuyên trách tầng trích xuất (parsing), nhận HTML/JSON và bóc tách dữ liệu sạch, fallback ngày hết hạn, validate bằng Pydantic schema.

### 2.2. Vượt WAF & Giả lập trình duyệt (Chrome 124 Impersonation)
* TopCV và TopDev áp dụng cơ chế Cloudflare Bot Management khắt khe. Crawler sử dụng `curl_cffi` với chữ ký TLS/JA3 giả lập Google Chrome 124 thật trên Windows, giúp vượt qua mã HTTP 403 Forbidden.

### 2.3. Hàng đợi Pending thông minh (Pending Queue Prioritization)
* Mỗi trang listing khi cào về sẽ chứa nhiều tin hơn số lượng detail cần lấy trong 1 phiên. Các tin chưa được cào sẽ có trạng thái `detail_status: "pending"`.
* Trong phiên cào tiếp theo, crawler **luôn ưu tiên quét và cào sạch toàn bộ các job pending cũ trước**, khi hết job chờ mới mở rộng cào trang listing mới.

### 2.4. Dừng sớm thông minh (Smart Early Stopping)
* Thay vì chạy cố định số trang tối đa (ví dụ 50 trang), crawler tự động dừng sớm nếu phát hiện **2 trang liên tiếp không có dữ liệu mới** (tránh gửi request vô ích lên server khi đã hết tin tuyển dụng).

### 2.5. Trích xuất Hạn nộp hồ sơ đa tầng (Fallback Deadline Parser)
* Tự động phát hiện các chuỗi thời gian tương đối như *"Còn 28 ngày"*, *"Hết hạn trong 11 ngày"*, *"5 days left"*, *"Hôm nay hết hạn"* để quy đổi chính xác ra ngày hết hạn chuẩn ISO `YYYY-MM-DD`.

---

## 3. Hướng Dẫn Sử Dụng & Lệnh Chạy (CLI)

Bộ crawler được điều phối thông qua CLI [`main_crawl.py`](../../main_crawl.py) ở thư mục gốc:

```powershell
# 1. Cào cả 3 nguồn (mỗi nguồn 100 jobs thành công - Mặc định)
python main_crawl.py --source all --target 100

# 2. Cào riêng từng nguồn cụ thể
python main_crawl.py --source topcv --target 50
python main_crawl.py --source topdev --target 50
python main_crawl.py --source vietnamworks --target 50

# 3. Chế độ cào bù các job bị lỗi (Retry Failed)
python main_crawl.py --source topcv --retry-failed
python main_crawl.py --source all --retry-failed

# 4. Chế độ Test Sandbox (không ghi vào data/raw/)
python main_crawl.py --source topcv --target 2 --output-dir tests/test_output
```

---

## 4. Hướng Dẫn Mở Rộng Thêm Crawler Mới

Để thêm một sàn tuyển dụng mới (ví dụ `itviec`):
1. Thêm cấu hình nguồn trong [`configs/sources.yaml`](../../configs/sources.yaml) (`base_url`, `rate_limit`, `pagination`...).
2. Tạo thư mục mới `src/crawlers/itviec/`:
   - `parser.py`: Viết các hàm parse HTML của trang ITViec.
   - `crawler.py`: Kế thừa lớp `BaseCrawler` từ `src.crawlers.base`, cài đặt phương thức `run(target_success_count)`.
   - `__init__.py`: Export `ITViecCrawler`.
3. Đăng ký crawler mới vào [`src/crawlers/__init__.py`](__init__.py) và `crawler_map` trong [`main_crawl.py`](../../main_crawl.py).
