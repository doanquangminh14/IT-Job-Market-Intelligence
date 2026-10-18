import re
import hashlib
from datetime import datetime
import pandas as pd

def clean_html_text(text):
    """
    Làm sạch thẻ HTML, giải mã thực thể HTML (&nbsp;, &amp;...),
    chuẩn hóa ký tự đầu dòng (bullet points) và loại bỏ khoảng trắng / dòng trống thừa.
    """
    if not text or pd.isna(text):
        return ""
    s = str(text)
    # 1. Giải mã các thực thể HTML phổ biến
    s = s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    # 2. Thay thế các thẻ ngắt khối bằng ký tự xuống dòng
    s = re.sub(r'<(?:br|/p|/li|/div|/h\d)[^>]*>', '\n', s, flags=re.IGNORECASE)
    # 3. Loại bỏ toàn bộ các thẻ HTML còn lại
    s = re.sub(r'<[^>]+>', ' ', s)
    # 4. Chuẩn hóa các dấu gạch đầu dòng (bullet points) về '- '
    s = re.sub(r'^[ \t]*[-\*\+\–•][ \t]*', '- ', s, flags=re.MULTILINE)
    # 5. Rút gọn khoảng trắng giữa các từ
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in s.split('\n')]
    # 6. Giữ lại các dòng có nội dung thực tế, loại bỏ dòng trống liên tiếp
    compact_lines = [line for line in lines if line]
    return '\n'.join(compact_lines)

def detect_language(text):
    """
    Nhận diện ngôn ngữ chính của bài đăng:
    - 'vi': Tiếng Việt
    - 'en': Tiếng Anh
    - 'vi-en': Song ngữ
    """
    if not text or pd.isna(text):
        return 'vi'
    s = str(text).lower()
    vn_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ')
    vn_words = ['và', 'các', 'của', 'trong', 'với', 'cho', 'khi', 'được', 'người', 'công việc', 'kinh nghiệm', 'yêu cầu', 'quyền lợi', 'kỹ năng']
    en_words = ['and', 'the', 'of', 'in', 'with', 'for', 'when', 'experience', 'requirements', 'skills', 'responsibilities', 'benefits', 'team', 'develop']

    vn_char_count = sum(1 for c in s if c in vn_chars)
    vn_word_hits = sum(1 for w in vn_words if re.search(r'\b' + re.escape(w) + r'\b', s))
    en_word_hits = sum(1 for w in en_words if re.search(r'\b' + re.escape(w) + r'\b', s))

    if vn_char_count > 10 or vn_word_hits >= 3:
        if en_word_hits >= 4 and vn_word_hits >= 3:
            return 'vi-en'
        return 'vi'
    elif en_word_hits > vn_word_hits:
        return 'en'
    return 'vi'

def compute_sha256(text):
    """Tính toán mã băm SHA256 nhận diện biến động nội dung bài đăng giữa các lần crawl."""
    if not text:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

def transform_job_descriptions(bronze_data):
    """
    Chuyển đổi dữ liệu Bronze thành danh sách các bản ghi chuẩn hóa của bảng job_descriptions.
    Đồng bộ 100% quan hệ 1-1 với job_id của bảng jobs.
    """
    df_merged = bronze_data["df_merged"]

    print(f"-> [Transformer: job_descriptions] Làm sạch nội dung văn bản cho {len(df_merged):,} việc làm...")
    desc_records = []

    for idx, row in df_merged.iterrows():
        job_id = row['job_id']
        overview_raw = str(row.get('overview_raw', '') or '').strip()
        responsibilities_raw = str(row.get('responsibilities_raw', '') or '').strip()
        requirements_raw = str(row.get('requirements_raw', '') or '').strip()
        benefits_raw = str(row.get('benefits_raw', '') or '').strip()

        # Tạo description_clean: Ưu tiên mô tả công việc / trách nhiệm thực tế (responsibilities_raw)
        # Chỉ fallback về overview_raw nếu công việc không có responsibilities_raw
        if responsibilities_raw:
            desc_combined = responsibilities_raw
        elif overview_raw:
            desc_combined = overview_raw
        else:
            desc_combined = ""

        desc_clean = clean_html_text(desc_combined)
        req_clean = clean_html_text(requirements_raw)
        ben_clean = clean_html_text(benefits_raw)

        full_content = f"{desc_clean}\n{req_clean}\n{ben_clean}".strip()
        lang = detect_language(full_content)
        text_hash = compute_sha256(full_content)

        desc_records.append({
            'job_id': job_id,
            'overview_raw': overview_raw if overview_raw else None,
            'responsibilities_raw': responsibilities_raw if responsibilities_raw else None,
            'requirements_raw': requirements_raw if requirements_raw else None,
            'benefits_raw': benefits_raw if benefits_raw else None,
            'description_clean': desc_clean if desc_clean else None,
            'requirements_clean': req_clean if req_clean else None,
            'benefits_clean': ben_clean if ben_clean else None,
            'language': lang,
            'text_hash': text_hash
        })

    print(f"   [Transformer: job_descriptions] Đã làm sạch thành công: {len(desc_records):,} bản ghi mô tả.")
    return desc_records
