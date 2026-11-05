"""Chuẩn hóa địa điểm: bỏ dấu tiếng Việt và trích xuất thành phố (không phân biệt có dấu/không dấu)."""
import re
import unicodedata
from typing import Any

import pandas as pd


def strip_accents(text: Any) -> str:
    """Hạ chữ thường và bỏ dấu tiếng Việt (đ -> d)."""
    s = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Thành phố được chọn theo vị trí xuất hiện sớm nhất trong chuỗi địa chỉ
_CITY_PATTERNS = {
    "Hồ Chí Minh": re.compile(
        r"\b(?:ho chi minh|tp\.?\s*hcm|tphcm|hcmc|hcm|sai gon|saigon|thu duc|binh thanh|tan binh|"
        r"phu nhuan|go vap|tan phu|binh tan|nha be|quan\s*\d{1,2}|district\s*\d{1,2})\b"
    ),
    "Hà Nội": re.compile(
        r"\b(?:ha noi|hanoi|hn|cau giay|nam tu liem|bac tu liem|ba dinh|dong da|hai ba trung|"
        r"long bien|ha dong|hoan kiem|tay ho|thanh xuan|me tri|my dinh)\b"
    ),
    "Đà Nẵng": re.compile(r"\b(?:da nang|danang|hai chau|son tra|ngu hanh son|lien chieu|thanh khe)\b"),
}
_NATIONWIDE = re.compile(r"\b(?:toan quoc|remote|viet nam|vietnam)\b")


def extract_city(loc_str: Any) -> str:
    """
    Trả về 'Hồ Chí Minh' | 'Hà Nội' | 'Đà Nẵng' | 'Khác' | 'Toàn quốc'.
    Với địa chỉ nhiều thành phố ("Hà Nội; Hồ Chí Minh") lấy thành phố xuất hiện đầu tiên.
    """
    if loc_str is None or (not isinstance(loc_str, str) and pd.isna(loc_str)) or not str(loc_str).strip():
        return "Toàn quốc"
    s = strip_accents(loc_str)
    best_city, best_pos = None, None
    for city, pat in _CITY_PATTERNS.items():
        m = pat.search(s)
        if m and (best_pos is None or m.start() < best_pos):
            best_city, best_pos = city, m.start()
    if best_city:
        return best_city
    # Chỉ ghi "Remote/Việt Nam/Toàn quốc" mà không có tỉnh thành cụ thể
    if _NATIONWIDE.search(s) and len(s.split()) <= 3:
        return "Toàn quốc"
    return "Khác"
