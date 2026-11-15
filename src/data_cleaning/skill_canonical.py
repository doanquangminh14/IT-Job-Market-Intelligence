import re
from typing import Dict, List, Optional, Set, Tuple

from src.data_cleaning.dictionaries import alias_map, load_dictionary

# Từ điển kỹ năng: configs/dictionaries/skills.yaml (dạng "Tên chuẩn: [các cách viết]", chia theo nhóm)
_SKILLS = load_dictionary("skills")
CANONICAL_SKILL_MAP = alias_map(_SKILLS["canonical"])      # cách viết ➔ tên chuẩn

# Danh sách từ khóa rác, phúc lợi, nhân thân, ngành nghề cần loại trừ triệt để
EXCLUDE_PATTERNS = [
    # 1. Phúc lợi, phụ cấp, thiết bị cá nhân
    r'xăng\s*xe', r'xăng', r'xe\s*máy', r'tai\s*nghe', r'ăn\s*trưa', r'cơm\s*trưa', r'tiền\s*ăn',
    r'gửi\s*xe', r'vé\s*xe', r'bãi\s*xe', r'đồng\s*phục', r'điện\s*thoại', r'laptop', r'máy\s*tính',
    r'thiết\s*bị', r'cấp\s*phát', r'công\s*cụ\s*làm\s*việc', r'bảo\s*hiểm', r'bhxh', r'bhyt', r'bhtn',
    r'khám\s*sức\s*khỏe', r'khám\s*định\s*kỳ', r'thưởng', r'tháng\s*13', r'lương\s*tháng', r'bonus',
    r'hoa\s*hồng', r'du\s*lịch', r'nghỉ\s*mát', r'nghỉ\s*phép', r'phép\s*năm', r'team\s*building',
    r'teambuilding', r'sinh\s*nhật', r'quà\s*tặng', r'hiếu\s*hỉ', r'thể\s*thao', r'gym', r'yoga',
    r'chăm\s*sóc', r'đãi\s*ngộ', r'phụ\s*cấp', r'hỗ\s*trợ',

    # 2. Ngành nghề / Lĩnh vực doanh nghiệp (Domain / Industry)
    r'thương\s*mại\s*điện\s*tử', r'e-?commerce', r'bán\s*lẻ', r'ngân\s*hàng', r'tài\s*chính',
    r'chứng\s*khoán', r'bất\s*động\s*sản', r'giáo\s*dục', r'y\s*tế', r'fmcg', r'logistics',
    r'xuất\s*nhập\s*khẩu', r'sản\s*xuất', r'nông\s*nghiệp', r'du\s*lịch\s*-\s*khách\s*sạn', r'f&b',
    r'xây\s*dựng', r'nội\s*thất', r'thực\s*phẩm', r'dược\s*phẩm', r'viễn\s*thông', r'vận\s*tải',

    # 3. Kênh bán hàng, chức năng thương mại không thuộc IT
    r'b2b', r'b2c', r'telesales', r'direct\s*sales', r'online\s*sales', r'bán\s*hàng',
    r'tư\s*vấn', r'kinh\s*doanh', r'chăm\s*sóc\s*khách\s*hàng', r'cskh', r'sales?',
    r'marketing', r'quảng\s*cáo', r'digital\s*marketing', r'seo', r'content', r'kinh\s*doanh\s*phần\s*mềm',

    # 4. Chức danh, cấp bậc (Job Titles, Seniority)
    r'data\s*analyst', r'business\s*analyst', r'developer', r'tester', r'engineer',
    r'product\s*owner', r'product\s*manager', r'nhân\s*viên', r'chuyên\s*viên', r'trưởng\s*nhóm',
    r'quản\s*lý', r'thực\s*tập', r'fresher', r'intern', r'junior', r'middle', r'senior',
    r'leader?', r'head', r'giám\s*đốc', r'cán\s*bộ', r'trợ\s*lý', r'thư\s*ký',

    # 5. Phân loại chung của sàn và tiêu chí nhân thân
    r'it\s*-\s*phần\s*mềm', r'công\s*nghệ\s*thông\s*tin\s*khác', r'chuyên\s*môn', r'toàn\s*thời\s*gian',
    r'bán\s*thời\s*gian', r'full\s*time', r'part\s*time', r'onsite', r'remote', r'hybrid',
    r'cao\s*đẳng', r'đại\s*học', r'trung\s*cấp', r'bằng\s*cấp', r'chứng\s*chỉ', r'kinh\s*nghiệm',
    r'trở\s*lên', r'yêu\s*cầu', r'kỹ\s*năng', r'tiêu\s*chuẩn', r'trách\s*nhiệm', r'nhiệm\s*vụ',
    r'tuổi\s*\d+', r'nam', r'nữ', r'giới\s*tính', r'xem\s*tất\s*cả', r'đọc\s*hiểu', r'giao\s*tiếp',
    r'mỹ\s*thuật', r'nghệ\s*thuật', r'kiến\s*trúc'
]


def normalize_skill_name(skill_str: str) -> Optional[str]:
    """
    Chuẩn hóa tên kỹ năng về dạng chuẩn (Canonical Form).
    Chỉ trả về tên chuẩn nếu là kỹ năng công nghệ thực sự.
    """
    if not skill_str:
        return None
    s = skill_str.strip()
    key = s.lower()
    
    # Kiểm tra từ rác
    if any(re.search(pat, key) for pat in EXCLUDE_PATTERNS):
        return None
        
    # Trực tiếp trong từ điển
    if key in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[key]
        
    # Chấp nhận các thuật ngữ kỹ thuật ASCII ngắn (tiếng Anh) hợp lệ
    if re.match(r'^[a-zA-Z0-9#\+\.\/\-_ ]{2,25}$', s) and not any(ord(c) > 127 for c in s):
        # Tránh các từ tiếng Anh quá chung chung
        if key not in {'other', 'another', 'etc', 'plus', 'good', 'well', 'basic', 'skill', 'tools'}:
            return s.title() if len(s) <= 15 else s
            
    return None


# ==============================================================================
# KỸ NĂNG CÔNG NGHỆ vs THẺ NGÀNH (đồng bộ với notebook 02, Bước 4)
# ==============================================================================
# required_skills_raw của TopCV/VietnamWorks trộn lẫn kỹ năng công nghệ, thẻ ngành/chức danh/ngoại ngữ và rác
# (phúc lợi, kinh nghiệm...). Kỹ năng ➔ `required_skills`, thẻ ➔ `job_tags`, rác ➔ loại bỏ.

# 2. Khái niệm hay gặp trong thẻ của sàn + công cụ game / 3D (phần "extra" của skills.yaml)
TECH_EXTRA = alias_map(_SKILLS["extra"])
TECH_LOOKUP = {**CANONICAL_SKILL_MAP, **TECH_EXTRA}

# 3. Khóa quá mơ hồ khi quét VĂN BẢN TỰ DO (vd 'go' trong "go to market", 'cv' trong "gửi CV", 'ml' viết tắt)
#    ➔ chỉ chấp nhận chúng khi xuất hiện như một THẺ rõ ràng, không quét từ mô tả.
_RULES = load_dictionary("skill_rules")   # configs/dictionaries/skill_rules.yaml
AMBIGUOUS_FREE_TEXT_KEYS = set(_RULES["ambiguous_free_text_keys"])

# 4. Mẫu nhận diện thẻ RÁC (phúc lợi, kinh nghiệm, học vấn, nhân thân...)
JUNK_PATTERN = re.compile("|".join(_RULES["junk_tag_patterns"]), re.IGNORECASE)

# 5. Regex quét kỹ năng trong văn bản. Dùng lookaround thay cho \b để nhận đúng C++, C#, .NET, CI/CD
TECH_PATTERNS = [
    (re.compile(r'(?<![\w+#.])' + re.escape(key) + r'(?![\w+#])'), canonical)
    for key, canonical in TECH_LOOKUP.items() if key not in AMBIGUOUS_FREE_TEXT_KEYS
]


def classify_tag(tag):
    """Phân loại một thẻ thô: ('skill', tên chuẩn) | ('tag', tên giữ nguyên) | ('junk', None)."""
    key = re.sub(r'\s+', ' ', tag).strip().lower()
    if key in TECH_LOOKUP:
        return 'skill', TECH_LOOKUP[key]
    if JUNK_PATTERN.search(key):
        return 'junk', None
    return 'tag', re.sub(r'\s+', ' ', tag).strip()


def extract_skills_and_tags(row):
    skills, tags, seen_s, seen_t = [], [], set(), set()

    # (a) Tách chuỗi thẻ thô. KHÔNG tách theo dấu "/" để giữ nguyên CI/CD, A/B Testing
    for part in re.split(r'[,;|•\n]', str(row.get('required_skills_raw', ''))):
        item = part.strip()
        if len(item) <= 1 or len(item) > 60:
            continue
        kind, name = classify_tag(item)
        if kind == 'skill' and name.lower() not in seen_s:
            seen_s.add(name.lower()); skills.append(name)
        elif kind == 'tag' and name.lower() not in seen_t:
            seen_t.add(name.lower()); tags.append(name)

    # (b) Bổ sung kỹ năng công nghệ quét từ mô tả JD
    desc = str(row.get('description_clean', '')).lower()
    for pattern, canonical in TECH_PATTERNS:
        if canonical.lower() not in seen_s and pattern.search(desc):
            seen_s.add(canonical.lower()); skills.append(canonical)
    return skills, tags


def extract_skills_from_text(text: str) -> List[str]:
    """Bóc tách kỹ năng công nghệ chuẩn hóa từ văn bản tự do (mô tả JD / nội dung CV)."""
    if not text:
        return []
    text_lower = str(text).lower()
    found, seen = [], set()
    for pattern, canonical in TECH_PATTERNS:
        if canonical.lower() not in seen and pattern.search(text_lower):
            seen.add(canonical.lower())
            found.append(canonical)
    return found


def normalize_user_skills(skills) -> List[str]:
    """Chuẩn hóa kỹ năng người dùng nhập tay: 'reactjs' ➔ 'React', 'k8s' ➔ 'Kubernetes'."""
    return [TECH_LOOKUP.get(str(s).strip().lower(), str(s).strip()) for s in (skills or []) if str(s).strip()]


# Nhóm kỹ năng THAY THẾ ĐƯỢC cho nhau (đồng bộ với notebook 05, mục 4.1): biết một kỹ năng trong nhóm thì học
# kỹ năng còn lại nhanh. Viết tay (không dùng đồng xuất hiện) vì kỹ năng hay đi cùng nhau (Python + SQL)
# chưa chắc thay thế được nhau. Tên phải là tên chuẩn của TECH_LOOKUP.
SKILL_GROUPS = [list(g) for g in load_dictionary("skill_groups")["groups"]]   # configs/dictionaries/skill_groups.yaml
RELATED_SKILLS: Dict[str, Set[str]] = {}
for _group in SKILL_GROUPS:
    for _a in _group:
        RELATED_SKILLS.setdefault(_a.lower(), set()).update(b.lower() for b in _group if b != _a)


def split_skill_match(user_skills, job_required_skills) -> Tuple[List[str], List[str], List[str]]:
    """Chia kỹ năng job yêu cầu thành 3 nhóm: khớp chính xác / gần nhau (bạn có kỹ năng cùng nhóm) / còn thiếu."""
    user_set = {str(s).lower() for s in (user_skills or []) if s and str(s).lower() != 'nan'}
    matched, related, missing = [], [], []
    for s in job_required_skills or []:
        if not s or str(s).lower() == 'nan':
            continue
        key = str(s).lower()
        if key in user_set:
            matched.append(s)
        elif RELATED_SKILLS.get(key, set()) & user_set:
            related.append(s)
        else:
            missing.append(s)
    return matched, related, missing
