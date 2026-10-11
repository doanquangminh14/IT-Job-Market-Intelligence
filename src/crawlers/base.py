from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import os
import re
import json
from datetime import datetime, timedelta
import pandas as pd


def parse_relative_deadline(text: str, base_date: Optional[datetime] = None) -> str:
    """
    Phát hiện các mẫu thời gian tương đối như 'Còn 28 ngày', 'Hết hạn trong 11 ngày', '5 days left',
    hoặc ngày cụ thể '28/10/2026' để quy đổi ra ngày hết hạn chuẩn ISO YYYY-MM-DD.
    Dùng làm phương án dự phòng (fallback) nếu backend không trả về ngày hết hạn gốc.
    """
    if not text:
        return ""
    if base_date is None:
        base_date = datetime.now()

    # 1. Mẫu: 'Còn X ngày', 'Hết hạn trong X ngày', 'X days left'
    m = re.search(r'(?:còn|hết hạn trong|hạn nộp|còn lại)\s*(\d+)\s*ngày', text, re.IGNORECASE)
    if not m:
        m = re.search(r'(\d+)\s*days?\s*left', text, re.IGNORECASE)
    if m:
        days = int(m.group(1))
        return (base_date + timedelta(days=days)).strftime("%Y-%m-%d")

    # 2. Mẫu: 'Hôm nay hết hạn', 'Còn X giờ'
    if re.search(r'hôm nay hết hạn|hết hạn hôm nay|expires today', text, re.IGNORECASE):
        return base_date.strftime("%Y-%m-%d")
    if re.search(r'(?:còn|hết hạn trong)\s*\d+\s*(?:giờ|hours?)', text, re.IGNORECASE):
        return base_date.strftime("%Y-%m-%d")

    # 3. Mẫu: Ngày cụ thể DD/MM/YYYY hoặc DD-MM-YYYY
    m_date = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if m_date:
        d, m, y = m_date.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    return ""


class BaseCrawler(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_name = config.get("name", "UnknownSource")
        self.base_url = config.get("base_url", "")
        self.rate_limit = config.get("rate_limit", {})

    @abstractmethod
    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
        """Thực thi toàn bộ luồng cào dữ liệu với mục tiêu số job thành công"""
        pass

    def save_records(
        self,
        folder_path: str,
        file_prefix: str,
        records: List[Dict[str, Any]]
    ) -> None:
        """Lưu danh sách records ra cả file .csv và .json"""
        if not records:
            return

        os.makedirs(folder_path, exist_ok=True)
        df = pd.DataFrame(records)

        # 1. Lưu file CSV với encoding utf-8-sig (hỗ trợ tốt tiếng Việt trên Excel)
        csv_file = os.path.join(folder_path, f"{file_prefix}.csv")
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")

        # 2. Lưu file JSON chuẩn tiếng Việt
        json_file = os.path.join(folder_path, f"{file_prefix}.json")
        df.to_json(json_file, orient="records", force_ascii=False, indent=2)
