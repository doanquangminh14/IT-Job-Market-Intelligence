"""
Package src.quality: Động cơ kiểm tra chất lượng dữ liệu (Data Quality Engine).
"""

from src.quality.rules import (
    ERR_CONTENT_TOO_SHORT,
    ERR_MISSING_JOB_ID,
    ERR_MISSING_JOB_URL,
    ERR_MISSING_SOURCE,
    ERR_MISSING_TITLE,
    MIN_JOB_CONTENT_LENGTH,
    evaluate_valid_rules,
)
from src.quality.validator import QualityValidator

__all__ = [
    "ERR_MISSING_JOB_URL",
    "ERR_MISSING_TITLE",
    "ERR_MISSING_SOURCE",
    "ERR_MISSING_JOB_ID",
    "ERR_CONTENT_TOO_SHORT",
    "MIN_JOB_CONTENT_LENGTH",
    "evaluate_valid_rules",
    "QualityValidator",
]
