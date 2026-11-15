"""Gán NHÓM NGHỀ cho tin tuyển dụng theo tiêu đề (Backend, Data/AI, DevOps/Cloud, Game/Đồ họa...).

Từ khóa nằm trong configs/dictionaries/job_domains.yaml. Dùng ở notebook 06 (01_simulation: chia nhóm người dùng mô phỏng).
"""
import re
import unicodedata
from typing import Dict, List

from src.data_cleaning.dictionaries import load_dictionary

_CFG = load_dictionary("job_domains")

NON_TECH_PATTERN: str = "|".join(_CFG["non_tech_keywords"])
DOMAIN_PATTERNS: Dict[str, str] = {d["name"]: "|".join(d["keywords"]) for d in _CFG["domains"]}   # giữ thứ tự ưu tiên
DOMAINS: List[str] = list(DOMAIN_PATTERNS)
OTHER = "Khác"

_NON_TECH_RE = re.compile(NON_TECH_PATTERN)
_DOMAIN_RE = [(name, re.compile(p)) for name, p in DOMAIN_PATTERNS.items()]


def strip_accents(text: str) -> str:
    """Hạ chữ thường và bỏ dấu tiếng Việt (đ ➔ d): 'Hà Nội' ➔ 'ha noi'."""
    s = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def job_domain(title: str) -> str:
    """Nhóm nghề khớp đầu tiên theo thứ tự trong job_domains.yaml; vị trí kinh doanh hoặc không khớp ➔ 'Khác'."""
    t = strip_accents(title)
    if _NON_TECH_RE.search(t):
        return OTHER
    for name, rx in _DOMAIN_RE:
        if rx.search(t):
            return name
    return OTHER
