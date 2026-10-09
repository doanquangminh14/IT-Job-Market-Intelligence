from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import os
import json
import pandas as pd


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
