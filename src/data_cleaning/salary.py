"""Chuẩn hóa mức lương về VNĐ/THÁNG (đồng bộ với notebook 02, Bước 8)."""
import re
from typing import Any, Optional, Tuple

import pandas as pd

EXCHANGE_RATE_USD = 25400
# Khoảng hợp lý của lương THÁNG: ngoài khoảng này coi là lỗi dữ liệu (nhầm đơn vị, USD chưa quy đổi...) ➔ bỏ
SALARY_MIN_VND = 1_000_000
SALARY_MAX_VND = 300_000_000

_NEGOTIABLE = ['thương lượng', 'cạnh tranh', 'thoa thuan', 'thỏa thuận', 'negotiable', 'deal']
_YEARLY = re.compile(r'/\s*năm|/\s*year|per year|annual|/\s*yr')
# Đơn vị "triệu" phải đi liền sau CON SỐ và đứng riêng: "15tr", "20 triệu", "15-20M" (KHÔNG khớp "MONTH")
_MILLION = re.compile(r'\d\s*(?:tr|triệu|trieu|m)\b')
_VND_MARK = re.compile(r'₫|vnd|đ\b')


def _parse_salary_text(sal_str: Any) -> Tuple[Optional[float], Optional[float]]:
    if sal_str is None or (not isinstance(sal_str, str) and pd.isna(sal_str)) or not str(sal_str).strip():
        return None, None
    s = str(sal_str).strip().lower()
    if any(k in s for k in _NEGOTIABLE):
        return None, None
    nums = [float(n.replace(',', '')) for n in re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?)', s)]
    if not nums:
        return None, None

    million = bool(_MILLION.search(s)) or 'triệu' in s
    usd = ('$' in s or 'usd' in s) and not million
    if usd:
        nums = [n * EXCHANGE_RATE_USD for n in nums]
    elif million:
        nums = [n * 1_000_000 for n in nums]
    elif not _VND_MARK.search(s):
        # Số trần (không ghi đơn vị): <100 ➔ triệu VNĐ ("15 - 20"); 100-20.000 ➔ USD ("500 - 2000", "Lên tới 3000"); còn lại giữ nguyên VNĐ
        if all(n < 100 for n in nums):
            nums = [n * 1_000_000 for n in nums]
        elif all(100 <= n <= 20_000 for n in nums):
            nums = [n * EXCHANGE_RATE_USD for n in nums]

    if _YEARLY.search(s):                      # lương năm ➔ lương tháng
        nums = [n / 12 for n in nums]

    if len(nums) >= 2:
        return min(nums[0], nums[1]), max(nums[0], nums[1])
    val = nums[0]
    if any(k in s for k in ['tới', 'up to', 'dưới', '<', 'tối đa']):
        return None, val
    if any(k in s for k in ['từ', 'trên', '>=', 'tối thiểu', 'from', '>']):
        return val, None
    return val, val


def _salary_from_title(title_str: Any) -> Tuple[Optional[float], Optional[float]]:
    """Khoảng lương ghi ngay trong tiêu đề, vd '... 15 - 20M', '... 15-20 triệu', '... 1000-2000 USD'."""
    if title_str is None or (not isinstance(title_str, str) and pd.isna(title_str)):
        return None, None
    t = str(title_str)
    m = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(m|tr|triệu|usd|\$)(?![a-zà-ỹ])', t, re.I)
    if not m:
        return None, None
    v1, v2, unit = float(m.group(1)), float(m.group(2)), m.group(3).lower()
    mult = EXCHANGE_RATE_USD if unit in ('usd', '$') else 1_000_000
    return min(v1, v2) * mult, max(v1, v2) * mult


def parse_salary_vnd(sal_str: Any, title_str: Any = "") -> Tuple[Optional[float], Optional[float]]:
    """
    Quy đổi lương về VNĐ/tháng ➔ (min, max); None nếu không có hoặc không hợp lý.
    Ưu tiên chuỗi lương gốc; chỉ dùng khoảng lương trong tiêu đề khi chuỗi gốc không có số.
    Hỗ trợ: triệu VNĐ, USD, lương năm (/năm ➔ chia 12), số trần; giá trị ngoài [1 triệu, 300 triệu]/tháng bị loại.
    """
    mn, mx = _parse_salary_text(sal_str)
    if mn is None and mx is None:
        mn, mx = _salary_from_title(title_str)
    ok = lambda v: v is not None and SALARY_MIN_VND <= v <= SALARY_MAX_VND
    return (mn if ok(mn) else None), (mx if ok(mx) else None)
