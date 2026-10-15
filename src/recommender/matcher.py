import os
import sys
import re
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Đảm bảo đường dẫn gốc dự án
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.embeddings.generator import get_embedding_model, load_embeddings_and_metadata
from src.pipelines.silver.transformers.job_skills import get_skill_patterns

_CACHED_PATTERNS = None

def extract_candidate_skills(candidate_text: str):
    """
    Tự động trích xuất các kỹ năng công nghệ có trong CV / mô tả của ứng viên
    bằng bộ matcher 76 kỹ năng chuẩn hóa của dự án.
    """
    global _CACHED_PATTERNS
    if _CACHED_PATTERNS is None:
        _CACHED_PATTERNS = get_skill_patterns()

    if not candidate_text:
        return []

    text_lower = candidate_text.lower()
    found_skills = []
    for skill_name, pattern in _CACHED_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_skills.append(skill_name)

    return sorted(list(set(found_skills)))

def recommend_jobs(
    candidate_profile_text: str,
    top_n: int = 10,
    filter_city: str = "Tất cả",
    filter_seniority: str = "Tất cả",
    filter_work_mode: str = "Tất cả",
    weight_semantic: float = 0.65,
    weight_skills: float = 0.35
):
    """
    Gợi ý Top việc làm phù hợp nhất cho ứng viên bằng thuật toán Hybrid Content-Based:
      1. Semantic Similarity: Độ tương đồng ngữ nghĩa vector (Cosine Similarity).
      2. Skill Overlap Score: Tỷ lệ trùng khớp kỹ năng công nghệ thực tế.
      3. Áp dụng bộ lọc cứng (Thành phố, Cấp bậc, Hình thức làm việc).

    Trả về:
      - candidate_skills: Danh sách kỹ năng nhận diện được từ CV
      - recommendations: Danh sách các công việc phù hợp kèm điểm Match Score chi tiết
    """
    embeddings_matrix, metadata_list = load_embeddings_and_metadata()
    model = get_embedding_model()

    # 1. Trích xuất kỹ năng ứng viên
    candidate_skills = extract_candidate_skills(candidate_profile_text)
    candidate_skills_set = set(candidate_skills)

    # 2. Mã hóa văn bản ứng viên thành vector 384 chiều
    clean_query = candidate_profile_text.strip()
    if not clean_query:
        return candidate_skills, []

    candidate_vector = model.encode([clean_query], normalize_embeddings=True)

    # 3. Tính độ tương đồng Cosine ngữ nghĩa với toàn bộ 2,752 việc làm
    semantic_scores = cosine_similarity(candidate_vector, embeddings_matrix)[0]

    # 4. Tính toán điểm tổng hợp và lọc kết quả
    candidates_ranked = []

    for idx, meta in enumerate(metadata_list):
        # Kiểm tra bộ lọc cứng
        if filter_city != "Tất cả" and meta["city"] != filter_city:
            continue
        if filter_seniority != "Tất cả" and meta["seniority_level"] != filter_seniority:
            continue
        if filter_work_mode != "Tất cả" and meta["work_mode"] != filter_work_mode:
            continue

        sem_score = float(semantic_scores[idx])
        job_skills = meta.get("skills", [])
        job_skills_set = set(job_skills)

        # Tính Skill Overlap Score
        if candidate_skills_set and job_skills_set:
            matched_skills = sorted(list(candidate_skills_set & job_skills_set))
            missing_skills = sorted(list(job_skills_set - candidate_skills_set))
            skill_score = len(matched_skills) / max(1, len(job_skills_set))
        elif not candidate_skills_set:
            # Nếu người dùng không nhập tên kỹ năng cụ thể, dùng 100% điểm ngữ nghĩa
            matched_skills = []
            missing_skills = job_skills
            skill_score = sem_score
        else:
            matched_skills = []
            missing_skills = job_skills
            skill_score = 0.0

        # Điểm kết hợp Hybrid
        if candidate_skills_set:
            final_score = (weight_semantic * sem_score) + (weight_skills * skill_score)
        else:
            final_score = sem_score

        # Chuẩn hóa về thang phần trăm [0, 100]
        match_pct = round(max(0.0, min(1.0, final_score)) * 100, 1)

        candidates_ranked.append({
            "job_id": meta["job_id"],
            "title": meta["title"],
            "company": meta["company"],
            "company_logo_url": meta.get("company_logo_url", ""),
            "experience_str": meta.get("experience_str", "Không yêu cầu"),
            "deadline_str": meta.get("deadline_str", ""),
            "city": meta["city"],
            "work_mode": meta["work_mode"],
            "seniority_level": meta["seniority_level"],
            "salary_str": meta["salary_str"],
            "url": meta["url"],
            "match_score": match_pct,
            "semantic_score": round(sem_score * 100, 1),
            "skill_score": round(skill_score * 100, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "description_snippet": meta.get("description_snippet", ""),
            "summary": meta.get("text_summary", "")
        })

    # 5. Sắp xếp giảm dần theo điểm phù hợp
    candidates_ranked.sort(key=lambda x: x["match_score"], reverse=True)
    top_recommendations = candidates_ranked[:top_n]

    return candidate_skills, top_recommendations
