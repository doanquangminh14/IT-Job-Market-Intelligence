"""
Package src.quality: Động cơ kiểm tra chất lượng dữ liệu (Data Quality Engine).
Hỗ trợ phân luồng 3 hướng: Valid | Quarantine | Invalid.
"""

from src.quality.rules import (
    ERR_CONTENT_TOO_SHORT,
    ERR_DATE_DEADLINE_BEFORE_PUBLISHED,
    ERR_DATE_FAR_PAST,
    ERR_DATE_MALFORMED,
    ERR_MISSING_JOB_ID,
    ERR_MISSING_JOB_URL,
    ERR_MISSING_SOURCE,
    ERR_MISSING_TITLE,
    ERR_SALARY_INVERTED,
    ERR_SALARY_NEGATIVE,
    ERR_SALARY_OUTLIER,
    MIN_JOB_CONTENT_LENGTH,
    evaluate_invalid_rules,
    evaluate_quarantine_rules,
    evaluate_valid_rules,
    route_single_record,
)
from src.quality.validator import QualityValidator

__all__ = [
    # Mã lỗi Invalid
    "ERR_MISSING_JOB_URL",
    "ERR_MISSING_TITLE",
    "ERR_MISSING_SOURCE",
    "ERR_MISSING_JOB_ID",
    "ERR_CONTENT_TOO_SHORT",
    # Mã lỗi Quarantine
    "ERR_SALARY_INVERTED",
    "ERR_SALARY_NEGATIVE",
    "ERR_SALARY_OUTLIER",
    "ERR_DATE_DEADLINE_BEFORE_PUBLISHED",
    "ERR_DATE_FAR_PAST",
    "ERR_DATE_MALFORMED",
    # Hằng số & Hàm đánh giá
    "MIN_JOB_CONTENT_LENGTH",
    "evaluate_invalid_rules",
    "evaluate_quarantine_rules",
    "evaluate_valid_rules",
    "route_single_record",
    # Class điều phối
    "QualityValidator",
]
