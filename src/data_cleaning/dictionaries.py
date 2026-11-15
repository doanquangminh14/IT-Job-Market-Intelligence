"""Đọc các từ điển cấu hình trong configs/dictionaries/*.yaml.

Từ điển (kỹ năng, nhóm kỹ năng gần nhau, quy tắc tách thẻ, từ khóa nghề IT) được viết ở dạng YAML để dễ tìm,
dễ đọc và dễ sửa; notebook 02, notebook 05 và ứng dụng Streamlit đều đọc qua module này.
"""
import os
from functools import lru_cache
from typing import Any, Dict

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DICTIONARY_DIR = os.path.join(PROJECT_ROOT, "configs", "dictionaries")


@lru_cache(maxsize=None)
def load_dictionary(name: str) -> Dict[str, Any]:
    """Nội dung file configs/dictionaries/<name>.yaml."""
    path = os.path.join(DICTIONARY_DIR, f"{name}.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def alias_map(groups: Dict[str, Dict[str, list]]) -> Dict[str, str]:
    """{nhóm: {tên chuẩn: [cách viết, ...]}} ➔ {cách viết: tên chuẩn}, giữ thứ tự trong file."""
    out: Dict[str, str] = {}
    for canons in (groups or {}).values():
        for canon, aliases in (canons or {}).items():
            for alias in aliases or []:
                alias = str(alias).strip().lower()
                if alias in out and out[alias] != str(canon):
                    raise ValueError(f"Cách viết '{alias}' bị gán cho 2 kỹ năng: '{out[alias]}' và '{canon}'")
                out[alias] = str(canon)
    return out
