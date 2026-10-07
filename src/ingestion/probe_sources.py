"""Task 03 - Probe 2 nguồn dữ liệu để xem dữ liệu THỰC TẾ.

Chỉ đọc và in báo cáo. KHÔNG ghi vào data/raw (raw dành cho ingestion thật ở Task 04).
Mẫu dữ liệu được lưu ở data/_probe/.

Chạy:
    python -m src.ingestion.probe_sources --source all
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.config import get_settings
from src.utils.logging_utils import get_logger, setup_logging

logger = get_logger(__name__)

# Heuristic CHỈ để ước lượng tỷ lệ job IT trong probe, không dùng cho ETL thật.
IT_TITLE_KEYWORDS = (
    "developer", "engineer", "software", "devops", "backend", "frontend",
    "full stack", "fullstack", "data", "python", "java", "machine learning",
    "cloud", "sre", "qa ", "security",
)
# Từ khóa để đoán nhóm ngành IT trong VietJobs (chỉ để gợi ý, bạn tự xác nhận).
VIET_IT_HINTS = ("công_nghệ", "cong_nghe", "thông_tin", "phần_mềm", "cntt")


def _out_dir() -> Path:
    path = get_settings().project_root / "data" / "_probe"
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------- #
# source_02: Arbeitnow
# --------------------------------------------------------------------------- #
def _fetch_arbeitnow_page(url: str, page: int, headers: dict, timeout: int) -> requests.Response:
    resp = requests.get(url, params={"page": page}, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def probe_arbeitnow() -> None:
    settings = get_settings()
    cfg = settings.config["sources"]["source_02_arbeitnow"]
    ing = settings.config["ingestion"]
    headers = {"User-Agent": ing["user_agent"]}
    timeout = int(ing["timeout_seconds"])
    delay = 1.0 / float(ing["rate_limit_per_second"])

    logger.info("===== PROBE source_02 (Arbeitnow) =====")
    r1 = _fetch_arbeitnow_page(cfg["base_url"], 1, headers, timeout)
    p1: dict[str, Any] = r1.json()

    logger.info("HTTP %s | content-type=%s", r1.status_code, r1.headers.get("content-type"))
    logger.info("Top-level keys: %s", list(p1.keys()))
    logger.info("links = %s", p1.get("links"))
    logger.info("meta  = %s", p1.get("meta"))
    rl = {k: v for k, v in r1.headers.items()
          if k.lower().startswith("x-ratelimit") or k.lower() == "retry-after"}
    logger.info("Rate-limit headers: %s", rl or "(none)")

    jobs: list[dict[str, Any]] = p1.get("data", [])
    logger.info("Page 1: %d jobs", len(jobs))
    if not jobs:
        logger.warning("Page 1 has no jobs - check the API response manually")
        return
    logger.info("Job keys: %s", sorted(jobs[0].keys()))

    # Kiểm tra pagination: trang 2 có khác trang 1 không?
    time.sleep(delay)
    r2 = _fetch_arbeitnow_page(cfg["base_url"], 2, headers, timeout)
    jobs2 = r2.json().get("data", [])
    overlap = {j["slug"] for j in jobs} & {j["slug"] for j in jobs2}
    logger.info("Page 2: %d jobs | overlap with page 1: %d slugs", len(jobs2), len(overlap))

    # Thống kê nhanh trên trang 1
    ts = [j["created_at"] for j in jobs if j.get("created_at")]
    if ts:
        lo = datetime.fromtimestamp(min(ts), tz=timezone.utc)
        hi = datetime.fromtimestamp(max(ts), tz=timezone.utc)
        logger.info("created_at range (UTC): %s -> %s", lo, hi)

    remote_share = sum(bool(j.get("remote")) for j in jobs) / len(jobs)
    escaped_share = sum("&lt;" in (j.get("description") or "") for j in jobs) / len(jobs)
    money_share = sum(
        any(s in (j.get("description") or "") for s in ("€", "EUR", "$", "£", "GBP"))
        for j in jobs
    ) / len(jobs)
    it_like = sum(
        any(k in (j.get("title") or "").lower() for k in IT_TITLE_KEYWORDS) for j in jobs
    )
    tags = Counter(t for j in jobs for t in j.get("tags", []))

    logger.info("remote=true share            : %.1f%%", 100 * remote_share)
    logger.info("description double-escaped   : %.1f%%", 100 * escaped_share)
    logger.info("description mentions currency: %.1f%% (salary-in-text)", 100 * money_share)
    logger.info("title looks IT (heuristic)   : %d / %d", it_like, len(jobs))
    logger.info("Top tags (NOTE: categories, not skills): %s", tags.most_common(8))

    out = _out_dir() / "arbeitnow_page1.json"
    out.write_text(json.dumps(p1, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved sample -> %s", out)


# --------------------------------------------------------------------------- #
# source_01: VietJobs (Hugging Face)
# --------------------------------------------------------------------------- #
def _load_vietjobs(repo_id: str) -> pd.DataFrame:
    from huggingface_hub import hf_hub_download, list_repo_files

    files = list_repo_files(repo_id, repo_type="dataset")
    logger.info("Files in repo: %s", files)
    csvs = [f for f in files if f.lower().endswith(".csv")]
    parquets = [f for f in files if f.lower().endswith(".parquet")]

    if csvs:
        path = hf_hub_download(repo_id, csvs[0], repo_type="dataset")
        logger.info("Loading CSV: %s", csvs[0])
        return pd.read_csv(path)
    if parquets:
        path = hf_hub_download(repo_id, parquets[0], repo_type="dataset")
        logger.info("Loading Parquet: %s", parquets[0])
        return pd.read_parquet(path)
    raise FileNotFoundError(f"No CSV/Parquet file found in dataset repo {repo_id}")


def probe_vietjobs() -> None:
    cfg = get_settings().config["sources"]["source_01_vietjobs"]
    logger.info("===== PROBE source_01 (VietJobs) =====")
    df = _load_vietjobs(cfg["hf_repo_id"])

    logger.info("Shape: %s rows x %s cols", *df.shape)
    logger.info("Columns: %s", list(df.columns))

    null_share = (df.isna().mean() * 100).round(1).sort_values(ascending=False)
    logger.info("Null %% per column (top 8):\n%s", null_share.head(8).to_string())

    if "country" in df.columns:
        logger.info("Country counts:\n%s", df["country"].value_counts().head(5).to_string())

    cats = df["category"].value_counts() if "category" in df.columns else pd.Series(dtype=int)
    logger.info("Categories (%d):\n%s", len(cats), cats.to_string())
    it_candidates = [c for c in cats.index if any(h in str(c).lower() for h in VIET_IT_HINTS)]
    logger.info("IT category CANDIDATES (please confirm by eye): %s", it_candidates)

    if {"salary_min", "salary_max"} <= set(df.columns):
        zero = ((df["salary_min"] == 0) & (df["salary_max"] == 0)).mean()
        logger.info("salary_min=max=0 (negotiable/missing): %.1f%%", 100 * zero)

    dup_cols = [c for c in ("job_title", "location", "description") if c in df.columns]
    dup_share = df.duplicated(subset=dup_cols).mean()
    logger.info("Exact duplicates on %s: %.1f%%", dup_cols, 100 * dup_share)

    if "technical_skills" in df.columns:
        sample_skills = df["technical_skills"].dropna().head(3).tolist()
        logger.info("technical_skills raw samples (type=%s): %s",
                    type(sample_skills[0]).__name__ if sample_skills else "n/a", sample_skills)

    subset = df[df["category"].isin(it_candidates)] if it_candidates else df
    if it_candidates:
        logger.info("IT-candidate rows: %d", len(subset))
    sample = subset.sample(n=min(200, len(subset)), random_state=42)
    out = _out_dir() / "vietjobs_sample.csv"
    sample.to_csv(out, index=False, encoding="utf-8-sig")
    logger.info("Saved sample -> %s", out)


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Probe candidate data sources")
    parser.add_argument("--source", choices=["vietjobs", "arbeitnow", "all"], default="all")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level, settings.path("logs") / "pipeline.log")

    tasks = {
        "vietjobs": probe_vietjobs,
        "arbeitnow": probe_arbeitnow,
    }
    selected = tasks if args.source == "all" else {args.source: tasks[args.source]}

    failed = 0
    for name, fn in selected.items():
        try:
            fn()
        except Exception:  # noqa: BLE001 - probe phải báo lỗi rõ rồi đi tiếp
            logger.exception("Probe '%s' FAILED", name)
            failed += 1
    logger.info("Probe finished | failed=%d", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())