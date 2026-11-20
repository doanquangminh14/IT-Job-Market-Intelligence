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
├── Dockerfile         # image website (build từ gốc repo), gunicorn + whitenoise
├── docker-entrypoint.sh  # migrate rồi chạy gunicorn
└── manage.py
```

## Chạy lần đầu

Dùng chung `.venv` ở gốc repo (để website gọi được `src/recommender`).

```powershell
# từ thư mục gốc repo
.\.venv\Scripts\Activate.ps1
pip install -r requirements/web.txt   # chỉ website (phiên bản đã khóa); hoặc requirements.txt để cài tất cả
pip install --no-deps -e .           # để import src.* từ web/

cd web
# Cấu hình nằm trong .env ở GỐC repo (dùng chung với pipeline): copy ..\.env.example ..\.env
# rồi điền DB_PASSWORD, DJANGO_SECRET_KEY; website dùng database WEB_DB_NAME (mặc định it_jobs_web)
# Tạo database rỗng trong PostgreSQL:  CREATE DATABASE it_jobs_web;
python manage.py migrate
python manage.py import_jobs      # nạp ../data/notebook/content_base/jobs_clean.csv
python manage.py createsuperuser  # tài khoản vào /admin
python manage.py runserver        # http://127.0.0.1:8000
```

Không có PostgreSQL? Đặt `WEB_DB_ENGINE=sqlite` trong `.env` để chạy thử bằng SQLite.

Trong VS Code: chọn interpreter `.venv`, rồi chạy cấu hình **Django: runserver (web/)** trong tab Run and Debug.

## Chạy bằng Docker

Không cần cài Python hay PostgreSQL trên máy, chỉ cần Docker Desktop. `docker-compose.yml` ở gốc repo dựng 2 container: `web` (Django + gunicorn, cổng 8000) và `db` (PostgreSQL 16 riêng, dữ liệu lưu ở volume `pgdata`).

```powershell
# từ thư mục gốc repo; cần file .env (copy .env.example .env, điền DB_PASSWORD, DJANGO_SECRET_KEY)
docker compose up -d --build                              # http://localhost:8000
docker compose exec web python manage.py import_jobs      # nạp ./data (gắn vào container ở chế độ chỉ đọc)
docker compose exec web python manage.py createsuperuser
docker compose logs -f web                                # xem log
docker compose down                                       # dừng (giữ dữ liệu); thêm -v để xóa cả database
```

- Container chạy với `DJANGO_DEBUG=False`; file static do whitenoise phục vụ (đã nén gzip). Muốn bật debug: đặt `DJANGO_DEBUG_DOCKER=True` trong `.env`.
- Database trong Docker **tách biệt** với PostgreSQL trên máy (không mở cổng ra ngoài), nên cần chạy `import_jobs` một lần.
- Đưa lên server có tên miền: thêm tên miền vào `DJANGO_ALLOWED_HOSTS` và `DJANGO_CSRF_TRUSTED_ORIGINS`; nếu đứng sau reverse proxy HTTPS thì đặt `DJANGO_SECURE_SSL=True` (bật redirect HTTPS và cookie secure).

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
- CI chạy test trên GitHub Actions, tự build image Docker.
