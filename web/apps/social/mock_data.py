"""Dữ liệu DEMO cho trang Cộng đồng (thảo luận #002).

Không phải người dùng thật. Stage 1 hiển thị trực tiếp; từ Stage 2 chỉ được nạp vào DB bằng
`python manage.py seed_community`, lệnh này chỉ chạy khi settings.COMMUNITY_DEMO bật (DEBUG).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _t(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=_TZ)


USERS = [
    {"username": "lan.nguyen", "title": "Sinh viên năm 3 – Khoa học máy tính",
     "skills": ["Python", "SQL", "Machine Learning"], "bio": "Đang tìm hướng đi cho Data Science."},
    {"username": "huy.dev", "title": "Junior Backend Developer",
     "skills": ["Java", "Spring Boot", "Docker"], "bio": "1 năm kinh nghiệm backend, thích chia sẻ."},
    {"username": "minh.fe", "title": "Frontend Developer",
     "skills": ["JavaScript", "React", "TypeScript"], "bio": "UI/UX và hiệu năng web."},
    {"username": "thao.data", "title": "Data Analyst",
     "skills": ["SQL", "Power BI", "Python"], "bio": "Phân tích dữ liệu tuyển dụng."},
    {"username": "quang.devops", "title": "DevOps Engineer",
     "skills": ["Docker", "Kubernetes", "AWS"], "bio": "CI/CD, cloud, observability."},
    {"username": "an.intern", "title": "Thực tập sinh QA",
     "skills": ["Testing", "Selenium"], "bio": "Mới vào nghề, hỏi nhiều."},
]

# Người dùng demo mặc định "đang theo dõi" (để tab Đang theo dõi không trống khi mới vào)
FOLLOWING_SEED = ["huy.dev", "thao.data"]

POSTS = [
    {"id": 1, "author": "lan.nguyen", "created_at": _t(24, 9, 15), "tags": ["Python", "Machine Learning"], "job_id": None,
     "like_count": 12,
     "body": "Mình đang học năm 3, muốn đi theo Data Science. Nên tập trung Python + SQL trước hay học luôn Machine Learning ạ?"},
    {"id": 2, "author": "huy.dev", "created_at": _t(24, 8, 40), "tags": ["Java", "Spring Boot"], "job_id": None,
     "like_count": 25,
     "body": "Chia sẻ sau 1 năm làm backend: viết test sớm giúp mình tự tin refactor hơn rất nhiều. Đừng để đến lúc có bug production mới viết."},
    {"id": 3, "author": "thao.data", "created_at": _t(23, 21, 5), "tags": ["SQL", "Power BI"], "job_id": None,
     "like_count": 18,
     "body": "Theo trang Phân tích thị trường, SQL nằm trong top kỹ năng được yêu cầu. Ai mới vào nghề data thì đầu tư SQL thật chắc nhé."},
    {"id": 4, "author": "minh.fe", "created_at": _t(23, 16, 30), "tags": ["React", "TypeScript"], "job_id": None,
     "like_count": 9,
     "body": "Chuyển dự án React sang TypeScript dần dần: bật strict từng thư mục một, đừng đổi cả repo trong một PR."},
    {"id": 5, "author": "quang.devops", "created_at": _t(23, 11, 0), "tags": ["Docker", "Kubernetes"], "job_id": None,
     "like_count": 14,
     "body": "Mẹo nhỏ: dùng multi-stage build cho Docker image, image production của team mình giảm từ 1.2GB xuống 180MB."},
    {"id": 6, "author": "an.intern", "created_at": _t(22, 20, 45), "tags": ["Testing"], "job_id": None,
     "like_count": 6,
     "body": "Thực tập QA tuần đầu: học cách viết bug report rõ ràng (bước tái hiện, kết quả mong đợi, kết quả thực tế). Có tài liệu nào hay không mọi người?"},
    {"id": 7, "author": "huy.dev", "created_at": _t(22, 14, 20), "tags": ["Docker"], "job_id": None,
     "like_count": 11,
     "body": "Lần đầu dùng docker compose cho môi trường dev: một lệnh là có đủ PostgreSQL + Redis. Không còn câu 'máy em chạy được'."},
    {"id": 8, "author": "lan.nguyen", "created_at": _t(22, 10, 0), "tags": ["SQL"], "job_id": None,
     "like_count": 4,
     "body": "Có ai biết bộ bài tập SQL nào luyện window function tốt không? Mình đang chuẩn bị phỏng vấn thực tập."},
    {"id": 9, "author": "thao.data", "created_at": _t(21, 19, 30), "tags": ["Python"], "job_id": None,
     "like_count": 20,
     "body": "pandas đủ dùng cho phần lớn bài toán phân tích. Khi dữ liệu > vài GB mới cần nghĩ tới công cụ khác."},
    {"id": 10, "author": "minh.fe", "created_at": _t(21, 9, 10), "tags": ["JavaScript"], "job_id": None,
     "like_count": 7,
     "body": "Đo trước khi tối ưu: Lighthouse + tab Performance của DevTools chỉ ra đúng chỗ chậm nhanh hơn đoán mò."},
    {"id": 11, "author": "quang.devops", "created_at": _t(20, 22, 0), "tags": ["AWS"], "job_id": None,
     "like_count": 8,
     "body": "Đặt budget alert trên AWS ngay từ ngày đầu. Bài học xương máu từ một con EC2 quên tắt."},
    {"id": 12, "author": "an.intern", "created_at": _t(20, 15, 25), "tags": ["Selenium", "Testing"], "job_id": None,
     "like_count": 3,
     "body": "Viết được test Selenium đầu tiên chạy trong CI. Chậm nhưng vui!"},
]

COMMENTS = [
    {"id": 1, "post_id": 1, "author": "thao.data", "created_at": _t(24, 9, 40),
     "body": "Python + SQL trước nhé, nền tảng đó dùng cả khi làm ML sau này."},
    {"id": 2, "post_id": 1, "author": "huy.dev", "created_at": _t(24, 10, 5),
     "body": "Đồng ý, thêm một chút thống kê cơ bản nữa là đẹp."},
    {"id": 3, "post_id": 2, "author": "an.intern", "created_at": _t(24, 9, 0),
     "body": "Cảm ơn anh, em đang tập viết unit test cho project cá nhân."},
    {"id": 4, "post_id": 5, "author": "huy.dev", "created_at": _t(23, 12, 0),
     "body": "Multi-stage build đúng là cứu tinh."},
    {"id": 5, "post_id": 8, "author": "thao.data", "created_at": _t(22, 11, 30),
     "body": "Thử LeetCode phần Database và trang 'SQL window functions' của Mode nhé."},
]
