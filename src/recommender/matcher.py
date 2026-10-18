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

from typing import Optional, List, Dict, Any, Tuple
from src.embeddings.generator import get_embedding_model, load_embeddings_and_metadata
from src.pipelines.silver.transformers.job_skills import get_skill_patterns
from src.recommender.synthetic_data import PERSONAS_DEF
from src.recommender.collaborative import get_cf_recommender

_CACHED_PATTERNS = None

# Bổ sung các kỹ năng phân tích / công cụ phổ biến từ hồ sơ ứng viên
EXTRA_CANDIDATE_SKILLS = {
    "Excel": r"(?:\bexcel\b|\bms\s*excel\b|\bmicrosoft\s*excel\b)",
    "Power BI": r"(?:\bpower\s*bi\b|\bpowerbi\b)",
    "Tableau": r"\btableau\b",
    "Figma": r"\bfigma\b",
    "Firebase": r"\bfirebase\b",
    "GraphQL": r"\bgraphql\b",
    "Airflow": r"(?:\bairflow\b|\bapache\s*airflow\b)",
    "GitLab": r"\bgitlab\b",
    "GitHub": r"\bgithub\b",
    "LangChain": r"(?:\blangchain\b|\blang\s*chain\b)",
    "RAG": r"(?:\brag\b|\bretrieval[\s-]augmented\b)"
}

DOMAIN_CLUES = {
    "data_engineer": [
        "phân tích dữ liệu", "data analyst", "data analysis", "dữ liệu", "data engineer",
        "business intelligence", "bi", "data warehouse", "báo cáo", "thống kê", "analytics",
        "power bi", "excel", "tableau", "dwh", "etl", "big data", "spark", "pipeline dữ liệu"
    ],
    "frontend_react": [
        "frontend", "front-end", "giao diện", "react", "vue", "angular", "ui/ux",
        "web frontend", "html", "css", "tailwind", "next.js", "client-side", "responsive"
    ],
    "backend_java": [
        "backend", "back-end", "java", "spring", "spring boot", "microservices",
        "api backend", "server", "hibernate", "jpa", "restful api", "phát triển máy chủ"
    ],
    "fullstack_node_python": [
        "fullstack", "full-stack", "node.js", "python backend", "django", "fastapi",
        "express", "toàn diện", "lập trình fullstack", "web app"
    ],
    "mobile_dev": [
        "mobile", "di động", "android", "ios", "flutter", "react native", "swift",
        "kotlin", "app di động", "ứng dụng di động", "lập trình app"
    ],
    "ai_ml_engineer": [
        "ai", "machine learning", "trí tuệ nhân tạo", "deep learning", "nlp", "llm",
        "computer vision", "khoa học dữ liệu", "data science", "pytorch", "tensorflow",
        "thị giác máy tính", "xử lý ngôn ngữ tự nhiên", "rag", "genai", "học máy"
    ],
    "devops_cloud": [
        "devops", "cloud", "hạ tầng", "ci/cd", "kubernetes", "aws", "docker",
        "sysadmin", "hệ thống", "quản trị mạng", "điện toán đám mây", "terraform", "linux"
    ],
    "fresher_intern": [
        "fresher", "intern", "thực tập", "thực tập sinh", "mới tốt nghiệp", "sinh viên",
        "chưa có kinh nghiệm", "entry-level", "trainee", "tìm chỗ thực tập"
    ]
}

def extract_candidate_skills(candidate_text: str):
    """
    Tự động trích xuất các kỹ năng công nghệ có trong CV / mô tả của ứng viên
    bằng bộ matcher 76 kỹ năng chuẩn hóa của dự án kết hợp các công cụ dữ liệu phổ biến.
    """
    global _CACHED_PATTERNS
    if _CACHED_PATTERNS is None:
        _CACHED_PATTERNS = dict(get_skill_patterns())
        _CACHED_PATTERNS.update(EXTRA_CANDIDATE_SKILLS)

    if not candidate_text:
        return []

    text_lower = candidate_text.lower()
    found_skills = []
    for skill_name, pattern in _CACHED_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_skills.append(skill_name)

    return sorted(list(set(found_skills)))

def infer_persona_from_skills(candidate_skills: List[str], raw_text: str = "") -> Dict[str, Any]:
    """
    Tự động suy luận Persona / Career Track phù hợp nhất dựa trên:
    1. Kỹ năng phát hiện từ CV (Skill Overlap)
    2. Từ khóa chuyên ngành xuất hiện trong văn bản mô tả (Domain Clues)
    """
    cand_set = set(candidate_skills)
    raw_lower = raw_text.lower() if raw_text else ""
    best_persona = PERSONAS_DEF[0]
    best_score = -1.0

    for p in PERSONAS_DEF:
        pid = p["id"]
        skills_in_p = set(p.get("skills", []))
        if pid == "data_engineer":
            skills_in_p = skills_in_p.union({"Excel", "Tableau", "Power BI"})

        overlap = len(cand_set.intersection(skills_in_p))
        score = float(overlap)

        # Cộng điểm ưu tiên nếu văn bản chứa từ khóa đặc trưng của chuyên ngành
        clues = DOMAIN_CLUES.get(pid, [])
        for clue in clues:
            if clue in raw_lower:
                score += 1.5

        if score > best_score:
            best_score = score
            best_persona = p

    return best_persona

def recommend_jobs(
    candidate_profile_text: str,
    top_n: int = 10,
    filter_city: str = "Tất cả",
    filter_seniority: str = "Tất cả",
    filter_work_mode: str = "Tất cả",
    weight_semantic: float = 0.45,
    weight_skills: float = 0.30,
    weight_cf: float = 0.25,
    persona_id: Optional[str] = None
) -> Tuple[List[str], Dict[str, Any], List[Dict[str, Any]]]:
    """
    [TRUE HYBRID RECOMMENDATION SYSTEM]
    Kết hợp cả 3 nguồn tri thức định lượng:
      1. Semantic Similarity (NLP 384d Vector): Hiểu ngữ cảnh mục tiêu nghề nghiệp, kinh nghiệm trong CV.
      2. Skill Overlap (Jaccard Match): Đảm bảo đáp ứng danh mục Tech Stack cốt lõi của công việc.
      3. Collaborative Filtering (TruncatedSVD Persona Factorization): Khai thác hành vi ứng tuyển của cộng đồng lập trình viên cùng chuyên ngành.
    
    Công thức True Hybrid:
      Final_Score = (0.45 * Semantic) + (0.30 * Skills) + (0.25 * Collaborative_Filtering)
    """
    embeddings_matrix, metadata_list = load_embeddings_and_metadata()
    model = get_embedding_model()

    # 1. Trích xuất kỹ năng ứng viên
    candidate_skills = extract_candidate_skills(candidate_profile_text)
    candidate_skills_set = set(candidate_skills)

    # 2. Xác định nhóm chân dung nghề nghiệp (Persona) để lấy vector CF
    if persona_id and persona_id != "auto":
        target_persona = next((p for p in PERSONAS_DEF if p["id"] == persona_id), None)
        if not target_persona:
            target_persona = infer_persona_from_skills(candidate_skills, candidate_profile_text)
    else:
        target_persona = infer_persona_from_skills(candidate_skills, candidate_profile_text)

    # 3. Lấy ma trận điểm tương thích Collaborative Filtering từ SVD Matrix Factorization
    cf_scores_map = {}
    try:
        cf_rec = get_cf_recommender()
        cf_scores_map = cf_rec.get_persona_scores_dict(target_persona["id"])
    except Exception as e:
        print(f"Lưu ý: Không thể tải điểm CF, sử dụng fallback mặc định: {e}")

    # 4. Mã hóa văn bản ứng viên thành vector 384 chiều
    clean_query = candidate_profile_text.strip()
    if not clean_query:
        return candidate_skills, target_persona, []

    candidate_vector = model.encode([clean_query], normalize_embeddings=True)

    # 5. Tính độ tương đồng Cosine ngữ nghĩa với toàn bộ việc làm
    semantic_scores = cosine_similarity(candidate_vector, embeddings_matrix)[0]

    # 6. Tính toán điểm tổng hợp True Hybrid và lọc kết quả
    candidates_ranked = []
    total_items = min(len(metadata_list), len(semantic_scores))

    for idx in range(total_items):
        meta = metadata_list[idx]
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
            matched_skills = []
            missing_skills = job_skills
            skill_score = sem_score
        else:
            matched_skills = []
            missing_skills = job_skills
            skill_score = 0.0

        # Lấy điểm Collaborative Filtering cho công việc này
        job_id = meta["job_id"]
        cf_score = float(cf_scores_map.get(job_id, 0.68))

        # Điểm True Hybrid: 45% NLP + 30% Kỹ Năng + 25% Lọc Cộng Tác CF
        final_score = (weight_semantic * sem_score) + (weight_skills * skill_score) + (weight_cf * cf_score)

        # Chuẩn hóa về thang phần trăm [0, 100]
        match_pct = round(max(0.0, min(1.0, final_score)) * 100, 1)

        candidates_ranked.append({
            "job_id": job_id,
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
            "cf_score": round(cf_score * 100, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "description_snippet": meta.get("description_snippet", ""),
            "summary": meta.get("text_summary", "")
        })

    # 7. Sắp xếp giảm dần theo điểm phù hợp True Hybrid
    candidates_ranked.sort(key=lambda x: x["match_score"], reverse=True)
    top_recommendations = candidates_ranked[:top_n]

    return candidate_skills, target_persona, top_recommendations

