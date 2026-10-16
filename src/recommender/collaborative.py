import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

MODELS_DIR = os.path.join(PROJECT_ROOT, "data", "models")
INTERACTIONS_DIR = os.path.join(PROJECT_ROOT, "data", "interactions")

_CACHED_CF = None

class CollaborativeRecommender:
    """
    Hệ thống gợi ý việc làm Lọc cộng tác (Collaborative Filtering):
    1. Item-to-Item CF: Tìm các công việc có cùng tập ứng viên tương tác (People Also Applied).
    2. Matrix Factorization (TruncatedSVD): Dự đoán sở thích ứng viên qua không gian vector tiềm ẩn.
    """
    def __init__(self, n_components: int = 30):
        self.n_components = n_components
        self.user_to_idx: Dict[int, int] = {}
        self.idx_to_user: Dict[int, int] = {}
        self.job_to_idx: Dict[int, int] = {}
        self.idx_to_job: Dict[int, int] = {}
        self.item_sim_matrix: Optional[np.ndarray] = None
        self.svd_model: Optional[TruncatedSVD] = None
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self.metrics: Dict[str, Any] = {}
        self.jobs_meta: Dict[int, Dict[str, Any]] = {}

    def load_data(self) -> pd.DataFrame:
        csv_path = os.path.join(INTERACTIONS_DIR, "user_interactions.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Chưa có tệp tương tác {csv_path}. Vui lòng chạy synthetic_data.py trước.")
        df = pd.read_csv(csv_path)
        return df

    def _load_jobs_metadata(self):
        """Tải metadata việc làm từ PostgreSQL để hiển thị kèm kết quả gợi ý."""
        query = """
            SELECT 
                j.job_id,
                j.title_normalized,
                c.company_name_normalized,
                c.company_logo_url,
                j.city,
                j.seniority_level,
                j.work_mode,
                COALESCE(j.salary_min_vnd, 0) as sal_min,
                COALESCE(j.salary_max_vnd, 0) as sal_max,
                COALESCE(array_agg(s.skill_name) FILTER (WHERE s.skill_name IS NOT NULL), '{}') as skills
            FROM jobs j
            LEFT JOIN companies c ON j.company_id = c.company_id
            LEFT JOIN job_skills js ON j.job_id = js.job_id
            LEFT JOIN skills s ON js.skill_id = s.skill_id
            WHERE j.is_active = true
            GROUP BY j.job_id, j.title_normalized, c.company_name_normalized, c.company_logo_url, j.city, j.seniority_level, j.work_mode, j.salary_min_vnd, j.salary_max_vnd;
        """
        try:
            with get_db_connection() as conn:
                df = pd.read_sql(query, conn)
                for _, r in df.iterrows():
                    s_min = r["sal_min"] / 1e6 if r["sal_min"] else 0
                    s_max = r["sal_max"] / 1e6 if r["sal_max"] else 0
                    if s_min > 0 and s_max > 0:
                        sal_str = f"{s_min:.1f} - {s_max:.1f} triệu VNĐ"
                    elif s_max > 0:
                        sal_str = f"Lên đến {s_max:.1f} triệu VNĐ"
                    else:
                        sal_str = "Thỏa thuận"

                    self.jobs_meta[int(r["job_id"])] = {
                        "job_id": int(r["job_id"]),
                        "title": r["title_normalized"],
                        "company_name": r["company_name_normalized"],
                        "company_logo_url": r["company_logo_url"],
                        "city": r["city"],
                        "seniority": r["seniority_level"],
                        "work_mode": r["work_mode"],
                        "salary_str": sal_str,
                        "skills": list(r["skills"])[:5]
                    }
        except Exception as e:
            print(f"Cảnh báo: Không thể tải metadata việc làm từ DB: {e}")

    def train(self, df_interactions: Optional[pd.DataFrame] = None):
        """Huấn luyện mô hình Item-to-Item Similarity và TruncatedSVD Matrix Factorization."""
        if df_interactions is None:
            df_interactions = self.load_data()

        self._load_jobs_metadata()

        print(f"-> Chuẩn bị ma trận tương tác từ {len(df_interactions):,} lượt tương tác...")
        unique_users = sorted(df_interactions["user_id"].unique())
        unique_jobs = sorted(df_interactions["job_id"].unique())

        self.user_to_idx = {uid: i for i, uid in enumerate(unique_users)}
        self.idx_to_user = {i: uid for i, uid in enumerate(unique_users)}
        self.job_to_idx = {jid: i for i, jid in enumerate(unique_jobs)}
        self.idx_to_job = {i: jid for i, jid in enumerate(unique_jobs)}

        n_users = len(unique_users)
        n_jobs = len(unique_jobs)
        print(f"   Kích thước ma trận: {n_users:,} Users x {n_jobs:,} Jobs (Sparsity: {100 - len(df_interactions)/(n_users*n_jobs)*100:.2f}%)")

        # Chia tập Train/Test (80/20) để đánh giá offline
        train_df, test_df = train_test_split(df_interactions, test_size=0.2, random_state=42)

        # Xây dựng ma trận Train
        row_indices = [self.user_to_idx[uid] for uid in train_df["user_id"]]
        col_indices = [self.job_to_idx[jid] for jid in train_df["job_id"]]
        ratings = train_df["rating"].values

        R_train = sp.csr_matrix((ratings, (row_indices, col_indices)), shape=(n_users, n_jobs), dtype=np.float32)

        # 1. HUẤN LUYỆN ITEM-BASED COLLABORATIVE FILTERING (COSINE SIMILARITY)
        print("-> [Mô hình 1] Đang tính ma trận Item-to-Item Cosine Similarity...")
        # Chuẩn hóa L2 norm theo cột (items)
        item_user_matrix = R_train.T.tocsr()  # Shape: (n_jobs, n_users)
        
        # Thêm epsilon để tránh chia cho 0
        norms = sp.linalg.norm(item_user_matrix, axis=1)
        norms[norms == 0] = 1.0
        normalized_items = item_user_matrix.multiply(sp.csr_matrix(1.0 / norms.reshape(-1, 1)))

        # S = (Items_norm) * (Items_norm)^T
        sim_sparse = normalized_items.dot(normalized_items.T)
        self.item_sim_matrix = sim_sparse.toarray()
        np.fill_diagonal(self.item_sim_matrix, 0.0)  # Bỏ đường chéo chính (tự tương đồng với chính nó)

        # 2. HUẤN LUYỆN MATRIX FACTORIZATION (TRUNCATED SVD)
        print(f"-> [Mô hình 2] Đang phân rã ma trận TruncatedSVD (k={self.n_components})...")
        k_comp = min(self.n_components, n_users - 1, n_jobs - 1)
        self.svd_model = TruncatedSVD(n_components=k_comp, random_state=42)
        self.user_factors = self.svd_model.fit_transform(R_train)  # (n_users, k)
        self.item_factors = self.svd_model.components_.T           # (n_jobs, k)

        var_ratio = float(np.sum(self.svd_model.explained_variance_ratio_)) * 100
        print(f"   Độ biến thiên giải thích được (Explained Variance): {var_ratio:.1f}%")

        # 3. ĐÁNH GIÁ MÔ HÌNH TRÊN TẬP TEST
        print("-> [Đánh giá Offline] Đo lường RMSE và Ranking Metrics trên tập kiểm thử (Test Set)...")
        # Dự đoán ratings tập test: R_hat = U * V^T
        test_u_idx = [self.user_to_idx[uid] for uid in test_df["user_id"]]
        test_j_idx = [self.job_to_idx[jid] for jid in test_df["job_id"]]
        actual_ratings = test_df["rating"].values

        pred_ratings = np.sum(self.user_factors[test_u_idx] * self.item_factors[test_j_idx], axis=1)
        rmse = float(np.sqrt(np.mean((actual_ratings - pred_ratings) ** 2)))

        # Precision@10 và Recall@10
        # Đánh giá xem trong top 10 job dự đoán cao nhất, có bao nhiêu job user thực tế đã tương tác (rating >= 2.0)
        hits = 0
        total_relevant = 0
        test_user_jobs = test_df[test_df["rating"] >= 2.0].groupby("user_id")["job_id"].apply(set).to_dict()

        evaluated_users = 0
        for uid, relevant_jobs in test_user_jobs.items():
            if len(relevant_jobs) == 0:
                continue
            u_idx = self.user_to_idx[uid]
            # Dự đoán cho toàn bộ jobs
            u_preds = self.user_factors[u_idx].dot(self.item_factors.T)
            top10_j_idx = np.argsort(u_preds)[::-1][:10]
            top10_jobs = set([self.idx_to_job[j] for j in top10_j_idx])

            hit_count = len(top10_jobs.intersection(relevant_jobs))
            hits += hit_count
            total_relevant += len(relevant_jobs)
            evaluated_users += 1

        precision_10 = (hits / (evaluated_users * 10)) * 100 if evaluated_users else 0.0
        recall_10 = (hits / total_relevant) * 100 if total_relevant else 0.0

        self.metrics = {
            "n_users": n_users,
            "n_jobs": n_jobs,
            "total_interactions": len(df_interactions),
            "explained_variance_pct": round(var_ratio, 2),
            "test_rmse": round(rmse, 3),
            "precision_at_10_pct": round(precision_10, 2),
            "recall_at_10_pct": round(recall_10, 2)
        }

        print(f"   Ket qua danh gia: RMSE={rmse:.3f} | Precision@10={precision_10:.2f}% | Recall@10={recall_10:.2f}%")
        self.save_model()

    def save_model(self):
        """Lưu trữ ma trận tương đồng Item-to-Item và metadata để phục vụ suy luận nhanh."""
        os.makedirs(MODELS_DIR, exist_ok=True)

        np.savez_compressed(
            os.path.join(MODELS_DIR, "cf_item_similarity.npz"),
            sim_matrix=self.item_sim_matrix,
            user_factors=self.user_factors,
            item_factors=self.item_factors
        )

        mapping_data = {
            "user_to_idx": {str(k): int(v) for k, v in self.user_to_idx.items()},
            "job_to_idx": {str(k): int(v) for k, v in self.job_to_idx.items()},
            "idx_to_job": {int(k): int(v) for k, v in self.idx_to_job.items()},
            "metrics": self.metrics
        }

        with open(os.path.join(MODELS_DIR, "cf_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)

        print(f"-> Da luu tru model Collaborative Filtering thanh cong tai: {MODELS_DIR}")

    def load_model(self):
        """Nạp ma trận đã huấn luyện từ đĩa vào RAM cache."""
        sim_file = os.path.join(MODELS_DIR, "cf_item_similarity.npz")
        meta_file = os.path.join(MODELS_DIR, "cf_metadata.json")

        if not os.path.exists(sim_file) or not os.path.exists(meta_file):
            print("Chưa tìm thấy model CF trên đĩa. Đang tiến hành huấn luyện...")
            self.train()
            return

        data = np.load(sim_file)
        self.item_sim_matrix = data["sim_matrix"]
        self.user_factors = data["user_factors"]
        self.item_factors = data["item_factors"]

        with open(meta_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            self.user_to_idx = {int(k): v for k, v in mapping.get("user_to_idx", {}).items()}
            self.job_to_idx = {int(k): v for k, v in mapping["job_to_idx"].items()}
            self.idx_to_job = {int(k): v for k, v in mapping["idx_to_job"].items()}
            self.metrics = mapping.get("metrics", {})

        self._load_jobs_metadata()
        print(f"-> Nap thanh cong Collaborative Filtering Model ({len(self.job_to_idx)} jobs).")

    def get_similar_jobs(self, job_id: int, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        [People Also Applied]
        Tìm các công việc có độ tương đồng hành vi cao nhất với job_id chỉ định
        dựa trên ma trận Item-to-Item Collaborative Filtering.
        """
        if self.item_sim_matrix is None:
            self.load_model()

        if job_id not in self.job_to_idx:
            # Fallback nếu job mới chưa có tương tác: tìm các job cùng seniority và skill
            return self._fallback_similar_jobs(job_id, top_k)

        j_idx = self.job_to_idx[job_id]
        sim_scores = self.item_sim_matrix[j_idx]

        # Lấy top K jobs có điểm tương đồng cao nhất
        top_indices = np.argsort(sim_scores)[::-1]
        results = []

        for idx in top_indices:
            score = float(sim_scores[idx])
            sim_job_id = self.idx_to_job[idx]
            if sim_job_id == job_id or score <= 0.05:
                continue

            meta = self.jobs_meta.get(sim_job_id)
            if meta:
                item_copy = dict(meta)
                item_copy["similarity_pct"] = round(min(98.5, max(50.0, score * 100)), 1)
                results.append(item_copy)
                if len(results) >= top_k:
                    break

        # Nếu không đủ, bổ sung fallback
        if len(results) < top_k:
            fallback = self._fallback_similar_jobs(job_id, top_k - len(results), exclude_ids=[r["job_id"] for r in results])
            results.extend(fallback)

        return results

    def _fallback_similar_jobs(self, job_id: int, top_k: int, exclude_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        target_job = self.jobs_meta.get(job_id)
        if not target_job:
            return []

        excludes = set(exclude_ids or [])
        excludes.add(job_id)

        target_skills = set(target_job.get("skills", []))
        target_sen = target_job.get("seniority", "")

        candidates = []
        for jid, meta in self.jobs_meta.items():
            if jid in excludes:
                continue
            shared = len(target_skills.intersection(set(meta.get("skills", []))))
            sen_match = 1 if meta.get("seniority") == target_sen else 0
            score = shared * 2 + sen_match
            candidates.append((score, meta))

        candidates.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, m in candidates[:top_k]:
            c = dict(m)
            c["similarity_pct"] = 75.0 + min(20.0, score * 4.0)
            out.append(c)
        return out

    def get_recommendations_for_persona(self, persona_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Gợi ý việc làm theo chân dung ứng viên (Persona) dựa trên hành vi tương tác tập thể."""
        if self.item_factors is None:
            self.load_model()

        users_meta_file = os.path.join(INTERACTIONS_DIR, "users_metadata.json")
        if not os.path.exists(users_meta_file):
            return []

        with open(users_meta_file, "r", encoding="utf-8") as f:
            all_users = json.load(f)

        # Lọc các users thuộc persona này
        persona_uids = [u["user_id"] for u in all_users if u.get("persona_id") == persona_id]
        if not persona_uids:
            return []

        valid_u_indices = [self.user_to_idx[uid] for uid in persona_uids if uid in self.user_to_idx]
        if not valid_u_indices:
            return []

        # Tính vector đại diện trung bình của Persona trong không gian ẩn (Centroid)
        persona_vector = np.mean(self.user_factors[valid_u_indices], axis=0)  # Shape: (k,)

        # Dự đoán điểm cho toàn bộ công việc: S = V_persona * Item_Factors^T
        pred_scores = self.item_factors.dot(persona_vector)

        top_indices = np.argsort(pred_scores)[::-1]
        results = []

        for idx in top_indices:
            job_id = self.idx_to_job[idx]
            meta = self.jobs_meta.get(job_id)
            if meta:
                score = float(pred_scores[idx])
                item_copy = dict(meta)
                # Chuẩn hóa điểm tương thích từ 60% đến 98%
                norm_score = round(min(98.5, max(65.0, 70.0 + score * 5.0)), 1)
                item_copy["match_score"] = norm_score
                results.append(item_copy)
                if len(results) >= top_n:
                    break

        return results

    def get_persona_scores_dict(self, persona_id: str) -> Dict[int, float]:
        """
        Trả về dictionary {job_id: cf_affinity_score} chuẩn hóa theo thang [0.0, 1.0]
        để phục vụ mô hình True Hybrid kết hợp cùng NLP.
        """
        if self.item_factors is None:
            self.load_model()

        users_meta_file = os.path.join(INTERACTIONS_DIR, "users_metadata.json")
        if not os.path.exists(users_meta_file):
            return {}

        with open(users_meta_file, "r", encoding="utf-8") as f:
            all_users = json.load(f)

        persona_uids = [u["user_id"] for u in all_users if u.get("persona_id") == persona_id]
        if not persona_uids:
            return {}

        valid_u_indices = [self.user_to_idx[uid] for uid in persona_uids if uid in self.user_to_idx]
        if not valid_u_indices:
            return {}

        persona_vector = np.mean(self.user_factors[valid_u_indices], axis=0)
        pred_scores = self.item_factors.dot(persona_vector)

        scores_dict = {}
        for idx, score in enumerate(pred_scores):
            jid = self.idx_to_job[idx]
            norm_score = min(0.99, max(0.50, 0.65 + float(score) * 0.05))
            scores_dict[jid] = norm_score
        return scores_dict



def get_cf_recommender() -> CollaborativeRecommender:
    """Singleton getter nạp mô hình trong RAM."""
    global _CACHED_CF
    if _CACHED_CF is None:
        _CACHED_CF = CollaborativeRecommender()
        _CACHED_CF.load_model()
    return _CACHED_CF

if __name__ == "__main__":
    rec = CollaborativeRecommender(n_components=30)
    rec.train()
    print("\n--- Test gợi ý Similar Jobs cho Job #1 ---")
    sims = rec.get_similar_jobs(1, top_k=4)
    for s in sims:
        print(f" -> Job #{s['job_id']}: {s['title']} | Cty: {s['company_name']} | Độ tương quan: {s['similarity_pct']}%")
