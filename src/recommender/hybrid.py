"""
Hybrid CBF + CF cho ứng dụng (đồng bộ với notebook 07).

Xếp hạng = W_CBF · z(CBF) + (1 - W_CBF) · z(CF), chuẩn hóa z-score trên các tin còn hạn của từng lượt gợi ý.
- Tin CF chưa biết (chưa ai tương tác: tin mới) chỉ dùng z(CBF), theo quy tắc "thiếu dữ liệu thì bỏ thành phần".
- Người dùng có ít hơn MIN_USER_INTERACTIONS tin đã tương tác, hoặc chưa có dữ liệu CF ➔ CBF thuần (như notebook 05).
- Notebook 07 chọn công thức z-score thay cho trộn tuyến tính vì nó tốt hơn theo sở thích thật (Oracle-P@10) mà
  không làm chìm tin mới; NDCG theo log lại ưu ái trộn tuyến tính do log thiên vị hệ đang hiển thị tin.
Hiển thị: "Tổng điểm (%)" vẫn là điểm CBF (độ phù hợp nội dung), thêm "Điểm CF (%)" (thứ hạng phần trăm theo hành vi),
danh sách được xếp theo Hybrid.
"""
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from src.recommender.collaborative import CFModel, InteractionLog, build_training_events
from src.recommender.content_based import ContentBasedRecommender

W_CBF = 0.5                   # notebook 07, mục 3 (chọn trên validation theo Oracle-P@10)
MIN_USER_INTERACTIONS = 1     # notebook 07, mục 4
CF_HIGHLIGHT_PCT = 80.0       # điểm CF từ mức này thì lời giải thích nhắc tới hành vi của người dùng tương tự


def _z(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(len(values))
    if mask.sum() > 1:
        v = values[mask]
        out[mask] = (v - v.mean()) / (v.std() + 1e-9)
    return out


def hybrid_scores(cbf_total: np.ndarray, cf_raw: np.ndarray, active: np.ndarray, w_cbf: float = W_CBF) -> np.ndarray:
    """Điểm xếp hạng Hybrid cho mọi tin; tin hết hạn = -inf; tin CF chưa biết (NaN) chỉ dùng z(CBF)."""
    active = np.asarray(active, dtype=bool)
    known = active & ~np.isnan(cf_raw)
    zc, za = _z(cbf_total, active), _z(np.nan_to_num(cf_raw), known)
    out = np.where(known, w_cbf * zc + (1 - w_cbf) * za, zc)
    return np.where(active, out, -np.inf)


def cf_percentile(cf_raw: np.ndarray, active: np.ndarray) -> np.ndarray:
    """Điểm CF dễ đọc: thứ hạng phần trăm (0-100) trong các tin còn hạn mà CF biết; NaN = CF không biết tin này."""
    out = np.full(len(cf_raw), np.nan)
    known = np.asarray(active, dtype=bool) & ~np.isnan(cf_raw)
    if known.any():
        out[known] = np.round(rankdata(cf_raw[known]) / known.sum() * 100, 1)
    return out


class HybridRecommender:
    """Bọc ContentBasedRecommender: thêm CF (ALS) khi người dùng đã có hành vi, ghi log hiển thị / hành động."""

    def __init__(self, cbf: ContentBasedRecommender, log: Optional[InteractionLog] = None,
                 use_simulated: bool = False, cf_model: Optional[CFModel] = None):
        self.cbf = cbf
        self.log = log or InteractionLog()
        self.use_simulated = use_simulated
        self.cf = cf_model if cf_model is not None else CFModel().fit(build_training_events(self.log, use_simulated))

    def user_events(self, user_id: str) -> pd.DataFrame:
        ev = self.log.load_events()
        return ev[ev["user_id"].astype(str) == str(user_id)]

    def recommend(self, user_id: str, top_n: int = 10, exclude_seen: bool = True,
                  **profile: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        profile: tham số hồ sơ như ContentBasedRecommender.recommend (target_title, cv_text, skills, user_exp,
        preferred_city, preferred_work_modes, min_salary). Trả về (bảng kết quả, thông tin chế độ đã dùng).
        """
        scored = self.cbf.score_all(**profile)
        if scored is None:
            return pd.DataFrame(), {"mode": "CBF", "n_interactions": 0, "reason": "Hồ sơ trống."}
        sc, total = scored
        job_ids = self.cbf.jobs_df["job_id"].astype(str).values
        ev = self.user_events(user_id)
        seen = set(ev["job_id"].astype(str))
        info: Dict[str, Any] = {"mode": "CBF", "n_interactions": len(seen), "w_cbf": W_CBF,
                                "cf_users": len(self.cf.user_index), "cf_items": len(self.cf.item_index)}

        rank, extra = total.astype(float).copy(), {}
        if len(seen) < MIN_USER_INTERACTIONS:
            info["reason"] = "Bạn chưa có tương tác nào: bấm 'Quan tâm' hoặc 'Ứng tuyển' để hệ thống học sở thích của bạn."
        elif not self.cf.ready:
            info["reason"] = "Chưa đủ dữ liệu tương tác để huấn luyện CF."
        else:
            vec = self.cf.user_vector(user_id, ev)
            if vec is None:
                info["reason"] = "Các tin bạn đã tương tác chưa có trong dữ liệu CF."
            else:
                cf_raw = self.cf.score(vec, job_ids)
                rank = hybrid_scores(total, cf_raw, sc["active"])
                extra["Điểm CF (%)"] = cf_percentile(cf_raw, sc["active"])
                info.update(mode="Hybrid", reason=f"Kết hợp nội dung hồ sơ ({W_CBF:.0%}) và hành vi của người dùng "
                                                  f"tương tự ({1 - W_CBF:.0%}), dựa trên {len(seen)} tin bạn đã tương tác.")

        rank = np.where(sc["active"], rank, -np.inf)
        if exclude_seen and seen:
            rank = np.where(np.isin(job_ids, list(seen)), -np.inf, rank)    # không gợi ý lại tin đã quan tâm / ứng tuyển
        order = [i for i in np.argsort(-rank, kind="stable")[:top_n] if np.isfinite(rank[i])]
        df = self.cbf.format_results(sc, total, order, profile.get("user_exp", 1.0), extra)

        if "Điểm CF (%)" in df.columns:   # nói rõ trong lời giải thích khi CF đóng góp mạnh
            hot = df["Điểm CF (%)"].fillna(0) >= CF_HIGHLIGHT_PCT
            df.loc[hot, "Lời giải thích"] = df.loc[hot, "Lời giải thích"] + "; Người dùng có hành vi giống bạn quan tâm tin này"
        df.insert(0, "Hạng", range(1, len(df) + 1))
        return df, info
