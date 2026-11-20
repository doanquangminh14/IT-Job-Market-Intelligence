# Website IT Job Market (Django)

Website tra cứu và phân tích việc làm IT, đọc dữ liệu sạch (`jobs_clean.csv`) mà pipeline của repo sinh ra.

| Thành phần | Công nghệ |
| :--- | :--- |
| Backend | Python 3.11 + Django 5.2 |
| Frontend | Django Templates, HTML, CSS, JavaScript |
| UI | Bootstrap 5.3 + Bootstrap Icons, Chart.js (qua CDN) |
| Database | PostgreSQL (database riêng `it_jobs_web`), Django ORM |
| Xác thực | Django Authentication (User tùy biến) |

## Cấu trúc

```
web/
├── config/            # settings, urls, wsgi, asgi
├── apps/
│   ├── core/          # trang chủ, giới thiệu
│   ├── accounts/      # đăng ký, đăng nhập, hồ sơ ứng viên (User + Profile)
│   ├── jobs/          # Company, Skill, Job, SavedJob; danh sách/lọc, chi tiết, lưu tin; lệnh import_jobs
│   └── analytics/     # dashboard thống kê thị trường (services.py chứa các truy vấn ORM)
├── templates/         # base.html, partials/, và thư mục theo từng app
├── static/            # css/main.css, js/main.js, js/analytics.js
├── tests/             # test Django (23 test)
├── .env.example
└── manage.py
```

## Chạy lần đầu

Dùng chung `.venv` ở gốc repo (để website gọi được `src/recommender`).

```powershell
# từ thư mục gốc repo
.\.venv\Scripts\Activate.ps1
pip install -r requirements/web.txt   # chỉ website; hoặc requirements.txt để cài tất cả
pip install -e .                     # để import src.* từ web/

cd web
copy .env.example .env            # điền DB_PASSWORD, DJANGO_SECRET_KEY
# Tạo database rỗng trong PostgreSQL:  CREATE DATABASE it_jobs_web;
python manage.py migrate
python manage.py import_jobs      # nạp ../data/notebook/content_base/jobs_clean.csv
python manage.py createsuperuser  # tài khoản vào /admin
python manage.py runserver        # http://127.0.0.1:8000
```

Không có PostgreSQL? Đặt `DB_ENGINE=sqlite` trong `.env` để chạy thử bằng SQLite.

Trong VS Code: chọn interpreter `.venv`, rồi chạy cấu hình **Django: runserver (web/)** trong tab Run and Debug.

## Cập nhật dữ liệu

Sau khi pipeline sinh lại `jobs_clean.csv` (crawl ➔ `scripts/refresh_pipeline.py`):

```powershell
python manage.py import_jobs           # upsert theo job_id: tin cũ được cập nhật, tin mới được thêm
python manage.py import_jobs --clear   # xóa sạch rồi nạp lại
python manage.py import_jobs --path đường/dẫn/khác.csv
```

"Còn hạn" được tính theo ngày hôm nay (`deadline >= hôm nay`), không dùng cờ `is_active` trong file.

## Chức năng

| Trang | URL | Ghi chú |
| :--- | :--- | :--- |
| Trang chủ | `/` | Số liệu tổng, kỹ năng hot, tin mới |
| Việc làm | `/jobs/` | Lọc theo từ khóa, kỹ năng, thành phố, hình thức, loại hình, lương; mặc định chỉ tin IT còn hạn; phân trang, sắp xếp |
| Chi tiết tin | `/jobs/<id>/` | So khớp kỹ năng với hồ sơ người dùng, tin tương tự (chung kỹ năng) |
| Tin đã lưu | `/jobs/saved/` | Cần đăng nhập |
| Phân tích | `/analytics/` | Top kỹ năng, thành phố, lương theo thành phố, hình thức, loại hình, nguồn, top công ty |
| Tài khoản | `/accounts/register/`, `login/`, `profile/` | Hồ sơ gồm chức danh, kỹ năng, kinh nghiệm, thành phố, hình thức, lương: đúng đầu vào của hệ gợi ý CBF |
| Quản trị | `/admin/` | Quản lý tin, công ty, kỹ năng, người dùng |

## Kiểm thử

```powershell
python manage.py test tests
```

Test tạo database tạm `test_it_jobs_web` (user PostgreSQL cần quyền CREATEDB).

## Hướng phát triển tiếp

- App `recommender`: gọi `src.recommender` (CBF / Hybrid) với dữ liệu từ `Profile` để gợi ý việc làm.
- Ghi nhận tương tác (xem, lưu, ứng tuyển) vào DB làm dữ liệu cho Collaborative Filtering. `SavedJob` đã là một tín hiệu.
- Docker (`Dockerfile` + `docker-compose` với PostgreSQL), gunicorn + whitenoise, CI chạy test trên GitHub Actions.
