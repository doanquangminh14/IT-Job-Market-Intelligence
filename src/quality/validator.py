"""
Module điều phối động cơ kiểm định và phân luồng chất lượng dữ liệu (QualityValidator).
Thực hiện đánh giá từng bản ghi, phân loại vào 3 luồng:
1. VALID -> Tầng Bronze (data/bronze/)
2. QUARANTINE -> Khu cách ly (data/quarantine/)
3. INVALID -> Dữ liệu rác/lỗi (data/invalid/)
"""

import json
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.quality.rules import (
    MIN_JOB_CONTENT_LENGTH,
    route_single_record,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class QualityValidator:
    """
    Động cơ kiểm tra chất lượng dữ liệu và phân luồng 3 hướng:
    Valid | Quarantine | Invalid.
    """

    def __init__(
        self,
        min_content_length: int = MIN_JOB_CONTENT_LENGTH,
        bronze_dir: Optional[str] = None,
        quarantine_dir: Optional[str] = None,
        invalid_dir: Optional[str] = None,
    ):
        self.min_content_length = min_content_length
        self.bronze_base_dir = bronze_dir or os.path.join(PROJECT_ROOT, "data", "bronze")
        self.quarantine_base_dir = quarantine_dir or os.path.join(PROJECT_ROOT, "data", "quarantine")
        self.invalid_base_dir = invalid_dir or os.path.join(PROJECT_ROOT, "data", "invalid")

    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kiểm tra 1 bản ghi và gắn kèm metadata chất lượng dữ liệu (_dq_*).
        
        Các trường bổ sung:
        - _dq_status: 'valid' | 'quarantine' | 'invalid'
        - _dq_errors: Danh sách mã lỗi chuẩn hóa nếu có
        - _dq_checked_at: Thời điểm kiểm tra (ISO format)
        """
        enriched = dict(record)
        status, errors = route_single_record(record, min_content_length=self.min_content_length)

        enriched["_dq_status"] = status
        enriched["_dq_errors"] = errors
        enriched["_dq_checked_at"] = datetime.now().isoformat()

        return enriched

    def route_records(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Quét và phân loại toàn bộ bản ghi thành 3 nhóm độc lập:
        
        Returns:
            (valid_records, quarantine_records, invalid_records, summary)
        """
        valid_records: List[Dict[str, Any]] = []
        quarantine_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []
        error_counter = Counter()

        for rec in records:
            checked = self.validate_record(rec)
            status = checked["_dq_status"]

            if status == "valid":
                valid_records.append(checked)
            elif status == "quarantine":
                quarantine_records.append(checked)
                for err in checked["_dq_errors"]:
                    error_counter[err] += 1
            else:  # invalid
                invalid_records.append(checked)
                for err in checked["_dq_errors"]:
                    error_counter[err] += 1

        total_scanned = len(records)
        v_count = len(valid_records)
        q_count = len(quarantine_records)
        i_count = len(invalid_records)

        summary = {
            "total_scanned": total_scanned,
            "valid_count": v_count,
            "valid_rate_pct": round(v_count / total_scanned * 100, 2) if total_scanned else 0.0,
            "quarantine_count": q_count,
            "quarantine_rate_pct": round(q_count / total_scanned * 100, 2) if total_scanned else 0.0,
            "invalid_count": i_count,
            "invalid_rate_pct": round(i_count / total_scanned * 100, 2) if total_scanned else 0.0,
            "errors_breakdown": dict(error_counter),
        }

        return valid_records, quarantine_records, invalid_records, summary

    def filter_valid_records(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Hàm tương thích: Lọc lấy các bản ghi Valid.
        (Bản ghi không đạt tính cả quarantine + invalid).
        """
        valid_records, quarantine_records, invalid_records, summary = self.route_records(records)
        compat_summary = {
            "total_scanned": summary["total_scanned"],
            "valid_count": summary["valid_count"],
            "invalid_count": summary["quarantine_count"] + summary["invalid_count"],
            "valid_rate_pct": summary["valid_rate_pct"],
            "errors_breakdown": summary["errors_breakdown"],
        }
        return valid_records, compat_summary

    def _save_json_file(self, records: List[Dict[str, Any]], base_dir: str, source: str, target_date: str, file_prefix: str) -> str:
        """Helper lưu file JSON phân cấp theo source/date."""
        dest_dir = os.path.join(base_dir, source.lower(), target_date)
        os.makedirs(dest_dir, exist_ok=True)
        file_path = os.path.join(dest_dir, f"{file_prefix}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return file_path

    def save_valid_to_bronze(
        self,
        valid_records: List[Dict[str, Any]],
        source: str,
        target_date: Optional[str] = None,
        file_prefix: str = "bronze_batch",
    ) -> str:
        """Lưu bản ghi Valid vào tầng Bronze (data/bronze/)."""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(valid_records, self.bronze_base_dir, source, date_str, file_prefix)

    def save_to_quarantine(
        self,
        quarantine_records: List[Dict[str, Any]],
        source: str,
        target_date: Optional[str] = None,
        file_prefix: str = "quarantine_batch",
    ) -> str:
        """Lưu bản ghi bị cách ly vào data/quarantine/."""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(quarantine_records, self.quarantine_base_dir, source, date_str, file_prefix)

    def save_to_invalid(
        self,
        invalid_records: List[Dict[str, Any]],
        source: str,
        target_date: Optional[str] = None,
        file_prefix: str = "invalid_batch",
    ) -> str:
        """Lưu bản ghi rác/hỏng vào data/invalid/."""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(invalid_records, self.invalid_base_dir, source, date_str, file_prefix)
