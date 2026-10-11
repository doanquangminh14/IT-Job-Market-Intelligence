"""
Module định nghĩa các quy tắc kiểm tra chất lượng dữ liệu (Data Quality Rules).
Bao gồm bộ tiêu chí toàn diện cho cả 3 luồng:
1. INVALID (Dữ liệu rác / hỏng nặng / thiếu trường cốt lõi)
2. QUARANTINE (Khu cách ly - Dữ liệu đầy đủ nhưng mâu thuẫn logic lương, ngày tháng)
3. VALID (Dữ liệu đạt chuẩn chất lượng 100%)
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# --- 1. MÃ LỖI LUỒNG INVALID (DỮ LIỆU RÁC / LỖI NẶNG) ---
ERR_MISSING_JOB_URL = "ERR_MISSING_JOB_URL"
ERR_MISSING_TITLE = "ERR_MISSING_TITLE"
ERR_MISSING_SOURCE = "ERR_MISSING_SOURCE"
ERR_MISSING_JOB_ID = "ERR_MISSING_JOB_ID"
ERR_CONTENT_TOO_SHORT = "ERR_CONTENT_TOO_SHORT"

# --- 2. MÃ LỖI LUỒNG QUARANTINE (BẤT THƯỜNG LOGIC NGHIỆP VỤ) ---
ERR_SALARY_INVERTED = "ERR_SALARY_INVERTED"                     # Min > Max
ERR_SALARY_NEGATIVE = "ERR_SALARY_NEGATIVE"                     # Chứa số âm
ERR_SALARY_OUTLIER = "ERR_SALARY_OUTLIER"                       # Lương dị thường (> 1 tỷ VND hoặc > $50,000)
ERR_DATE_DEADLINE_BEFORE_PUBLISHED = "ERR_DATE_DEADLINE_BEFORE_PUBLISHED" # Deadline trước ngày đăng
ERR_DATE_FAR_PAST = "ERR_DATE_FAR_PAST"                         # Năm quá xa trong quá khứ (< 2020)
ERR_DATE_MALFORMED = "ERR_DATE_MALFORMED"                       # Ngày tháng sai định dạng không parse được

SUPPORTED_SOURCES = {"topcv", "topdev", "vietnamworks"}
MIN_JOB_CONTENT_LENGTH = 100


# ==============================================================================
# A. CÁC QUY TẮC KIỂM TRA LUỒNG INVALID (CỐT LÕI)
# ==============================================================================

def check_identity_and_url(record: Dict[str, Any]) -> List[str]:
    """Kiểm tra mã định danh và URL tin tuyển dụng."""
    errors: List[str] = []

    source_job_id = str(record.get("source_job_id", "") or "").strip()
    detail_id = str(record.get("detail_id", "") or "").strip()
    if not source_job_id and not detail_id:
        errors.append(ERR_MISSING_JOB_ID)

    job_url = str(record.get("job_url", "") or "").strip()
    if not job_url:
        errors.append(ERR_MISSING_JOB_URL)
    else:
        try:
            parsed = urlparse(job_url)
            if not parsed.scheme or parsed.scheme not in ("http", "https") or not parsed.netloc:
                errors.append(ERR_MISSING_JOB_URL)
        except Exception:
            errors.append(ERR_MISSING_JOB_URL)

    return errors


def check_core_info(record: Dict[str, Any]) -> List[str]:
    """Kiểm tra tiêu đề và nguồn tuyển dụng."""
    errors: List[str] = []

    title = str(record.get("title_raw", "") or "").strip()
    if len(title) < 2:
        errors.append(ERR_MISSING_TITLE)

    source = str(record.get("source", "") or "").strip().lower()
    if not source or source not in SUPPORTED_SOURCES:
        errors.append(ERR_MISSING_SOURCE)

    return errors


def check_content_length(record: Dict[str, Any], min_length: int = MIN_JOB_CONTENT_LENGTH) -> List[str]:
    """Kiểm tra tổng độ dài nội dung mô tả (chống bot block/captcha/trang rỗng)."""
    errors: List[str] = []

    overview = str(record.get("overview_raw", "") or "").strip()
    responsibilities = str(record.get("responsibilities_raw", "") or "").strip()
    requirements = str(record.get("requirements_raw", "") or "").strip()
    benefits = str(record.get("benefits_raw", "") or "").strip()

    total_content = f"{overview} {responsibilities} {requirements} {benefits}".strip()
    if len(total_content) < min_length:
        errors.append(ERR_CONTENT_TOO_SHORT)

    return errors


def evaluate_invalid_rules(record: Dict[str, Any], min_content_length: int = MIN_JOB_CONTENT_LENGTH) -> List[str]:
    """Kiểm tra toàn bộ các lỗi thuộc nhóm INVALID."""
    errors: List[str] = []
    errors.extend(check_identity_and_url(record))
    errors.extend(check_core_info(record))
    errors.extend(check_content_length(record, min_length=min_content_length))
    return errors


# ==============================================================================
# B. CÁC QUY TẮC KIỂM TRA LUỒNG QUARANTINE (LOGIC LƯƠNG & NGÀY THÁNG)
# ==============================================================================

def _parse_salary_numbers(salary_str: str) -> Optional[Tuple[float, float, str]]:
    """
    Trích xuất min_val, max_val và đơn vị (vnd/usd/trieu) từ chuỗi lương thô.
    Hỗ trợ các mẫu:
    - '25 - 40 triệu', '40 - 25 triệu'
    - '$ 1,202-2,600 /tháng', '1000 - 2000 USD'
    - '30,000,000 - 45,000,000 VND'
    """
    sal_lower = salary_str.lower().strip()
    if not sal_lower:
        return None

    # Bỏ qua các chuỗi thỏa thuận
    if any(w in sal_lower for w in ["thỏa thuận", "thoả thuận", "thương lượng", "negotiable", "cạnh tranh"]):
        return None

    # Tìm các khoảng có dấu '-' giữa 2 số
    # Chuẩn hóa dấu phẩy và chấm ngăn cách hàng nghìn
    clean_str = sal_lower.replace(",", "")

    # Tìm dạng range: number - number
    match_range = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:-|đến|to)\s*(-?\d+(?:\.\d+)?)", clean_str)
    if match_range:
        try:
            val1 = float(match_range.group(1))
            val2 = float(match_range.group(2))

            # Suy luận đơn vị thông minh:
            # 1. Nếu giá trị >= 500,000 (ví dụ 14,000,000) -> chắc chắn là VND
            if max(abs(val1), abs(val2)) >= 500_000:
                unit = "vnd"
            elif any(u in sal_lower for u in ["$", "usd", "đô"]):
                unit = "usd"
            elif "triệu" in sal_lower or re.search(r"\b(?:tr|m)\b", sal_lower) or re.search(r"\d+\s*(?:tr|m)\b", sal_lower):
                unit = "trieu"
            elif any(u in sal_lower for u in ["vnd", "vnđ", "đồng"]):
                unit = "vnd"
            else:
                unit = "unknown"

            return val1, val2, unit
        except ValueError:
            pass

    return None


def check_salary_sanity(record: Dict[str, Any]) -> List[str]:
    """
    Kiểm tra tính hợp lý của lương:
    - Min > Max -> ERR_SALARY_INVERTED
    - Số âm -> ERR_SALARY_NEGATIVE
    - Quá lớn dị thường (> 1 tỷ VND / > $50,000 USD) -> ERR_SALARY_OUTLIER
    """
    errors: List[str] = []
    sal_raw = str(record.get("salary_raw", "") or "").strip()
    if not sal_raw:
        return errors

    parsed = _parse_salary_numbers(sal_raw)
    if not parsed:
        return errors

    val1, val2, unit = parsed

    # 1. Số âm
    if val1 < 0 or val2 < 0:
        errors.append(ERR_SALARY_NEGATIVE)

    # 2. Min > Max (Inverted)
    if val1 > val2:
        errors.append(ERR_SALARY_INVERTED)

    # 3. Outlier kiểm tra mức tối đa phi thực tế
    max_val = max(val1, val2)
    if unit == "usd" and max_val > 50000:
        errors.append(ERR_SALARY_OUTLIER)
    elif unit == "trieu" and max_val > 1000:  # > 1 tỷ VND
        errors.append(ERR_SALARY_OUTLIER)
    elif unit == "vnd" and max_val > 1_000_000_000:
        errors.append(ERR_SALARY_OUTLIER)

    return errors


def _parse_iso_or_date(date_str: str) -> Optional[datetime]:
    """Parse chuỗi ngày tháng theo các định dạng phổ biến."""
    if not date_str:
        return None
    d_clean = date_str.strip()
    # Thử ISO format
    try:
        return datetime.fromisoformat(d_clean)
    except Exception:
        pass

    # Thử YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d_clean[:10], fmt)
        except Exception:
            pass
    return None


def check_date_sanity(record: Dict[str, Any]) -> List[str]:
    """
    Kiểm tra tính hợp lý của ngày đăng và hạn nộp:
    - Deadline trước ngày đăng -> ERR_DATE_DEADLINE_BEFORE_PUBLISHED
    - Năm quá xa trong quá khứ (< 2020) -> ERR_DATE_FAR_PAST
    - Có chuỗi ngày nhưng không parse được -> ERR_DATE_MALFORMED
    """
    errors: List[str] = []

    pub_raw = str(record.get("published_at_raw", "") or "").strip()
    dl_raw = str(record.get("deadline_raw", "") or "").strip()

    dt_pub: Optional[datetime] = None
    dt_dl: Optional[datetime] = None

    if pub_raw:
        dt_pub = _parse_iso_or_date(pub_raw)
        if not dt_pub:
            errors.append(ERR_DATE_MALFORMED)
        elif dt_pub.year < 2020:
            errors.append(ERR_DATE_FAR_PAST)

    if dl_raw:
        dt_dl = _parse_iso_or_date(dl_raw)
        if not dt_dl:
            errors.append(ERR_DATE_MALFORMED)
        elif dt_dl.year < 2020:
            errors.append(ERR_DATE_FAR_PAST)

    # So sánh logic Deadline vs Published
    if dt_pub and dt_dl:
        # Nếu deadline trước ngày đăng tin
        if dt_dl.date() < dt_pub.date():
            errors.append(ERR_DATE_DEADLINE_BEFORE_PUBLISHED)

    return errors


def evaluate_quarantine_rules(record: Dict[str, Any]) -> List[str]:
    """Kiểm tra toàn bộ các lỗi thuộc nhóm QUARANTINE."""
    errors: List[str] = []
    errors.extend(check_salary_sanity(record))
    errors.extend(check_date_sanity(record))
    return errors


# ==============================================================================
# C. BỘ ĐIỀU PHỐI PHÂN LUỒNG TỔNG THỂ (3-WAY ROUTER)
# ==============================================================================

def route_single_record(
    record: Dict[str, Any], min_content_length: int = MIN_JOB_CONTENT_LENGTH
) -> Tuple[str, List[str]]:
    """
    Phân luồng 1 bản ghi vào đúng 1 trong 3 nhóm:
    
    1. 'invalid': Nếu vi phạm bất kỳ lỗi cốt lõi nào (thiếu URL, title, bot-block).
    2. 'quarantine': Nếu vượt qua Invalid nhưng chứa bất thường logic (lương đảo, deadline sai).
    3. 'valid': Nếu vượt qua mọi tiêu chuẩn chất lượng.
    
    Returns:
        (status, error_codes)
        status: 'valid' | 'quarantine' | 'invalid'
    """
    # Bước 1: Kiểm tra lỗi Invalid trước
    invalid_errors = evaluate_invalid_rules(record, min_content_length=min_content_length)
    if invalid_errors:
        return "invalid", invalid_errors

    # Bước 2: Kiểm tra lỗi Quarantine (Logic anomalies)
    quarantine_errors = evaluate_quarantine_rules(record)
    if quarantine_errors:
        return "quarantine", quarantine_errors

    # Bước 3: Đạt chuẩn Valid
    return "valid", []


def evaluate_valid_rules(record: Dict[str, Any], min_content_length: int = MIN_JOB_CONTENT_LENGTH) -> Tuple[bool, List[str]]:
    """Hàm tương thích ngược: kiểm tra bản ghi có đạt Valid hay không."""
    status, errors = route_single_record(record, min_content_length=min_content_length)
    return status == "valid", errors
