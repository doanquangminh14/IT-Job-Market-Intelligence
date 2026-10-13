import re
from datetime import datetime
import pandas as pd
from .companies import clean_company_name

EXCHANGE_RATE_USD_VND = 25400

def clean_job_title(title):
    """Làm sạch tiêu đề việc làm, loại bỏ quảng cáo lương, địa điểm trong ngoặc vuông, từ ngữ tuyển gấp."""
    if not title or pd.isna(title):
        return ""
    t = str(title).strip()
    t = re.sub(r'\[.*?\]', '', t)  # Bỏ [HCM], [Hà Nội], [HOT]...
    noise_patterns = [
        r'(?:-|\|)?\s*(?:thu nhập|lương|up to|upto|lên đến|tới)\s*.*$',
        r'(?:-|\|)?\s*(?:hấp dẫn|deal|thỏa thuận|cạnh tranh)\s*$',
        r'(?:-|\|)?\s*(?:tại|ở)\s+(?:hà nội|hcm|đà nẵng|hồ chí minh).*$',
        r'^\s*(?:tuyển gấp|tuyển dụng|gấp:?)\s*',
        r'\(hà nội\)|\(hcm\)|\(hồ chí minh\)|\(đà nẵng\)',
    ]
    for p in noise_patterns:
        t = re.sub(p, '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip(' -|/,:;')
    return t.title() if len(t) <= 4 else t

def extract_seniority(title, exp_str=""):
    """Bóc tách cấp bậc chuyên môn: Intern, Fresher, Junior, Middle, Senior, Lead, Manager, Director."""
    t = (str(title) + " " + str(exp_str)).lower()
    if any(k in t for k in ['giám đốc', 'director', 'cto', 'cio', 'cpo']):
        return "Director"
    if any(k in t for k in ['trưởng phòng', 'manager', 'head of', 'quản lý']):
        return "Manager"
    if any(k in t for k in ['lead', 'leader', 'trưởng nhóm', 'techlead']):
        return "Lead"
    if any(k in t for k in ['thực tập', 'intern', 'trainee']):
        return "Intern"
    if any(k in t for k in ['fresher', 'mới tốt nghiệp']):
        return "Fresher"
    if any(k in t for k in ['senior', 'sr.', 'sr ', 'chuyên viên cao cấp']):
        return "Senior"
    if any(k in t for k in ['junior', 'jr.', 'jr ']):
        return "Junior"
    if any(k in t for k in ['middle', 'mid ', 'mid-']):
        return "Middle"
    return "Undetermined"

def parse_salary(raw_str):
    """
    Bóc tách mức lương đa định dạng (VNĐ, USD, khoảng, cận trên, thỏa thuận)
    và quy đổi chuẩn hóa về salary_min_vnd, salary_max_vnd.
    """
    res = {
        'salary_min': None, 'salary_max': None,
        'salary_currency': 'VND', 'salary_period': 'monthly',
        'salary_type': 'undisclosed',
        'salary_min_vnd': None, 'salary_max_vnd': None
    }
    if not raw_str or pd.isna(raw_str):
        return res
    s = str(raw_str).strip()
    s_lower = s.lower()

    if any(k in s_lower for k in ['thương lượng', 'cạnh tranh', 'thoa thuan', 'thỏa thuận', 'negotiable', 'deal']):
        res['salary_type'] = 'negotiable'
        return res

    period = 'yearly' if any(k in s_lower for k in ['/năm', 'năm', 'year']) else 'monthly'
    res['salary_period'] = period

    # 1. Định dạng USD
    has_usd = ('$' in s_lower or 'usd' in s_lower) and not ('tr' in s_lower or 'triệu' in s_lower)
    if has_usd:
        res['salary_currency'] = 'USD'
        nums = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?)', s)
        clean_nums = [float(n.replace(',', '')) for n in nums]
        if len(clean_nums) >= 2:
            vmin, vmax = clean_nums[0], clean_nums[1]
            if vmin <= 10 and vmax <= 10:
                res['salary_type'] = 'negotiable'
                return res
            if vmin > vmax:
                vmin, vmax = vmax, vmin
            res['salary_min'] = vmin
            res['salary_max'] = vmax
            mult = EXCHANGE_RATE_USD_VND if period == 'monthly' else (EXCHANGE_RATE_USD_VND / 12)
            res['salary_min_vnd'] = vmin * mult
            res['salary_max_vnd'] = vmax * mult
            res['salary_type'] = 'range'
            return res
        elif len(clean_nums) == 1:
            val = clean_nums[0]
            if val <= 10:
                res['salary_type'] = 'negotiable'
                return res
            mult = EXCHANGE_RATE_USD_VND if period == 'monthly' else (EXCHANGE_RATE_USD_VND / 12)
            res['salary_max'] = val
            res['salary_max_vnd'] = val * mult
            res['salary_type'] = 'max_only' if any(k in s_lower for k in ['tới', 'up to', 'dưới', '<']) else 'fixed'
            if res['salary_type'] == 'fixed':
                res['salary_min'] = val
                res['salary_min_vnd'] = val * mult
            return res

    # 2. Định dạng Triệu VNĐ (chứa 'tr', 'triệu', 'm')
    if any(k in s_lower for k in ['tr', 'triệu', 'm']):
        res['salary_currency'] = 'VND'
        nums = re.findall(r'(\d+(?:[.,]\d+)?)', s)
        clean_nums = [float(n.replace(',', '.')) for n in nums]
        if len(clean_nums) >= 2:
            vmin, vmax = clean_nums[0], clean_nums[1]
            if vmin > 1000: vmin /= 1_000_000
            if vmax > 1000: vmax /= 1_000_000
            if vmin > vmax: vmin, vmax = vmax, vmin
            res['salary_min'] = vmin * 1_000_000
            res['salary_max'] = vmax * 1_000_000
            res['salary_min_vnd'] = res['salary_min']
            res['salary_max_vnd'] = res['salary_max']
            res['salary_type'] = 'range'
            return res
        elif len(clean_nums) == 1:
            val = clean_nums[0]
            if val > 1000: val /= 1_000_000
            res['salary_max'] = val * 1_000_000
            res['salary_max_vnd'] = res['salary_max']
            res['salary_type'] = 'max_only' if any(k in s_lower for k in ['tới', 'up to', 'dưới', '<']) else 'fixed'
            if res['salary_type'] == 'fixed':
                res['salary_min'] = res['salary_max']
                res['salary_min_vnd'] = res['salary_max_vnd']
            return res

    # 3. Định dạng số nguyên gốc VNĐ (ví dụ 10,000,000 - 18,000,000)
    nums = re.findall(r'(\d+(?:,\d{3})*(?:\.\d+)?)', s)
    clean_nums = [float(n.replace(',', '')) for n in nums if float(n.replace(',', '')) > 100]
    if len(clean_nums) >= 2:
        vmin, vmax = clean_nums[0], clean_nums[1]
        if vmin > vmax: vmin, vmax = vmax, vmin
        res['salary_min'] = vmin
        res['salary_max'] = vmax
        res['salary_min_vnd'] = vmin
        res['salary_max_vnd'] = vmax
        res['salary_type'] = 'range'
        return res
    elif len(clean_nums) == 1:
        val = clean_nums[0]
        if val <= 1000:
            val_vnd = val * EXCHANGE_RATE_USD_VND
            res['salary_currency'] = 'USD'
            res['salary_max'] = val
            res['salary_max_vnd'] = val_vnd
            res['salary_type'] = 'fixed'
            res['salary_min'] = val
            res['salary_min_vnd'] = val_vnd
            return res
        res['salary_max'] = val
        res['salary_max_vnd'] = val
        res['salary_type'] = 'max_only' if any(k in s_lower for k in ['tới', 'up to', 'dưới', '<']) else 'fixed'
        if res['salary_type'] == 'fixed':
            res['salary_min'] = val
            res['salary_min_vnd'] = val
        return res

    return res

def parse_experience_years(exp_str):
    """Bóc tách số năm kinh nghiệm tối thiểu/tối đa."""
    if not exp_str or pd.isna(exp_str):
        return None, None
    s = str(exp_str).strip().lower()
    if any(k in s for k in ['không yêu cầu', 'chưa có kinh nghiệm', 'không cần']):
        return 0.0, 0.0
    m_range = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*năm', s)
    if m_range:
        return float(m_range.group(1)), float(m_range.group(2))
    m_min = re.search(r'(?:trên|từ|tối thiểu|\+)\s*(\d+(?:\.\d+)?)\s*năm|(\d+(?:\.\d+)?)\s*(?:\+|năm trở lên)', s)
    if m_min:
        v = m_min.group(1) or m_min.group(2)
        return float(v), None
    m_max = re.search(r'dưới\s*(\d+(?:\.\d+)?)\s*năm', s)
    if m_max:
        return 0.0, float(m_max.group(1))
    m_exact = re.search(r'(\d+(?:\.\d+)?)\s*năm', s)
    if m_exact:
        return float(m_exact.group(1)), float(m_exact.group(1))
    return None, None

def normalize_location_city(loc_str, wm_str=""):
    """Chuẩn hóa thành phố làm việc."""
    combined = (str(loc_str) + ' ' + str(wm_str)).lower()
    if any(k in combined for k in ['hồ chí minh', 'tp.hcm', 'hcm', 'sài gòn', 'saigon']):
        return 'Hồ Chí Minh'
    if any(k in combined for k in ['hà nội', 'ha noi', 'hn']):
        return 'Hà Nội'
    if any(k in combined for k in ['đà nẵng', 'da nang']):
        return 'Đà Nẵng'
    if any(k in combined for k in ['hải phòng', 'hai phong']):
        return 'Hải Phòng'
    if any(k in combined for k in ['cần thơ', 'can tho']):
        return 'Cần Thơ'
    return 'Khác'

def normalize_education(edu_str):
    """Chuẩn hóa trình độ học vấn yêu cầu."""
    if not edu_str or pd.isna(edu_str):
        return "Không yêu cầu"
    s = str(edu_str).strip().lower()
    if any(k in s for k in ['đại học', 'cử nhân', 'bachelor']):
        return "Đại học"
    if any(k in s for k in ['cao đẳng', 'college']):
        return "Cao đẳng"
    if any(k in s for k in ['thạc sĩ', 'master']):
        return "Thạc sĩ"
    if any(k in s for k in ['tiến sĩ', 'phd']):
        return "Tiến sĩ"
    if any(k in s for k in ['trung cấp', 'chứng chỉ']):
        return "Trung cấp / Chứng chỉ"
    return "Không yêu cầu"

def normalize_work_mode(mode_str, loc_str=""):
    """Chuẩn hóa hình thức làm việc: Onsite, Hybrid, Remote."""
    combined = (str(mode_str) + ' ' + str(loc_str)).lower()
    if any(k in combined for k in ['remote', 'từ xa', 'làm việc từ xa']):
        return "Remote"
    if any(k in combined for k in ['hybrid', 'linh hoạt']):
        return "Hybrid"
    return "Onsite"

def clean_date_str(val):
    """Làm sạch chuỗi thời gian, chuyển chuỗi rỗng thành None để tương thích với PostgreSQL TIMESTAMPTZ."""
    if not val or pd.isna(val):
        return None
    s = str(val).strip()
    return s if len(s) >= 8 else None

def transform_jobs(bronze_data, conn=None):
    """
    Chuyển đổi dữ liệu Bronze thành danh sách các bản ghi chuẩn hóa của bảng jobs.
    Đối chiếu company_id từ bảng companies trong database, khử trùng lặp chéo sàn,
    và xác định is_active hoàn toàn dựa trên deadline.
    """
    df_merged = bronze_data["df_merged"]

    # 1. Lấy mapping company_id từ PostgreSQL để đảm bảo toàn vẹn khóa ngoại 100%
    comp_map = {}
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute("SELECT lower(company_name_normalized), company_id FROM companies;")
            comp_map = {r[0]: r[1] for r in cur.fetchall()}

    now_iso = datetime.now().isoformat()
    today_str = datetime.now().strftime('%Y-%m-%d')
    source_id_map = {'topcv': 1, 'topdev': 2, 'vietnamworks': 3, 'itviec': 4}

    print(f"-> [Transformer: jobs] Làm sạch và chuẩn hóa {len(df_merged):,} tin việc làm...")
    job_records = []

    for idx, row in df_merged.iterrows():
        source = row.get('source', '')
        raw_comp = str(row.get('company_name_raw', '') or '').strip()
        norm_comp = clean_company_name(raw_comp).lower()
        comp_id = comp_map.get(norm_comp, None)
        if comp_id is None:
            # Fallback nếu chưa nạp companies vào DB (dự phòng)
            comp_id = 1

        title_raw = str(row.get('title_raw', '') or '').strip()
        title_norm = clean_job_title(title_raw)
        seniority = extract_seniority(title_raw, row.get('experience_raw', ''))

        sal_res = parse_salary(row.get('salary_raw', ''))
        e_min, e_max = parse_experience_years(row.get('experience_raw', ''))
        edu_lvl = normalize_education(row.get('education_raw', ''))
        city = normalize_location_city(row.get('location_raw', ''), row.get('work_mode_raw', ''))
        wm = normalize_work_mode(row.get('work_mode_raw', ''), row.get('location_raw', ''))

        # Trạng thái còn hạn: dựa hoàn toàn vào deadline
        deadline_str = str(row.get('deadline_raw', '') or '').strip()
        is_act = True
        if deadline_str:
            is_act = (deadline_str[:10] >= today_str)

        job_id = idx + 1

        job_records.append({
            'job_id': job_id,
            'primary_source_id': source_id_map.get(source, 1),
            'company_id': comp_id,
            'canonical_job_id': None,
            'title_raw': title_raw,
            'title_normalized': title_norm,
            'seniority_level': seniority,
            'location_raw': row.get('location_raw', ''),
            'city': city,
            'work_mode_raw': row.get('work_mode_raw', ''),
            'work_mode': wm,
            'employment_type': 'Full-time',
            'working_time_raw': row.get('working_time_raw', ''),
            'salary_raw': row.get('salary_raw', ''),
            'salary_min': sal_res['salary_min'],
            'salary_max': sal_res['salary_max'],
            'salary_currency': sal_res['salary_currency'],
            'salary_period': sal_res['salary_period'],
            'salary_type': sal_res['salary_type'],
            'salary_min_vnd': sal_res['salary_min_vnd'],
            'salary_max_vnd': sal_res['salary_max_vnd'],
            'experience_raw': row.get('experience_raw', ''),
            'experience_min_years': e_min,
            'experience_max_years': e_max,
            'education_raw': row.get('education_raw', ''),
            'education_level': edu_lvl,
            'published_at': clean_date_str(row.get('published_at_raw') or row.get('posted_at_raw')),
            'updated_at_source': clean_date_str(row.get('updated_at_raw')),
            'deadline': clean_date_str(deadline_str),
            'is_active': is_act
        })

    # Phát hiện tin trùng lặp chéo sàn (Cross-portal Duplicate Detection)
    # Gom nhóm theo (company_id, lower(title_normalized))
    dedup_groups = {}
    cross_dup_count = 0
    for r in job_records:
        key = (r['company_id'], r['title_normalized'].lower())
        if key not in dedup_groups:
            dedup_groups[key] = r['job_id']
        else:
            # Gán canonical_job_id trỏ về tin xuất hiện đầu tiên
            r['canonical_job_id'] = dedup_groups[key]
            cross_dup_count += 1

    active_count = sum(1 for r in job_records if r['is_active'])
    print(f"   [Transformer: jobs] Đã làm sạch thành công: {len(job_records):,} tin việc làm.")
    print(f"   [Transformer: jobs] Phát hiện {cross_dup_count} tin đăng chéo sàn (đã gán canonical_job_id).")
    print(f"   [Transformer: jobs] Tỷ lệ tin còn hạn: {active_count:,} / {len(job_records)} ({active_count/len(job_records)*100:.1f}%).")
    return job_records
