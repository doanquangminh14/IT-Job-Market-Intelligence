"""
Module điều phối động cơ kiểm định và phân luồng chất lượng dữ liệu (QualityValidator).
Hỗ trợ lưu trữ tích lũy (Master Cumulation) vào tầng Bronze (data/bronze/):
- bronze_listings_master.json : Bảng tổng hợp toàn bộ Listings của các sàn
- bronze_details_valid.json   : Bảng tổng hợp toàn bộ Details đạt chuẩn Valid
- bronze_details_quarantine.json : Bảng tổng hợp các Details bị cách ly (nếu có)
- bronze_details_invalid.json : Bảng tổng hợp các Details bị lỗi/rác (nếu có)
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
    Valid | Quarantine | Invalid kèm cơ chế tích lũy Master Bronze.
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
        Kiểm tra 1 bản ghi và gắn kèm metadata chất lượng dữ liệu (dq_*).
        
        Các trường bổ sung:
        - dq_status: 'valid' | 'quarantine' | 'invalid'
        - dq_errors: Danh sách mã lỗi chuẩn hóa nếu có
        - dq_checked_at: Thời điểm kiểm tra (ISO format)
        (đồng thời giữ _dq_* để tương thích hoàn toàn)
        """
        enriched = dict(record)
        status, errors = route_single_record(record, min_content_length=self.min_content_length)

        now_str = datetime.now().isoformat()
        enriched["dq_status"] = status
        enriched["dq_errors"] = errors
        enriched["dq_checked_at"] = now_str

        # Tương thích ngược
        enriched["_dq_status"] = status
        enriched["_dq_errors"] = errors
        enriched["_dq_checked_at"] = now_str

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
            status = checked["dq_status"]

            if status == "valid":
                valid_records.append(checked)
            elif status == "quarantine":
                quarantine_records.append(checked)
                for err in checked["dq_errors"]:
                    error_counter[err] += 1
            else:  # invalid
                invalid_records.append(checked)
                for err in checked["dq_errors"]:
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
        """Hàm tương thích: Lọc lấy các bản ghi Valid."""
        valid_records, quarantine_records, invalid_records, summary = self.route_records(records)
        compat_summary = {
            "total_scanned": summary["total_scanned"],
            "valid_count": summary["valid_count"],
            "invalid_count": summary["quarantine_count"] + summary["invalid_count"],
            "valid_rate_pct": summary["valid_rate_pct"],
            "errors_breakdown": summary["errors_breakdown"],
        }
        return valid_records, compat_summary

    # ==========================================================================
    # CƠ CHẾ NẠP TÍCH LŨY (UPSERT MASTER FILES) TẠI TẦNG BRONZE
    # ==========================================================================

    def _upsert_json_file(self, new_records: List[Dict[str, Any]], target_file: str) -> Tuple[str, int, int]:
        """
        Nạp tích lũy và khử trùng lặp theo (source, source_job_id):
        - Nếu tin đã tồn tại -> cập nhật nội dung mới nhất.
        - Nếu tin mới -> bổ sung thêm vào.
        
        Returns:
            (target_file, new_added_count, total_count)
        """
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        master_dict: Dict[str, Dict[str, Any]] = {}

        # 1. Đọc dữ liệu cũ nếu file master đã tồn tại
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        for item in existing_data:
                            k = f"{item.get('source', '')}_{item.get('source_job_id', '')}"
                            if k != "_":
                                master_dict[k] = item
            except Exception as e:
                print(f"[CANH BAO] Không thể đọc file master cũ {target_file}: {e}")

        old_count = len(master_dict)

        # 2. Upsert dữ liệu mới vào
        for r in new_records:
            k = f"{r.get('source', '')}_{r.get('source_job_id', '')}"
            if k != "_":
                master_dict[k] = r
            else:
                # Nếu thiếu source_job_id, dùng detail_id hoặc job_url làm fallback key
                fallback_key = r.get("detail_id") or r.get("job_url") or str(id(r))
                master_dict[str(fallback_key)] = r

        total_count = len(master_dict)
        new_added = total_count - old_count

        # 3. Ghi lại ra file master dạng list
        master_list = list(master_dict.values())
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(master_list, f, ensure_ascii=False, indent=2)

        return target_file, new_added, total_count

    def save_master_listings(self, listings: List[Dict[str, Any]]) -> Tuple[str, int, int]:
        """Lưu tích lũy vào data/bronze/bronze_listings_master.json."""
        target_file = os.path.join(self.bronze_base_dir, "bronze_listings_master.json")
        return self._upsert_json_file(listings, target_file)

    def save_master_details_valid(self, valid_details: List[Dict[str, Any]]) -> Tuple[str, int, int]:
        """Lưu tích lũy vào data/bronze/bronze_details_valid.json."""
        target_file = os.path.join(self.bronze_base_dir, "bronze_details_valid.json")
        return self._upsert_json_file(valid_details, target_file)

    def save_master_details_quarantine(self, quarantine_details: List[Dict[str, Any]]) -> Tuple[str, int, int]:
        """Lưu tích lũy vào data/bronze/bronze_details_quarantine.json."""
        target_file = os.path.join(self.bronze_base_dir, "bronze_details_quarantine.json")
        return self._upsert_json_file(quarantine_details, target_file)

    def save_master_details_invalid(self, invalid_details: List[Dict[str, Any]]) -> Tuple[str, int, int]:
        """Lưu tích lũy vào data/bronze/bronze_details_invalid.json."""
        target_file = os.path.join(self.bronze_base_dir, "bronze_details_invalid.json")
        return self._upsert_json_file(invalid_details, target_file)

    # ==========================================================================
    # CÁC HÀM LƯU PHÂN CẤP CŨ (BACKWARD COMPATIBILITY CHO UNIT TESTS)
    # ==========================================================================

    def _save_json_file(self, records: List[Dict[str, Any]], base_dir: str, source: str, target_date: str, file_prefix: str) -> str:
        dest_dir = os.path.join(base_dir, source.lower(), target_date)
        os.makedirs(dest_dir, exist_ok=True)
        file_path = os.path.join(dest_dir, f"{file_prefix}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return file_path

    def save_valid_to_bronze(self, valid_records: List[Dict[str, Any]], source: str, target_date: Optional[str] = None, file_prefix: str = "bronze_batch") -> str:
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(valid_records, self.bronze_base_dir, source, date_str, file_prefix)

    def save_to_quarantine(self, quarantine_records: List[Dict[str, Any]], source: str, target_date: Optional[str] = None, file_prefix: str = "quarantine_batch") -> str:
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(quarantine_records, self.quarantine_base_dir, source, date_str, file_prefix)

    def save_to_invalid(self, invalid_records: List[Dict[str, Any]], source: str, target_date: Optional[str] = None, file_prefix: str = "invalid_batch") -> str:
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        return self._save_json_file(invalid_records, self.invalid_base_dir, source, date_str, file_prefix)
