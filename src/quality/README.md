# 🛡️ Data Quality Module (`src/quality`)

Module chịu trách nhiệm kiểm định chất lượng dữ liệu (Data Quality Gate) và phân luồng bản ghi từ kho dữ liệu thô (`data/raw/`) trước khi đưa vào kho sạch (`data/bronze/`).

---

## 1. Cấu Trúc Thư Mục

```
src/quality/
├── __init__.py           # Export QualityValidator, rules và các mã lỗi
├── rules.py              # Định nghĩa các quy tắc kiểm tra tính Hợp Lệ (Valid Rules)
└── validator.py          # Động cơ kiểm tra, gắn metadata DQ và lưu vào Bronze
```

---

## 2. Tiêu Chuẩn Luồng Hợp Lệ (Valid Rules)

Một bản ghi được gắn nhãn `_dq_status: "valid"` khi vượt qua toàn bộ 3 nhóm bài kiểm tra:

1. **Định danh & URL (`check_identity_and_url`)**:
   - `job_url` bắt buộc có và là HTTP/HTTPS URL hợp lệ.
   - `source_job_id` hoặc `detail_id` không được để trống.
   - Mã lỗi nếu vi phạm: `ERR_MISSING_JOB_URL`, `ERR_MISSING_JOB_ID`.

2. **Thông tin tuyển dụng cốt lõi (`check_core_info`)**:
   - `title_raw` không được để trống (độ dài $\ge 2$ ký tự).
   - `source` phải thuộc danh sách sàn hợp lệ (`topcv`, `topdev`, `vietnamworks`).
   - Mã lỗi nếu vi phạm: `ERR_MISSING_TITLE`, `ERR_MISSING_SOURCE`.

3. **Chống chặn bot / Trang lỗi (`check_content_length`)**:
   - Tổng độ dài các trường mô tả (`overview_raw` + `responsibilities_raw` + `requirements_raw` + `benefits_raw`) phải đạt tối thiểu **100 ký tự**.
   - Giúp lọc bỏ các trang bị Cloudflare chặn, Captcha hoặc bài tuyển dụng rác/rỗng.
   - Mã lỗi nếu vi phạm: `ERR_CONTENT_TOO_SHORT`.

---

## 3. Cách Sử Dụng CLI (`main_quality.py`)

Chạy kiểm định và xem thống kê (Dry-Run, không ghi đè dữ liệu):
```bash
python main_quality.py
```

Chỉ kiểm định ngày gần nhất:
```bash
python main_quality.py --latest
```

Kiểm định và lưu các bản ghi Hợp Lệ vào tầng Bronze (`data/bronze/`):
```bash
python main_quality.py --save-bronze
```

Chỉ kiểm định một sàn cụ thể:
```bash
python main_quality.py --source topcv
```

---

## 4. Kiểm Thử (Unit Tests)

Bộ unit test kiểm tra toàn diện các quy tắc và validator:
```bash
pytest tests/unit/test_data_quality.py -v
```
