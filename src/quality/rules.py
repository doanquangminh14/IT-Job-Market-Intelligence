"""
Module định nghĩa các quy tắc kiểm tra chất lượng dữ liệu (Data Quality Rules).
Tập trung vào bộ tiêu chí đánh giá tính HỢP LỆ (VALID) của bản ghi tin tuyển dụng thô (Raw Details).
"""

from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

# --- CÁC MÃ LỖI CHUẨN HÓA DÀNH CHO LUỒNG HỢP LỆ (VALID ERROR CODES) ---
ERR_MISSING_JOB_URL = "ERR_MISSING_JOB_URL"
ERR_MISSING_TITLE = "ERR_MISSING_TITLE"
ERR_MISSING_SOURCE = "ERR_MISSING_SOURCE"
ERR_MISSING_JOB_ID = "ERR_MISSING_JOB_ID"
ERR_CONTENT_TOO_SHORT = "ERR_CONTENT_TOO_SHORT"

SUPPORTED_SOURCES = {"topcv", "topdev", "vietnamworks"}
MIN_JOB_CONTENT_LENGTH = 100  # Ngưỡng ký tự tối thiểu để loại trừ trang lỗi/captcha/bot block


def check_identity_and_url(record: Dict[str, Any]) -> List[str]:
    """
    Kiểm tra mã định danh và URL tin tuyển dụng:
    - job_url không được rỗng và phải là một HTTP/HTTPS URL hợp lệ.
    - detail_id hoặc source_job_id phải tồn tại.
    """
    errors: List[str] = []

    # 1. Kiểm tra Job ID
    source_job_id = str(record.get("source_job_id", "") or "").strip()
    detail_id = str(record.get("detail_id", "") or "").strip()
    if not source_job_id and not detail_id:
        errors.append(ERR_MISSING_JOB_ID)

    # 2. Kiểm tra URL
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
    """
    Kiểm tra thông tin tuyển dụng cốt lõi:
    - title_raw không được rỗng (độ dài >= 2 ký tự).
    - source phải thuộc danh sách sàn hỗ trợ.
    """
    errors: List[str] = []

    # 1. Tiêu đề
    title = str(record.get("title_raw", "") or "").strip()
    if len(title) < 2:
        errors.append(ERR_MISSING_TITLE)

    # 2. Sàn nguồn
    source = str(record.get("source", "") or "").strip().lower()
    if not source or source not in SUPPORTED_SOURCES:
        errors.append(ERR_MISSING_SOURCE)

    return errors


def check_content_length(record: Dict[str, Any], min_length: int = MIN_JOB_CONTENT_LENGTH) -> List[str]:
    """
    Kiểm tra tổng độ dài mô tả công việc (overview + responsibilities + requirements + benefits).
    Nếu tổng < 100 ký tự -> nghi vấn trang bị lỗi Cloudflare, Captcha, hoặc bài đăng rỗng.
    """
    errors: List[str] = []

    overview = str(record.get("overview_raw", "") or "").strip()
    responsibilities = str(record.get("responsibilities_raw", "") or "").strip()
    requirements = str(record.get("requirements_raw", "") or "").strip()
    benefits = str(record.get("benefits_raw", "") or "").strip()

    total_content = f"{overview} {responsibilities} {requirements} {benefits}".strip()
    if len(total_content) < min_length:
        errors.append(ERR_CONTENT_TOO_SHORT)

    return errors


def evaluate_valid_rules(record: Dict[str, Any], min_content_length: int = MIN_JOB_CONTENT_LENGTH) -> Tuple[bool, List[str]]:
    """
    Hàm tổng hợp đánh giá bản ghi có đạt chuẩn HỢP LỆ (VALID) hay không.
    
    Returns:
        (is_valid, error_list)
        - is_valid: True nếu vượt qua tất cả các bài kiểm tra, False nếu vi phạm bất kỳ tiêu chuẩn nào.
        - error_list: Danh sách các mã lỗi vi phạm chuẩn hóa.
    """
    all_errors: List[str] = []

    all_errors.extend(check_identity_and_url(record))
    all_errors.extend(check_core_info(record))
    all_errors.extend(check_content_length(record, min_length=min_content_length))

    is_valid = len(all_errors) == 0
    return is_valid, all_errors
