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
    weight_semantic: float = 0.45
    weight_skills: float = 0.30
    weight_cf: float = 0.25
    persona_id: Optional[str] = None

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
        detected_skills, target_persona, recommendations = recommend_jobs(
            candidate_profile_text=text,
            top_n=payload.top_n,
            filter_city=payload.city,
            filter_seniority=payload.seniority,
            filter_work_mode=payload.work_mode,
            weight_semantic=payload.weight_semantic,
            weight_skills=payload.weight_skills,
            weight_cf=payload.weight_cf,
            persona_id=payload.persona_id
        )
        return {
            "candidate_skills": detected_skills,
            "inferred_persona": {
                "id": target_persona.get("id", ""),
                "name": target_persona.get("name", "")
            } if target_persona else None,
            "weights": {
                "semantic": payload.weight_semantic,
                "skills": payload.weight_skills,
                "cf": payload.weight_cf
            },
            "total_matches": len(recommendations),
            "recommendations": recommendations
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
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

@router.get("/similar-jobs/{job_id}")
def get_similar_jobs_collaborative(job_id: int, top_k: int = 4):
    """
    [Collaborative Filtering: People Also Applied]
    Tìm các công việc có cùng tập ứng viên quan tâm / ứng tuyển nhiều nhất
    dựa trên ma trận tương đồng Item-to-Item Collaborative Filtering.
    """
    try:
        from src.recommender.collaborative import get_cf_recommender
        rec = get_cf_recommender()
        similar_jobs = rec.get_similar_jobs(job_id=job_id, top_k=top_k)
        return {
            "target_job_id": job_id,
            "total": len(similar_jobs),
            "similar_jobs": similar_jobs
        }
    except Exception as e:
        return {
            "target_job_id": job_id,
            "total": 0,
            "similar_jobs": [],
            "error": str(e)
        }

@router.get("/personas")
def get_cf_personas():
    """Lấy danh sách các nhóm chân dung nghề nghiệp IT (Personas) để người dùng chọn nhanh."""
    from src.recommender.synthetic_data import PERSONAS_DEF
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "skills": p["skills"][:5],
            "seniorities": p["seniorities"]
        }
        for p in PERSONAS_DEF
    ]

@router.get("/persona-feed")
def get_recommendations_by_persona(persona_id: str = "backend_java", limit: int = 10):
    """
    [Collaborative Filtering: Persona Recommendations]
    Gợi ý danh sách việc làm dựa trên xu hướng tương tác cộng đồng của nhóm ứng viên tương ứng.
    """
    try:
        from src.recommender.collaborative import get_cf_recommender
        rec = get_cf_recommender()
        jobs = rec.get_recommendations_for_persona(persona_id=persona_id, top_n=limit)
        return {
            "persona_id": persona_id,
            "total": len(jobs),
            "recommendations": jobs
        }
    except Exception as e:
        return {
            "persona_id": persona_id,
            "total": 0,
            "recommendations": [],
            "error": str(e)
        }
