"""Khử trùng lặp tin tuyển dụng: khớp chính xác + khớp gần đúng (biến thể tên công ty, mô tả giống nhau)."""
import re
from typing import Dict, Tuple

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from src.data_cleaning.location import strip_accents

_LEGAL_TOKENS = {
    "cong", "ty", "cty", "tnhh", "mtv", "co", "phan", "cp", "jsc", "llc", "inc", "corp", "ltd",
    "company", "limited", "joint", "stock", "group", "tap", "doan", "ngan", "hang", "tmcp",
    "chi", "nhanh", "vietnam", "viet", "nam", "the", "and", "va", "mot", "thanh", "vien",
}


def company_tokens(name: str) -> frozenset:
    """Tập token đặc trưng của tên công ty (bỏ dấu, bỏ từ pháp lý/chung chung)."""
    toks = re.findall(r"[a-z0-9]+", strip_accents(name))
    core = [t for t in toks if t not in _LEGAL_TOKENS]
    return frozenset(core or toks)


def company_key(name: str) -> str:
    return " ".join(sorted(company_tokens(name)))


def companies_compatible(a: frozenset, b: frozenset) -> bool:
    """Cùng một công ty nếu token tên này nằm trọn trong tên kia (MBBANK ⊂ Quân Đội MBBANK)."""
    return bool(a) and bool(b) and (a <= b or b <= a)


def title_key(title: str) -> str:
    """Tiêu đề chuẩn hóa: bỏ dấu, bỏ mã tin trong ngoặc và ký tự không phải chữ-số."""
    t = strip_accents(title)
    t = re.sub(r"\([^)]*\d[^)]*\)", " ", t)  # (2025td943), (ma tin 123)
    return " ".join(re.findall(r"[a-z0-9+#.]+", t))


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


class _UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def deduplicate_jobs(
    jobs: pd.DataFrame,
    title_block_sim: float = 0.80,
    company_block_sim: float = 0.92,
    title_jaccard: float = 0.85,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Khử trùng lặp 3 lớp:
      1. Cùng (khóa công ty, khóa tiêu đề)                                   -> trùng chính xác
      2. Cùng tiêu đề + công ty tương thích + mô tả giống >= title_block_sim -> biến thể tên công ty
      3. Cùng công ty + mô tả giống >= company_block_sim                     -> đổi tiêu đề nhẹ
    Giữ bản có hạn nộp xa nhất, mô tả dài nhất. Trả về (df đã khử, báo cáo các bản bị loại).
    """
    df = jobs.reset_index(drop=True).copy()
    n = len(df)
    df["_ck"] = df["company_name"].map(company_key)
    df["_ct"] = df["company_name"].map(company_tokens)
    df["_tk"] = df["title"].map(title_key)
    desc = df["description_clean"].fillna("").astype(str)
    df["_len"] = desc.str.len()

    X = TfidfVectorizer(sublinear_tf=True).fit_transform(desc)
    uf = _UnionFind(n)
    reason: Dict[int, str] = {}

    def link(i: int, j: int, why: str):
        uf.union(i, j)
        reason.setdefault(i, why)
        reason.setdefault(j, why)

    # Lớp 1: trùng chính xác
    for _, idx in df.groupby(["_ck", "_tk"]).indices.items():
        for j in idx[1:]:
            link(idx[0], j, "exact")

    # Lớp 2: cùng tiêu đề, công ty tương thích, mô tả giống
    for tk, idx in df.groupby("_tk").indices.items():
        if len(idx) < 2 or len(tk) < 3:
            continue
        sim = linear_kernel(X[idx])
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                if sim[a, b] >= title_block_sim and companies_compatible(df.at[i, "_ct"], df.at[j, "_ct"]):
                    link(i, j, "company_name_variant")

    # Lớp 3: cùng công ty, mô tả gần như y hệt VÀ tiêu đề giống, cùng thành phố, cùng yêu cầu kinh nghiệm.
    # (Chỉ so mô tả là không đủ: nhiều tin cùng công ty chia sẻ phần giới thiệu/phúc lợi giống hệt nhau.)
    city = df["city"] if "city" in df.columns else pd.Series([""] * n)
    exp = df["experience_min"] if "experience_min" in df.columns else pd.Series([0.0] * n)
    for _, idx in df.groupby("_ck").indices.items():
        if len(idx) < 2:
            continue
        sim = linear_kernel(X[idx])
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                if (sim[a, b] >= company_block_sim
                        and _jaccard(df.at[i, "_tk"], df.at[j, "_tk"]) >= title_jaccard
                        and city[i] == city[j]
                        and (exp[i] == exp[j] or (pd.isna(exp[i]) and pd.isna(exp[j])))):
                    link(i, j, "same_description")

    df["_grp"] = [uf.find(i) for i in range(n)]
    df["_deadline"] = df["deadline"].fillna("") if "deadline" in df.columns else ""
    ordered = df.sort_values(by=["_grp", "_deadline", "_len"], ascending=[True, False, False])
    kept = ordered.drop_duplicates("_grp", keep="first")
    dropped = df.loc[~df.index.isin(kept.index)].copy()
    rep = kept.set_index("_grp")
    dropped["kept_job_id"] = dropped["_grp"].map(rep["job_id"])
    dropped["kept_company"] = dropped["_grp"].map(rep["company_name"])
    dropped["reason"] = [reason.get(i, "duplicate") for i in dropped.index]
    report = dropped[["job_id", "company_name", "title", "kept_job_id", "kept_company", "reason"]].reset_index(drop=True)

    result = df.loc[kept.sort_index().index].drop(columns=[c for c in df.columns if c.startswith("_")])
    return result.reset_index(drop=True), report
