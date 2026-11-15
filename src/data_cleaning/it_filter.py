"""Phân loại tin tuyển dụng thuộc lĩnh vực IT hay không (phục vụ lọc nhiễu cho CBF).

Từ khóa và kỹ năng lõi nằm trong configs/dictionaries/it_filter.yaml.
"""
import re
from typing import Iterable, Union

from src.data_cleaning.dictionaries import load_dictionary

_CFG = load_dictionary("it_filter")

# Chức danh/từ khóa đặc trưng của nghề IT (mỗi từ khóa là một mẫu regex, ghép bằng "|")
IT_TITLE_PATTERN = re.compile("(" + "|".join(_CFG["it_title_keywords"]) + ")", re.IGNORECASE)

# Kỹ năng công nghệ lõi: có >= 2 kỹ năng này thì coi là việc IT dù tiêu đề mơ hồ
CORE_IT_SKILLS = {str(s).lower() for s in _CFG["core_it_skills"]}


def _skill_list(skills: Union[str, Iterable[str], None]) -> list:
    if skills is None or isinstance(skills, float):  # None hoặc NaN
        return []
    if isinstance(skills, str):
        return [s.strip().lower() for s in skills.split(",") if s.strip()]
    return [str(s).strip().lower() for s in skills if str(s).strip()]


def is_it_job(title: str, required_skills: Union[str, Iterable[str], None] = None, min_core_skills: int = 2) -> bool:
    """True nếu tiêu đề mang tính IT hoặc có >= min_core_skills kỹ năng công nghệ lõi."""
    if title and IT_TITLE_PATTERN.search(str(title)):
        return True
    return len(set(_skill_list(required_skills)) & CORE_IT_SKILLS) >= min_core_skills
