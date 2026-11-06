"""
Lọc cộng tác (CF) bằng Matrix Factorization cho phản hồi ngầm (ALS, Hu-Koren-Volinsky 2008)
và nhật ký tương tác người dùng của ứng dụng. Đồng bộ với notebook 06 (ALS) và notebook 07 (fold-in).

- InteractionLog: ghi / đọc data/interactions/{events,impressions}.csv (lượt hiển thị, quan tâm, ứng tuyển).
- als_implicit, fold_in: thuật toán, giống hệt notebook.
- CFModel: huấn luyện ALS trên log (tùy chọn thêm dữ liệu mô phỏng của notebook 06 làm nền), chấm điểm tin cho một người dùng.
"""
import csv
import json
import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INTERACTIONS_DIR = os.path.join(PROJECT_ROOT, "data", "interactions")
SIMULATED_DIR = os.path.join(PROJECT_ROOT, "data", "simulated")

# Độ mạnh của tín hiệu (giống notebook 06): bấm xem 1, lưu / quan tâm 3, ứng tuyển 5
EVENT_WEIGHT = {"click": 1.0, "save": 3.0, "apply": 5.0}
# Tham số ALS chọn trên validation ở notebook 06 (in lại ở notebook 07, mục 6)
ALS_PARAMS = {"k": 8, "reg": 0.1, "alpha_conf": 1.0}
SIM_USER_PREFIX = "sim_"


# ==============================================================================
# NHẬT KÝ TƯƠNG TÁC
# ==============================================================================

class InteractionLog:
    """Ghi lượt hiển thị và hành động của người dùng ra CSV (nối thêm, an toàn khi chạy lại ứng dụng)."""

    EVENT_COLS = ["ts", "user_id", "job_id", "event", "position", "source"]
    IMPRESSION_COLS = ["ts", "user_id", "job_id", "position", "source", "mode"]

    def __init__(self, base_dir: str = INTERACTIONS_DIR):
        self.base_dir = base_dir
        self.events_path = os.path.join(base_dir, "events.csv")
        self.impressions_path = os.path.join(base_dir, "impressions.csv")

    def _append(self, path: str, cols: List[str], rows: List[Dict]):
        os.makedirs(self.base_dir, exist_ok=True)
        new_file = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new_file:
                w.writeheader()
            w.writerows(rows)

    def log_event(self, user_id: str, job_id: str, event: str, position: Optional[int] = None, source: str = "") -> None:
        if event not in EVENT_WEIGHT:
            raise ValueError(f"Loại sự kiện không hợp lệ: {event} (chỉ nhận {list(EVENT_WEIGHT)})")
        self._append(self.events_path, self.EVENT_COLS, [{
            "ts": datetime.now().isoformat(timespec="seconds"), "user_id": str(user_id), "job_id": str(job_id),
            "event": event, "position": "" if position is None else int(position), "source": source}])

    def log_impressions(self, user_id: str, job_ids: Iterable[str], source: str = "", mode: str = "") -> None:
        """Lưu các tin đã hiển thị (kèm vị trí): cần để sau này hiệu chỉnh thiên lệch hiển thị khi đánh giá trên log thật."""
        ts = datetime.now().isoformat(timespec="seconds")
        rows = [{"ts": ts, "user_id": str(user_id), "job_id": str(j), "position": i, "source": source, "mode": mode}
                for i, j in enumerate(job_ids)]
        if rows:
            self._append(self.impressions_path, self.IMPRESSION_COLS, rows)

    def load_events(self) -> pd.DataFrame:
        if not os.path.exists(self.events_path):
            return pd.DataFrame(columns=self.EVENT_COLS)
        return pd.read_csv(self.events_path, dtype={"user_id": str, "job_id": str})

    def version(self) -> Tuple[str, float]:
        """Khóa cache: đổi khi có sự kiện mới."""
        p = self.events_path
        return p, (os.path.getmtime(p) if os.path.exists(p) else 0.0)

    def user_job_ids(self, user_id: str) -> List[str]:
        ev = self.load_events()
        return ev.loc[ev["user_id"] == str(user_id), "job_id"].astype(str).unique().tolist()


def load_simulated_events(sim_dir: str = SIMULATED_DIR) -> pd.DataFrame:
    """Tương tác mô phỏng của notebook 06 (người dùng đổi tên thành sim_<id>), dùng làm nền khi chưa có log thật."""
    path = os.path.join(sim_dir, "interactions_alpha0.5.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["user_id", "job_id", "event"])
    sim = pd.read_csv(path, dtype={"job_id": str})
    return pd.DataFrame({"user_id": SIM_USER_PREFIX + sim["user_id"].astype(str), "job_id": sim["job_id"], "event": sim["event"]})


# ==============================================================================
# ALS CHO PHẢN HỒI NGẦM (giống notebook 06 / 07)
# ==============================================================================

def als_implicit(R: sp.csr_matrix, k: int = 8, reg: float = 0.1, alpha_conf: float = 1.0,
                 iters: int = 12, seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """Tối thiểu hóa Σ c_uj (p_uj - x_u·y_j)² + reg(‖x‖² + ‖y‖²), c_uj = 1 + alpha_conf·w_uj. Trả về (X, Y)."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 0.01, (R.shape[0], k))
    Y = rng.normal(0, 0.01, (R.shape[1], k))
    Rt, I = R.T.tocsr(), reg * np.eye(k)

    def update(A, B, M):
        BtB = B.T @ B
        for r in range(M.shape[0]):
            s, e = M.indptr[r], M.indptr[r + 1]
            if s == e:
                A[r] = 0
                continue
            idx, c = M.indices[s:e], 1 + alpha_conf * M.data[s:e]
            Bi = B[idx]
            A[r] = np.linalg.solve(BtB + (Bi.T * (c - 1)) @ Bi + I, Bi.T @ c)

    for _ in range(iters):
        update(X, Y, R)
        update(Y, X, Rt)
    return X, Y


def fold_in(Y: np.ndarray, item_idx: np.ndarray, weights: np.ndarray, reg: float = 0.1, alpha_conf: float = 1.0) -> np.ndarray:
    """Vector cho người dùng CHƯA có trong mô hình, giữ nguyên vector tin Y (một bước cập nhật ALS)."""
    Yi, c = Y[item_idx], 1 + alpha_conf * np.asarray(weights, dtype=float)
    return np.linalg.solve(Y.T @ Y + (Yi.T * (c - 1)) @ Yi + reg * np.eye(Y.shape[1]), Yi.T @ c)


class CFModel:
    """ALS huấn luyện trên log tương tác; cho điểm CF của một người dùng với danh sách tin bất kỳ (NaN = tin CF không biết)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = dict(ALS_PARAMS, **(params or {}))
        self.user_index: Dict[str, int] = {}
        self.item_index: Dict[str, int] = {}
        self.X: Optional[np.ndarray] = None
        self.Y: Optional[np.ndarray] = None
        self.n_events = 0

    @staticmethod
    def _matrix(events: pd.DataFrame) -> Tuple[sp.csr_matrix, Dict[str, int], Dict[str, int]]:
        ev = events.assign(weight=events["event"].map(EVENT_WEIGHT)).dropna(subset=["weight"])
        ev = ev.groupby(["user_id", "job_id"], as_index=False)["weight"].max()          # giữ hành động mạnh nhất
        users = {u: i for i, u in enumerate(ev["user_id"].astype(str).unique())}
        items = {j: i for i, j in enumerate(ev["job_id"].astype(str).unique())}
        R = sp.csr_matrix((ev["weight"].values.astype(np.float32),
                           (ev["user_id"].astype(str).map(users).values, ev["job_id"].astype(str).map(items).values)),
                          shape=(len(users), len(items)))
        return R, users, items

    def fit(self, events: pd.DataFrame) -> "CFModel":
        self.n_events = len(events)
        if events.empty:
            return self
        R, self.user_index, self.item_index = self._matrix(events)
        self.X, self.Y = als_implicit(R, **self.params)
        return self

    @property
    def ready(self) -> bool:
        return self.Y is not None and len(self.item_index) > 0

    def user_vector(self, user_id: str, user_events: Optional[pd.DataFrame] = None) -> Optional[np.ndarray]:
        """Vector người dùng: lấy từ mô hình nếu đã học, nếu chưa thì fold-in từ user_events (không cần huấn luyện lại)."""
        if not self.ready:
            return None
        if str(user_id) in self.user_index:
            return self.X[self.user_index[str(user_id)]]
        if user_events is None or user_events.empty:
            return None
        ev = user_events.assign(weight=user_events["event"].map(EVENT_WEIGHT)).dropna(subset=["weight"])
        ev = ev[ev["job_id"].astype(str).isin(self.item_index)].groupby("job_id")["weight"].max()
        if ev.empty:
            return None
        idx = np.array([self.item_index[str(j)] for j in ev.index])
        return fold_in(self.Y, idx, ev.values, self.params["reg"], self.params["alpha_conf"])

    def score(self, user_vec: np.ndarray, job_ids: Iterable[str]) -> np.ndarray:
        """Điểm ALS x_u·y_j cho từng tin; NaN với tin chưa có tương tác (CF không biết: tin mới)."""
        job_ids = [str(j) for j in job_ids]
        out = np.full(len(job_ids), np.nan)
        known = np.array([j in self.item_index for j in job_ids])
        if known.any():
            idx = np.array([self.item_index[j] for j, k in zip(job_ids, known) if k])
            out[known] = self.Y[idx] @ user_vec
        return out


def build_training_events(log: InteractionLog, use_simulated: bool = False) -> pd.DataFrame:
    """Log thật của ứng dụng (+ dữ liệu mô phỏng làm nền nếu bật chế độ demo)."""
    real = log.load_events()[["user_id", "job_id", "event"]]
    if not use_simulated:
        return real.reset_index(drop=True)
    return pd.concat([load_simulated_events(), real], ignore_index=True)


def simulated_data_available(sim_dir: str = SIMULATED_DIR) -> bool:
    return os.path.exists(os.path.join(sim_dir, "interactions_alpha0.5.csv"))


def simulated_snapshot(sim_dir: str = SIMULATED_DIR) -> Optional[str]:
    try:
        with open(os.path.join(sim_dir, "config.json"), encoding="utf-8") as f:
            return json.load(f).get("snapshot")
    except Exception:
        return None
