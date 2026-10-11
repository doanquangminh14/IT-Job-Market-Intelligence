# 🧪 Test Suite & Quality Assurance (`tests/`)

Thư mục chứa toàn bộ các kịch bản kiểm thử tự động (Unit Test & Integration Test) của dự án IT-Job-Market-Intelligence, được xây dựng dựa trên framework **Pytest**.

---

## 1. Cấu Trúc Thư Mục

```text
tests/
├── conftest.py                       # Fixtures dùng chung: dữ liệu mẫu HTML, RSC stream, API response JSON
│
├── unit/                             # Kiểm thử logic độc lập (Chạy offline, không gọi mạng)
│   ├── test_base_utils.py            # Test clean_html, fix_encoding, parse_relative_deadline
│   ├── test_topcv_parser.py          # Test parse thẻ job card, chi tiết TopCV
│   ├── test_topdev_parser.py         # Test decode Next.js RSC, chi tiết TopDev
│   ├── test_vietnamworks_parser.py   # Test parse item API, validate Pydantic schema
│   └── test_profiling.py             # Test nhận diện ngôn ngữ, tính toán profiling metrics
│
└── integration/                      # Kiểm thử tích hợp luồng
    └── test_sandbox_output.py        # Kiểm tra tính cô lập của thư mục Sandbox
```

---

## 2. Cơ Chế Cô Lập Sandbox (Sandbox Output Isolation)

Một trong những vấn đề nghiêm trọng nhất khi test crawler là việc sinh file rác hoặc ghi đè làm hỏng kho dữ liệu thực tế tại `data/raw/`.

Dự án đã giải quyết triệt để vấn đề này bằng cơ chế **Sandbox Output**:
* Mọi crawler đều hỗ trợ tham số `output_dir`:
  ```python
  crawler = TopCVCrawler(output_dir=str(tmp_path))
  ```
* Trong các bài test tích hợp, toàn bộ dữ liệu cào thử nghiệm được chuyển hướng ghi vào thư mục tạm `tmp_path` (được Pytest tự động tạo và xóa sạch sau khi test kết thúc).
* Thư mục `tests/test_output/` đã được cấu hình trong [`.gitignore`](../.gitignore) để tuyệt đối không bị commit file test lên GitHub.

---

## 3. Hướng Dẫn Chạy Kiểm Thử

Để chạy toàn bộ bài test:

```powershell
# 1. Chạy toàn bộ test suite và hiển thị chi tiết từng bài test:
pytest tests -v

# 2. Chạy riêng một nhóm test (ví dụ Unit Test):
pytest tests/unit -v

# 3. Chạy riêng một file test cụ thể:
pytest tests/unit/test_profiling.py -v

# 4. Chạy dừng ngay khi gặp bài test lỗi đầu tiên (-x):
pytest tests -x
```
