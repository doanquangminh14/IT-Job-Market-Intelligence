import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

PERSONAS_DEF = [
    {
        "id": "backend_java",
        "name": "Kỹ Sư Backend (Java / Microservices)",
        "skills": ["Java", "Spring", "Hibernate", "Microservices", "SQL", "PostgreSQL", "Docker", "Kafka", "Redis"],
        "seniorities": ["Junior", "Middle", "Senior", "Lead"],
        "target_share": 0.18
    },
    {
        "id": "frontend_react",
        "name": "Kỹ Sư Frontend (React / TypeScript)",
        "skills": ["React", "TypeScript", "JavaScript", "HTML", "CSS", "Next.js", "Redux", "Tailwind", "Vue"],
        "seniorities": ["Junior", "Middle", "Senior"],
        "target_share": 0.16
    },
    {
        "id": "fullstack_node_python",
        "name": "Kỹ Sư Fullstack (Node.js / Python / Cloud)",
        "skills": ["Node.js", "Python", "React", "TypeScript", "Express.js", "FastAPI", "MongoDB", "Docker", "PostgreSQL"],
        "seniorities": ["Junior", "Middle", "Senior", "Lead"],
        "target_share": 0.15
    },
    {
        "id": "mobile_dev",
        "name": "Lập Trình Viên Di Động (Flutter / iOS / Android)",
        "skills": ["Flutter", "React Native", "iOS", "Android", "Swift", "Kotlin", "Dart"],
        "seniorities": ["Junior", "Middle", "Senior"],
        "target_share": 0.10
    },
    {
        "id": "data_engineer",
        "name": "Kỹ Sư Dữ Liệu & Phân Tích (Data Platform / SQL)",
        "skills": ["Python", "SQL", "Spark", "Pandas", "PostgreSQL", "Data Warehouse", "Power BI", "ETL", "Kafka"],
        "seniorities": ["Middle", "Senior", "Lead"],
        "target_share": 0.12
    },
    {
        "id": "ai_ml_engineer",
        "name": "Kỹ Sư AI & Machine Learning (PyTorch / NLP / LLM)",
        "skills": ["Python", "PyTorch", "TensorFlow", "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLM"],
        "seniorities": ["Middle", "Senior", "Lead"],
        "target_share": 0.10
    },
    {
        "id": "devops_cloud",
        "name": "Kỹ Sư DevOps & Điện Toán Đám Mây (K8s / AWS)",
        "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform", "GCP", "Azure", "Git"],
        "seniorities": ["Middle", "Senior", "Lead"],
        "target_share": 0.09
    },
    {
        "id": "fresher_intern",
        "name": "Thực Tập Sinh & Sinh Viên IT Mới Tốt Nghiệp",
        "skills": ["Python", "Java", "JavaScript", "SQL", "Git", "HTML", "CSS", "C++"],
        "seniorities": ["Intern", "Fresher"],
        "target_share": 0.10
    }
]

CITIES_POOL = ["Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Tất cả"]
CITIES_WEIGHTS = [0.55, 0.35, 0.07, 0.03]

def fetch_active_jobs_with_skills() -> pd.DataFrame:
    """Truy vấn toàn bộ việc làm active và danh sách kỹ năng chuẩn hóa từ PostgreSQL."""
    query = """
        SELECT 
            j.job_id,
            j.title_normalized,
            j.seniority_level,
            j.city,
            j.work_mode,
            COALESCE(j.salary_min_vnd, 0) as salary_min,
            COALESCE(j.salary_max_vnd, 0) as salary_max,
            COALESCE(array_agg(s.skill_name) FILTER (WHERE s.skill_name IS NOT NULL), '{}') as skills
        FROM jobs j
        LEFT JOIN job_skills js ON j.job_id = js.job_id
        LEFT JOIN skills s ON js.skill_id = s.skill_id
        WHERE j.is_active = true
        GROUP BY j.job_id, j.title_normalized, j.seniority_level, j.city, j.work_mode, j.salary_min_vnd, j.salary_max_vnd
        ORDER BY j.job_id;
    """
    with get_db_connection() as conn:
        df = pd.read_sql(query, conn)
    return df

def generate_synthetic_dataset(num_users: int = 800, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """
    Sinh tập dữ liệu tương tác người dùng - việc làm (User-Item Interactions)
    với quy luật chuyên môn thực tế phục vụ huấn luyện Collaborative Filtering.
    """
    np.random.seed(seed)
    random.seed(seed)

    print("-> Dang truy van danh sach viec lam active tu PostgreSQL...")
    jobs_df = fetch_active_jobs_with_skills()
    print(f"   Lay thanh cong {len(jobs_df):,} viec lam con han (active).")

    # 1. Sinh danh sach Users
    users_list = []
    user_id_counter = 1

    for persona in PERSONAS_DEF:
        persona_users_count = int(num_users * persona["target_share"])
        for _ in range(persona_users_count):
            # Chọn ngẫu nhiên 3 đến 6 kỹ năng đặc trưng của persona
            num_skills = random.randint(3, min(6, len(persona["skills"])))
            user_skills = random.sample(persona["skills"], num_skills)
            user_seniority = random.choice(persona["seniorities"])
            user_city = np.random.choice(CITIES_POOL, p=CITIES_WEIGHTS)

            users_list.append({
                "user_id": user_id_counter,
                "persona_id": persona["id"],
                "persona_name": persona["name"],
                "seniority": user_seniority,
                "city": user_city,
                "skills": user_skills
            })
            user_id_counter += 1

    # Bổ sung bù nếu chưa đủ num_users
    while len(users_list) < num_users:
        p = random.choice(PERSONAS_DEF)
        users_list.append({
            "user_id": user_id_counter,
            "persona_id": p["id"],
            "persona_name": p["name"],
            "seniority": random.choice(p["seniorities"]),
            "city": np.random.choice(CITIES_POOL, p=CITIES_WEIGHTS),
            "skills": random.sample(p["skills"], 4)
        })
        user_id_counter += 1

    users_df = pd.DataFrame(users_list)
    print(f"-> Da tao thanh cong {len(users_df):,} ung vien mo phong (Users) qua 8 personas.")

    # 2. Xay dung ma tran tuong tac (User - Job Interactions)
    interactions_list = []
    base_date = datetime.now() - timedelta(days=60)

    # Chuyển đổi job skills thành tập hợp để so khớp nhanh
    jobs_records = jobs_df.to_dict(orient="records")
    for j in jobs_records:
        j["skills_set"] = set(j["skills"])

    print("-> Dang mo phong luot tuong tac (View, Bookmark, Apply) dua tren do phu hop ky nang...")

    for _, user in users_df.iterrows():
        u_id = user["user_id"]
        u_skills = set(user["skills"])
        u_sen = user["seniority"]
        u_city = user["city"]

        # Tính điểm tương hợp của user với từng job
        candidate_scores = []
        for job in jobs_records:
            j_skills = job["skills_set"]
            # 1. Điểm kỹ năng (Jaccard hoặc tỷ lệ kỹ năng trùng)
            intersection = len(u_skills.intersection(j_skills))
            skill_score = intersection / max(1, len(u_skills))

            # 2. Điểm cấp bậc
            sen_score = 0.0
            if job["seniority_level"] == u_sen:
                sen_score = 1.0
            elif u_sen == "Senior" and job["seniority_level"] in ["Middle", "Lead"]:
                sen_score = 0.6
            elif u_sen == "Middle" and job["seniority_level"] in ["Junior", "Senior"]:
                sen_score = 0.6
            elif u_sen in ["Intern", "Fresher"] and job["seniority_level"] in ["Intern", "Fresher", "Junior"]:
                sen_score = 0.8

            # 3. Điểm địa điểm
            city_score = 0.5
            if u_city == "Tất cả" or job["city"] == u_city or job["work_mode"] == "Remote":
                city_score = 1.0
            elif job["city"] == "Toàn quốc":
                city_score = 0.8

            total_affinity = 0.55 * skill_score + 0.30 * sen_score + 0.15 * city_score

            # Chỉ giữ các job có độ tương hợp tối thiểu
            if total_affinity >= 0.25 or (intersection >= 1 and sen_score >= 0.5):
                candidate_scores.append((job["job_id"], total_affinity))

        # Nếu không có ứng viên nào đủ cao, lấy ngẫu nhiên 5 job cùng cấp bậc
        if not candidate_scores:
            same_sen_jobs = [j["job_id"] for j in jobs_records if j["seniority_level"] == u_sen]
            if not same_sen_jobs:
                same_sen_jobs = [j["job_id"] for j in jobs_records[:50]]
            sampled = random.sample(same_sen_jobs, min(10, len(same_sen_jobs)))
            candidate_scores = [(jid, 0.3) for jid in sampled]

        # Sắp xếp và chọn top candidate jobs với yếu tố ngẫu nhiên (Softmax/Weighted sample)
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidate_scores[:80]

        # Số lượng tương tác của người dùng này: 15 đến 40 lượt
        num_interactions = random.randint(15, min(40, len(top_candidates)))
        probs = np.array([score for _, score in top_candidates])
        probs = probs / probs.sum()

        chosen_indices = np.random.choice(len(top_candidates), size=num_interactions, replace=False, p=probs)
        chosen_jobs = [top_candidates[idx] for idx in chosen_indices]

        for j_id, affinity in chosen_jobs:
            # Mô phỏng hành vi:
            # Mọi tương tác đều bắt đầu bằng view (weight = 1)
            # Nếu affinity cao -> có xác suất bookmark (weight = 2) và apply (weight = 3)
            rating = 1.0
            action = "view"

            rand_val = random.random()
            if affinity >= 0.6 and rand_val < 0.45:
                action = "apply"
                rating = 3.0
            elif affinity >= 0.4 and rand_val < 0.65:
                action = "bookmark"
                rating = 2.0

            random_days = random.randint(0, 58)
            random_secs = random.randint(0, 86400)
            interaction_time = base_date + timedelta(days=random_days, seconds=random_secs)

            interactions_list.append({
                "user_id": u_id,
                "job_id": j_id,
                "action": action,
                "rating": rating,
                "affinity_score": round(affinity, 3),
                "timestamp": interaction_time.strftime("%Y-%m-%d %H:%M:%S")
            })

    interactions_df = pd.DataFrame(interactions_list)
    print(f"-> Tong cong da sinh duoc: {len(interactions_df):,} luot tuong tac User-Job.")
    print(f"   Phan bo hanh vi: View={sum(interactions_df['action']=='view'):,}, Bookmark={sum(interactions_df['action']=='bookmark'):,}, Apply={sum(interactions_df['action']=='apply'):,}")

    return users_df, interactions_df, PERSONAS_DEF

def save_synthetic_data(users_df: pd.DataFrame, interactions_df: pd.DataFrame, personas: List[Dict[str, Any]]):
    """Lưu trữ dữ liệu tương tác mô phỏng vào thư mục data/interactions/."""
    out_dir = os.path.join(PROJECT_ROOT, "data", "interactions")
    os.makedirs(out_dir, exist_ok=True)

    interactions_file = os.path.join(out_dir, "user_interactions.csv")
    users_file = os.path.join(out_dir, "users_metadata.json")
    personas_file = os.path.join(out_dir, "personas_metadata.json")

    interactions_df.to_csv(interactions_file, index=False, encoding="utf-8")
    users_df.to_json(users_file, orient="records", force_ascii=False, indent=2)

    with open(personas_file, "w", encoding="utf-8") as f:
        json.dump(personas, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print("   HOAN TAT SINH DU LIEU TUONG TAC MO PHONG (COLLABORATIVE FILTERING)")
    print("=" * 75)
    print(f" - Tep tuong tac User-Job: {interactions_file} ({len(interactions_df):,} ban ghi)")
    print(f" - Tep ho so ung vien    : {users_file} ({len(users_df):,} ung vien)")
    print(f" - Tep danh muc Personas : {personas_file} ({len(personas)} nhom)")
    print("=" * 75)

if __name__ == "__main__":
    users_df, interactions_df, personas = generate_synthetic_dataset(num_users=800)
    save_synthetic_data(users_df, interactions_df, personas)
