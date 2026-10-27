import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.data_cleaning.skill_canonical import (
    CANONICAL_SKILL_MAP,
    EXCLUDE_PATTERNS,
    normalize_skill_name,
    extract_skills_from_text
)

EXCHANGE_RATE_USD = 25400

class JobCleaner:
    """
    Pipeline làm sạch và chuẩn hóa dữ liệu tin tuyển dụng IT từ Bronze sang Silver/Gold.
    """

    @staticmethod
    def clean_company_name(name: Any) -> str:
        """Chuẩn hóa tên công ty, loại bỏ tiền tố/hậu tố pháp lý (Công ty TNHH, CP, JSC...)."""
        if not name or pd.isna(name):
            return "Không rõ"
        s = str(name).strip()
        s = re.sub(r'^(?:công ty|cty)?\s*(?:tnhh mtv|tnhh|cổ phần|cp|tập đoàn)\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'[\s,\-]+(?:tnhh|cổ phần|jsc|llc|inc|corp|co\.,?\s*ltd\.?|ltd\.?)$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'[\s,\-]+(?:chi nhánh|vietnam|việt nam)$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+', ' ', s).strip(' -,/:;')
        return s if s else str(name).strip()

    @staticmethod
    def clean_job_title(title: Any) -> str:
        """Làm sạch chức danh tuyển dụng, loại bỏ tag địa điểm thừa, giật tít, mức lương đính kèm."""
        if not title or pd.isna(title):
            return ""
        t = str(title).strip()
        t = re.sub(r'\[.*?\]', '', t)
        t = re.sub(r'\((?:hà nội|hcm|đà nẵng|hồ chí minh|toàn quốc)\)', '', t, flags=re.IGNORECASE)
        t = re.sub(r'^\s*(?:tuyển gấp|tuyển dụng|gấp:?)\s*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'(?:-|\|)?\s*(?:thu nhập|lương|up to|upto|lên đến|tới)\s*.*$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'(?:-|\|)?\s*(?:hấp dẫn|deal|thỏa thuận|cạnh tranh)\s*$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s+', ' ', t).strip(' -|/,:;')
        return t

    @staticmethod
    def clean_html_description(text: Any) -> str:
        """Loại bỏ thẻ HTML, giải mã thực thể HTML và chuẩn hóa định dạng dòng mô tả."""
        if not text or pd.isna(text):
            return ""
        s = str(text)
        s = s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        s = re.sub(r'<(?:br|/p|/li|/div|/h\d)[^>]*>', '\n', s, flags=re.IGNORECASE)
        s = re.sub(r'<[^>]+>', ' ', s)
        s = re.sub(r'^[ \t]*[-\*\+\–•][ \t]*', '- ', s, flags=re.MULTILINE)
        lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')]
        return '\n'.join([l for l in lines if l])

    @staticmethod
    def extract_and_normalize_skills(row: pd.Series) -> List[str]:
        """Loại bỏ các tag phúc lợi, nhân thân và chuẩn hóa tên kỹ năng về dạng chuẩn."""
        raw_skills = str(row.get('required_skills_raw', ''))
        desc = str(row.get('description_clean', '')).lower()
        
        clean_skills = []
        seen = set()
        
        # 1. Lọc từ các tag thô
        for p in re.split(r'[,;|/•\n]', raw_skills):
            item = re.sub(r'\s+', ' ', p).strip()
            if not item or len(item) <= 1 or len(item) > 40:
                continue
            if any(re.search(pat, item.lower()) for pat in EXCLUDE_PATTERNS):
                continue
            norm_name = normalize_skill_name(item)
            if norm_name and norm_name.lower() not in seen:
                seen.add(norm_name.lower())
                clean_skills.append(norm_name)
                
        # 2. Bổ sung kỹ năng từ văn bản mô tả JD
        for key_tech, canonical_name in CANONICAL_SKILL_MAP.items():
            if re.search(r'\b' + re.escape(key_tech) + r'\b', desc):
                if canonical_name.lower() not in seen:
                    seen.add(canonical_name.lower())
                    clean_skills.append(canonical_name)
                    
        return clean_skills

    @staticmethod
    def extract_preferred_skills(row: pd.Series) -> List[str]:
        """Trích xuất kỹ năng ưu tiên (nice-to-have)."""
        raw_pref = row.get('preferred_skills_raw')
        if raw_pref and pd.notnull(raw_pref) and str(raw_pref).strip():
            skills = [normalize_skill_name(s) for s in str(raw_pref).split(',') if s.strip()]
            return [s for s in skills if s]
        
        desc = str(row.get('description_clean', '')).lower()
        pref_section = ""
        m = re.search(r'(?:ưu tiên|điểm cộng|nice to have|plus|yêu cầu khác)[\s:]*([^\.\n]+)', desc)
        if m:
            pref_section = m.group(1)
            
        found_skills = []
        req_skills_lower = [k.lower() for k in (row.get('required_skills') or [])]
        for key_tech, canonical_name in CANONICAL_SKILL_MAP.items():
            if re.search(r'\b' + re.escape(key_tech) + r'\b', pref_section):
                if canonical_name.lower() not in req_skills_lower and canonical_name not in found_skills:
                    found_skills.append(canonical_name)
        return found_skills

    @staticmethod
    def parse_experience_range(exp_str: Any) -> Tuple[Optional[float], Optional[float]]:
        """Phân tích số năm kinh nghiệm tối thiểu và tối đa."""
        if not exp_str or pd.isna(exp_str):
            return None, None
        s = str(exp_str).strip().lower()
        if any(k in s for k in ['không yêu cầu', 'chưa có kinh nghiệm', 'không cần', 'fresher', 'intern']):
            return 0.0, 0.0
        m_range = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*năm', s)
        if m_range:
            return float(m_range.group(1)), float(m_range.group(2))
        m_min = re.search(r'(?:trên|từ|tối thiểu|\+)\s*(\d+(?:\.\d+)?)\s*năm|(\d+(?:\.\d+)?)\s*(?:\+|năm trở lên)', s)
        if m_min:
            v = float(m_min.group(1) or m_min.group(2))
            return v, None
        m_max = re.search(r'dưới\s*(\d+(?:\.\d+)?)\s*năm', s)
        if m_max:
            return 0.0, float(m_max.group(1))
        m_month = re.search(r'(\d+)\s*tháng', s)
        if m_month:
            years = round(float(m_month.group(1)) / 12.0, 1)
            return years, years
        m_exact = re.search(r'(\d+(?:\.\d+)?)\s*năm', s)
        if m_exact:
            v = float(m_exact.group(1))
            return v, v
        return None, None

    @staticmethod
    def extract_city(loc_str: Any) -> str:
        """Phân loại địa điểm về các thành phố chuẩn."""
        if not loc_str or pd.isna(loc_str):
            return "Toàn quốc"
        s = str(loc_str).lower()
        if any(k in s for k in ['hồ chí minh', 'hcm', 'sài gòn', 'saigon', 'thủ đức']):
            return "Hồ Chí Minh"
        if any(k in s for k in ['hà nội', 'hn', 'cầu giấy', 'nam từ liêm', 'ba đình', 'đống đa']):
            return "Hà Nội"
        if any(k in s for k in ['đà nẵng', 'da nang']):
            return "Đà Nẵng"
        if any(k in s for k in ['cần thơ', 'hải phòng', 'bình dương', 'đồng nai']):
            return "Khác"
        return "Khác"

    @staticmethod
    def parse_salary_vnd(sal_str: Any, title_str: Any = "") -> Tuple[Optional[float], Optional[float]]:
        """Quy đổi mức lương sang đơn vị VND (xử lý USD, triệu VND, khoảng lương)."""
        # 1. Bổ trợ từ tiêu đề nếu tiêu đề chứa khoảng lương rõ ràng (vd: '15 - 20M', '15 - 20 triệu')
        if title_str and pd.notnull(title_str):
            m_title = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:m|tr|triệu|usd|\$)', str(title_str), re.I)
            if m_title:
                v1, v2 = float(m_title.group(1)), float(m_title.group(2))
                is_usd = '$' in str(title_str) or 'usd' in str(title_str).lower()
                mult = EXCHANGE_RATE_USD if is_usd else (1_000_000 if (v1 < 500 and v2 < 500) else 1)
                return min(v1, v2) * mult, max(v1, v2) * mult

        if not sal_str or pd.isna(sal_str):
            return None, None
        s = str(sal_str).strip().lower()
        if any(k in s for k in ['thương lượng', 'cạnh tranh', 'thoa thuan', 'thỏa thuận', 'negotiable', 'deal']):
            return None, None
            
        has_usd = ('$' in s or 'usd' in s) and not ('tr' in s or 'triệu' in s)
        nums = [float(n.replace(',', '')) for n in re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?)', s)]
        if not nums:
            return None, None
            
        if has_usd:
            nums = [n * EXCHANGE_RATE_USD for n in nums]
        else:
            if any(k in s for k in ['tr', 'triệu', 'trieu', 'm']) or any(n < 500 for n in nums):
                nums = [n * 1_000_000 for n in nums]
                
        if len(nums) >= 2:
            return min(nums[0], nums[1]), max(nums[0], nums[1])
        elif len(nums) == 1:
            val = nums[0]
            if any(k in s for k in ['tới', 'up to', 'dưới', '<', 'tối đa']):
                return None, val
            elif any(k in s for k in ['từ', 'trên', '>=', 'tối thiểu', 'from', '>']):
                return val, None
            return val, val
        return None, None

    @staticmethod
    def clean_employment_type(emp_str: Any, title_str: str = "") -> str:
        """Chuẩn hóa loại hình làm việc: Full-time, Part-time, Intern, Contract."""
        c = (str(emp_str) + " " + str(title_str)).lower()
        if any(k in c for k in ['intern', 'thực tập', 'trainee']):
            return 'Intern'
        if any(k in c for k in ['part-time', 'bán thời gian', 'parttime']):
            return 'Part-time'
        if any(k in c for k in ['freelance', 'hợp đồng', 'contract']):
            return 'Contract'
        return 'Full-time'

    @staticmethod
    def clean_work_mode(mode_str: Any, loc_str: str = "") -> str:
        """Chuẩn hóa chế độ làm việc: Remote, Hybrid, Onsite."""
        c = (str(mode_str) + ' ' + str(loc_str)).lower()
        if any(k in c for k in ['remote', 'từ xa', 'làm việc từ xa']):
            return 'Remote'
        if any(k in c for k in ['hybrid', 'linh hoạt']):
            return 'Hybrid'
        return 'Onsite'

    @staticmethod
    def parse_deadline(d_str: Any) -> Tuple[Optional[str], bool]:
        """Chuẩn hóa hạn nộp hồ sơ và cờ is_active."""
        if not d_str or pd.isna(d_str):
            return None, True
        s = str(d_str).strip()
        try:
            if 'T' in s:
                dt = datetime.fromisoformat(s)
            else:
                dt = datetime.strptime(s[:10], '%Y-%m-%d')
            d_formatted = dt.strftime('%Y-%m-%d')
            is_act = dt.date() >= datetime.now().date()
            return d_formatted, is_act
        except Exception:
            return s[:10], True

    @staticmethod
    def load_logo_map() -> Tuple[Dict[str, str], Dict[str, str]]:
        """Quét các file listings raw để tạo bản đồ logo theo job_url và company_name."""
        import glob
        url_to_logo = {}
        comp_to_logo = {}
        for p in glob.glob('data/raw/*/listings/*/*.json'):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                for it in items:
                    url = (it.get('job_url') or it.get('detail_url') or it.get('url') or '').strip()
                    logo = (it.get('company_logo_url') or it.get('companyLogo') or it.get('logo') or it.get('image_logo') or '').strip()
                    comp = (it.get('company_name') or it.get('company_name_raw') or it.get('company') or '').strip().lower()
                    if logo:
                        if url and url not in url_to_logo:
                            url_to_logo[url] = logo
                        if comp and comp not in comp_to_logo:
                            comp_to_logo[comp] = logo
            except Exception:
                continue
        return url_to_logo, comp_to_logo

    def process_records(self, raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Thực thi toàn bộ pipeline làm sạch và chuyển hóa danh sách bản ghi thô."""
        processed = []
        for item in raw_records:
            desc_parts = [item.get(k, '') for k in ['overview_raw', 'responsibilities_raw', 'requirements_raw', 'benefits_raw'] if item.get(k)]
            processed.append({
                'job_id': item.get('detail_id') or f"{item.get('source', '')}_{item.get('source_job_id', '')}",
                'company_name_raw': (item.get('company_name_raw') or '').strip(),
                'title_raw': (item.get('title_raw') or '').strip(),
                'description_raw': '\n\n'.join(desc_parts),
                'required_skills_raw': (item.get('required_skills_raw') or '').strip(),
                'preferred_skills_raw': (item.get('preferred_skills_raw') or '').strip(),
                'experience_raw': (item.get('experience_raw') or '').strip(),
                'location_raw': (item.get('location_raw') or item.get('company_location_raw') or '').strip(),
                'salary_raw': (item.get('salary_raw') or '').strip(),
                'employment_type_raw': (item.get('employment_type_raw') or '').strip(),
                'work_mode_raw': (item.get('work_mode_raw') or '').strip(),
                'deadline_raw': (item.get('deadline_raw') or '').strip(),
                'job_url': (item.get('job_url') or '').strip()
            })

        jobs = pd.DataFrame(processed)
        
        # 1. Company Name & Title
        jobs['company_name'] = jobs['company_name_raw'].apply(self.clean_company_name)
        jobs['title'] = jobs['title_raw'].apply(self.clean_job_title)
        
        # 1b. Company Logo
        url_to_logo, comp_to_logo = self.load_logo_map()
        raw_logos = jobs.apply(
            lambda r: url_to_logo.get(r['job_url']) or comp_to_logo.get(r['company_name'].lower(), '') or '',
            axis=1
        )
        jobs['company_logo_url'] = raw_logos.apply(
            lambda x: re.sub(r'^https?://cdn-new\.topcv\.vn/unsafe/(https?://)', r'\1', str(x)).strip() if x else ''
        )
        
        # 2. Description
        jobs['description_clean'] = jobs['description_raw'].apply(self.clean_html_description)
        
        # 3. Skills
        jobs['required_skills'] = jobs.apply(self.extract_and_normalize_skills, axis=1)
        jobs['preferred_skills'] = jobs.apply(self.extract_preferred_skills, axis=1)
        
        # 4. Experience
        exp_res = jobs['experience_raw'].apply(self.parse_experience_range)
        jobs['experience_min'] = exp_res.apply(lambda x: x[0])
        jobs['experience_max'] = exp_res.apply(lambda x: x[1])
        
        # 5. Location & City
        jobs['location'] = jobs['location_raw'].apply(lambda x: re.sub(r'\s+', ' ', str(x)).strip() if pd.notnull(x) else "")
        jobs['city'] = jobs['location'].apply(self.extract_city)
        
        # 6. Salary
        sal_res = jobs.apply(lambda r: self.parse_salary_vnd(r['salary_raw'], r['title_raw']), axis=1)
        jobs['salary_min'] = sal_res.apply(lambda x: x[0])
        jobs['salary_max'] = sal_res.apply(lambda x: x[1])
        
        # 7. Employment Type & Work Mode
        jobs['employment_type'] = jobs.apply(lambda r: self.clean_employment_type(r['employment_type_raw'], r['title']), axis=1)
        jobs['work_mode'] = jobs.apply(lambda r: self.clean_work_mode(r['work_mode_raw'], r['location']), axis=1)
        
        # 8. Deadline & Active
        dl_res = jobs['deadline_raw'].apply(self.parse_deadline)
        jobs['deadline'] = dl_res.apply(lambda x: x[0])
        jobs['is_active'] = dl_res.apply(lambda x: x[1])
        
        # 9. Khử trùng lặp theo (company_name, title)
        jobs['desc_len'] = jobs['description_clean'].str.len()
        jobs = jobs.sort_values(by=['company_name', 'title', 'deadline', 'desc_len'], ascending=[True, True, False, False])
        jobs = jobs.drop_duplicates(subset=['company_name', 'title'], keep='first')
        jobs = jobs.drop(columns=['desc_len'])
        
        final_columns = [
            'job_id', 'company_name', 'title', 'description_clean', 'required_skills', 'preferred_skills',
            'experience_min', 'experience_max', 'location', 'city', 'salary_min', 'salary_max',
            'employment_type', 'work_mode', 'deadline', 'is_active', 'job_url', 'company_logo_url'
        ]
        return jobs[final_columns]

    def clean_and_save(self, input_bronze_path: str, output_csv_path: str, output_parquet_path: Optional[str] = None) -> pd.DataFrame:
        """Đọc file Bronze JSON, làm sạch và lưu ra file CSV / Parquet."""
        print(f" Đang đọc dữ liệu Bronze từ: {input_bronze_path}")
        with open(input_bronze_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        print(f" Tổng số bản ghi Bronze: {len(raw_data):,}")
        df_clean = self.process_records(raw_data)
        
        # Format list to comma-separated string for CSV export
        df_export = df_clean.copy()
        df_export['required_skills'] = df_export['required_skills'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
        df_export['preferred_skills'] = df_export['preferred_skills'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
        
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        df_export.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f" Đã lưu {len(df_export):,} việc làm sạch ra: {output_csv_path}")
        
        if output_parquet_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_parquet_path)), exist_ok=True)
            df_export.to_parquet(output_parquet_path, index=False)
            print(f" Đã lưu Parquet ra: {output_parquet_path}")
            
        return df_clean

if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    bronze_path = os.path.join(PROJECT_ROOT, "data", "bronze", "bronze_details_valid.json")
    csv_path = os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.csv")
    parquet_path = os.path.join(PROJECT_ROOT, "data", "silver", "jobs_cleaned.parquet")
    
    cleaner = JobCleaner()
    cleaner.clean_and_save(bronze_path, csv_path, parquet_path)
