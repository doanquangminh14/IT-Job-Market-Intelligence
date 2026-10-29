import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.api.routes_jobs import router as jobs_router
from src.api.routes_recommender import router as recommender_router
from src.api.routes_analytics import router as analytics_router

app = FastAPI(
    title="IT Job Market Intelligence Platform",
    description="Hệ thống thông minh phân tích thị trường và gợi ý việc làm CNTT Việt Nam",
    version="2.2.0"
)
# Tech Stacks Analysis v2.2.0


# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các API Routers
app.include_router(jobs_router)
app.include_router(recommender_router)
app.include_router(analytics_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "IT-Job-Market-Intelligence",
        "version": "2.0.0"
    }

# Phục vụ thư mục Web tĩnh (Frontend)
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
if not os.path.exists(WEB_DIR):
    os.makedirs(WEB_DIR, exist_ok=True)

# Mount thư mục tĩnh
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_home():
    """Phục vụ trực tiếp giao diện Web chính của nền tảng."""
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "IT Job Market Intelligence Web App đang khởi tạo giao diện."}
