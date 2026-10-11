"""
Module điều phối động cơ kiểm định chất lượng dữ liệu (QualityValidator).
Thực hiện đánh giá từng bản ghi, lọc ra các bản ghi hợp lệ (VALID),
gắn nhãn kiểm định Data Quality và hỗ trợ lưu trữ vào tầng Bronze.
"""

import json
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.quality.rules import (
    MIN_JOB_CONTENT_LENGTH,
    evaluate_valid_rules,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class QualityValidator:
    """
    Động cơ kiểm tra chất lượng dữ liệu và phân luồng bản ghi hợp lệ.
    """

    def __init__(self, min_content_length: int = MIN_JOB_CONTENT_LENGTH, bronze_dir: Optional[str] = None):
        self.min_content_length = min_content_length
        self.bronze_base_dir = bronze_dir or os.path.join(PROJECT_ROOT, "data", "bronze")

    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kiểm tra 1 bản ghi và gắn kèm metadata chất lượng dữ liệu (_dq_*).
        
        Trả về bản sao của record kèm các trường:
        - _dq_status: 'valid' hoặc 'invalid'
        - _dq_errors: Danh sách mã lỗi nếu không hợp lệ
        - _dq_checked_at: Thời điểm thực hiện kiểm tra (ISO format)
        """
        enriched = dict(record)
        is_valid, errors = evaluate_valid_rules(record, min_content_length=self.min_content_length)

        enriched["_dq_status"] = "valid" if is_valid else "invalid"
        enriched["_dq_errors"] = errors
        enriched["_dq_checked_at"] = datetime.now().isoformat()

        return enriched

    def filter_valid_records(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Quét qua danh sách các bản ghi thô:
        1. Lọc ra các bản ghi đạt chuẩn HỢP LỆ (VALID).
        2. Tổng hợp báo cáo thống kê tỷ lệ hợp lệ và các lỗi phát hiện.
        
        Returns:
            (valid_records, quality_summary)
        """
        valid_records: List[Dict[str, Any]] = []
        error_counter = Counter()
        invalid_count = 0

        for rec in records:
            checked = self.validate_record(rec)
            if checked["_dq_status"] == "valid":
                valid_records.append(checked)
            else:
                invalid_count += 1
                for err in checked["_dq_errors"]:
                    error_counter[err] += 1

        total_scanned = len(records)
        valid_count = len(valid_records)
        valid_rate = round((valid_count / total_scanned * 100), 2) if total_scanned > 0 else 0.0

        summary = {
            "total_scanned": total_scanned,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "valid_rate_pct": valid_rate,
            "errors_breakdown": dict(error_counter),
        }

        return valid_records, summary

    def save_valid_to_bronze(
        self,
        valid_records: List[Dict[str, Any]],
        source: str,
        target_date: Optional[str] = None,
        file_prefix: str = "bronze_batch",
    ) -> str:
        """
        Lưu danh sách các bản ghi hợp lệ vào tầng Bronze:
        Cấu trúc: data/bronze/{source}/{target_date}/{file_prefix}.json
        
        Returns:
            Đường dẫn tuyệt đối của file đã lưu.
        """
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        dest_dir = os.path.join(self.bronze_base_dir, source.lower(), date_str)
        os.makedirs(dest_dir, exist_ok=True)

        file_name = f"{file_prefix}.json"
        dest_filepath = os.path.join(dest_dir, file_name)

        with open(dest_filepath, "w", encoding="utf-8") as f:
            json.dump(valid_records, f, ensure_ascii=False, indent=2)

        return dest_filepath
