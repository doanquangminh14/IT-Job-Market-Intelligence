import os
import sys
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.recommender.matcher import recommend_jobs, extract_candidate_skills

router = APIRouter(prefix="/api/recommender", tags=["Recommender"])

class RecommendRequest(BaseModel):
    profile_text: str
    top_n: int = 12
    city: str = "Tất cả"
    seniority: str = "Tất cả"
    work_mode: str = "Tất cả"
    weight_semantic: float = 0.65
    weight_skills: float = 0.35

@router.post("/match")
def match_jobs_for_candidate(payload: RecommendRequest):
    """
    Tiếp nhận thông tin hồ sơ ứng viên (đoạn văn bản CV hoặc nguyện vọng),
    trích xuất kỹ năng và tính toán độ tương đồng Hybrid (Vector + Kỹ năng).
    """
    text = payload.profile_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp nội dung CV hoặc mô tả nguyện vọng nghề nghiệp.")

    try:
        detected_skills, recommendations = recommend_jobs(
            candidate_profile_text=text,
            top_n=payload.top_n,
            filter_city=payload.city,
            filter_seniority=payload.seniority,
            filter_work_mode=payload.work_mode,
            weight_semantic=payload.weight_semantic,
            weight_skills=payload.weight_skills
        )
        return {
            "candidate_skills": detected_skills,
            "total_matches": len(recommendations),
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình tính toán gợi ý: {str(e)}")

@router.get("/presets")
def get_preset_profiles():
    """Danh sách các hồ sơ mẫu để người dùng thử nghiệm nhanh."""
    return [
        {
            "id": "fresher_da",
            "name": "Fresher Data Analyst",
            "subtitle": "SQL / Python / Power BI",
            "text": "Tôi là sinh viên mới tốt nghiệp ngành Công nghệ thông tin / Hệ thống thông tin, có nền tảng tốt về truy vấn dữ liệu SQL, phân tích dữ liệu với Python (Pandas, NumPy) và trực quan hóa báo cáo trên Power BI. Mong muốn tìm kiếm cơ hội việc làm vị trí Fresher hoặc Junior Data Analyst, sẵn sàng học hỏi thêm về Data Warehouse và Business Intelligence."
        },
        {
            "id": "junior_fe",
            "name": "Junior Frontend Developer",
            "subtitle": "React / TypeScript / Next.js",
            "text": "Lập trình viên Frontend có 1-2 năm kinh nghiệm làm việc chuyên sâu với React, TypeScript, Next.js, HTML5, CSS3, Tailwind CSS và thiết kế giao diện Figma. Có kinh nghiệm xây dựng ứng dụng Web responsive đa thiết bị, tối ưu hóa tốc độ tải trang và kết nối RESTful API."
        },
        {
            "id": "backend_java",
            "name": "Java Spring Boot Backend",
            "subtitle": "Java / Spring Boot / PostgreSQL",
            "text": "Kỹ sư Backend với 2-3 năm kinh nghiệm lập trình Java, thành thạo framework Spring Boot, Spring Framework và kiến trúc Microservices. Nắm vững cơ sở dữ liệu quan hệ PostgreSQL, MySQL, thiết kế RESTful API chuẩn mực, tối ưu hóa câu lệnh truy vấn và xử lý caching với Redis."
        },
        {
            "id": "cloud_devops",
            "name": "Cloud & DevOps Engineer",
            "subtitle": "AWS / Docker / Kubernetes / CI-CD",
            "text": "Kỹ sư DevOps có kinh nghiệm quản trị hạ tầng đám mây AWS, đóng gói ứng dụng bằng Docker và điều phối cụm Kubernetes (K8s). Thành thạo thiết lập quy trình tự động hóa CI/CD pipeline, quản trị hệ điều hành Linux và giám sát hệ thống với Prometheus, Grafana."
        }
    ]
