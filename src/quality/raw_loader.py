"""Đọc dữ liệu thô (data/raw/<source>/{listings,details}/<ngày>/*.json) để kiểm định và nạp Bronze."""
import json
import os
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_SOURCES = ["topcv", "topdev", "vietnamworks"]


def _load_raw(source: str, kind: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Đọc tất cả các file JSON trong data/raw/{source}/{kind}/[target_date]/ (kind = listings | details).
    Gắn thêm metadata: raw_file_name và raw_date.
    """
    records: List[Dict[str, Any]] = []
    root = os.path.join(PROJECT_ROOT, "data", "raw", source, kind)
    if not os.path.exists(root):
        return records

    date_folders = [target_date] if target_date else sorted(os.listdir(root))

    for date_folder in date_folders:
        folder_path = os.path.join(root, date_folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path)):
            if fname.endswith(".json"):
                fpath = os.path.join(folder_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                item["raw_file_name"] = fname
                                item["raw_date"] = date_folder
                                records.append(item)
                except Exception as e:
                    print(f"[CANH BAO] Không thể đọc {kind[:-1]} file {fpath}: {e}")
    return records


def load_raw_listings(source: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Đọc các file listing JSON trong data/raw/{source}/listings/[target_date]/."""
    return _load_raw(source, "listings", target_date)


def load_raw_details(source: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Đọc các file detail JSON trong data/raw/{source}/details/[target_date]/."""
    return _load_raw(source, "details", target_date)


def get_latest_date() -> Optional[str]:
    """Tìm ngày mới nhất có dữ liệu trong data/raw/."""
    found_dates = set()
    for s in RAW_SOURCES:
        for sub in ["details", "listings"]:
            d_path = os.path.join(PROJECT_ROOT, "data", "raw", s, sub)
            if os.path.exists(d_path):
                for d in os.listdir(d_path):
                    if os.path.isdir(os.path.join(d_path, d)):
                        found_dates.add(d)
    return max(found_dates) if found_dates else None
