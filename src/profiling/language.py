import re
from typing import Literal

LanguageType = Literal["vi", "en", "mixed", "unknown"]

VI_DIACRITICS_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

VI_KEYWORDS = {
    "tuyển", "công việc", "yêu cầu", "mô tả", "quyền lợi", "kinh nghiệm", "lương",
    "địa điểm", "hồ sơ", "ứng viên", "chúng tôi", "phúc lợi", "bảo hiểm", "chế độ"
}

EN_KEYWORDS = {
    "responsibilities", "requirements", "benefits", "experience", "salary",
    "description", "qualifications", "looking for", "skills", "must have",
    "nice to have", "developer", "engineer", "team", "opportunity", "working"
}


def detect_job_language(text: str) -> LanguageType:
    """
    Nhận diện ngôn ngữ của tin tuyển dụng dựa trên dấu tiếng Việt và từ khóa đặc trưng.
    Trả về:
    - 'vi': Tiếng Việt
    - 'en': Tiếng Anh
    - 'mixed': Song ngữ
    - 'unknown': Văn bản quá ngắn hoặc không xác định
    """
    if not text or len(text.strip()) < 30:
        return "unknown"

    lower_text = text.lower()

    # 1. Kiểm tra mật độ ký tự có dấu tiếng Việt
    vi_diacritic_matches = len(VI_DIACRITICS_PATTERN.findall(lower_text))

    # 2. Đếm số từ khóa tiếng Việt & tiếng Anh xuất hiện
    vi_kw_count = sum(1 for kw in VI_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower_text))
    en_kw_count = sum(1 for kw in EN_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower_text))

    # Đánh giá:
    is_vi = vi_diacritic_matches >= 5 or vi_kw_count >= 3
    is_en = en_kw_count >= 4 and vi_diacritic_matches <= 2

    if is_vi and en_kw_count >= 2:
        # Có dấu tiếng Việt nhưng các phần mô tả/yêu cầu lại dùng tiếng Anh
        return "mixed"
    elif is_vi:
        return "vi"
    elif is_en:
        return "en"
    elif vi_diacritic_matches > 0:
        return "vi"
    elif en_kw_count >= 2:
        return "en"
    return "unknown"
