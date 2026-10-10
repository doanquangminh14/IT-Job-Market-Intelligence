import os
import sys
import re

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

import yaml
from bs4 import BeautifulSoup
from curl_cffi import requests

# Đảm bảo đường dẫn gốc của project luôn nằm trong sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crawlers.base import BaseCrawler
from src.schemas.job import JobListingRaw, JobDetailRaw


def clean_html(raw_html: str) -> str:
    """Loại bỏ các thẻ HTML và định dạng text gọn gàng"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def fix_encoding(text: Any) -> str:
    """Khắc phục lỗi mã hóa Unicode escape dạng double-encoded UTF-8 nếu có"""
    if not text:
        return ""
    try:
        return str(text).encode('latin1').decode('utf-8')
    except Exception:
        return str(text)


class TopDevCrawler(BaseCrawler):
    def __init__(self, config_path: str = "configs/sources.yaml"):
        # 1. Đọc file cấu hình sources.yaml
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            topdev_cfg = all_configs.get("sources", {}).get("topdev", {})

        super().__init__(topdev_cfg)

        # 2. Tham số cào & đường dẫn
        self.listing_url_template = self.config.get(
            "listing_url",
            "https://topdev.vn/viec-lam/tim-kiem?job_categories_ids=2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2C11%2C12%2C13%2C67&page={page}"
        )
        pagination = self.config.get("pagination", {})
        self.start_page = int(pagination.get("start_page", 1))
        self.max_pages = int(pagination.get("max_pages", 20))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 1.2))
        self.delay_max = float(rate_limit.get("delay_max", 2.0))
        self.timeout = int(rate_limit.get("timeout", 20))

        # Cấu hình retry & backoff: giãn cách 15s, 30s, 45s
        self.retry_delays = [15, 30, 45]
        self.max_retries = len(self.retry_delays)

        # 3. Cấu trúc thư mục lưu trữ JSON thuần túy theo ngày
        # data/raw/topdev/listings/YYYY-MM-DD/
        # data/raw/topdev/details/YYYY-MM-DD/
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "topdev")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        # 4. Thiết lập Logging
        self.logger = self._setup_logger()

        # 5. Khởi tạo session giả lập trình duyệt Chrome
        self.session = requests.Session(impersonate="chrome124")

    def _setup_logger(self) -> logging.Logger:
        """Thiết lập logger ghi cả ra Terminal và File log trong thư mục details của ngày hôm nay"""
        logger = logging.getLogger("TopDevCrawler")
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        log_format = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [TopDev] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # File Handler ghi vào thư mục logs chung
        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "topdev.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        return logger

    def _get_next_tc_index(self) -> int:
        """
        Tìm số thứ tự tiếp theo cho file TCxxx.json trong thư mục details của ngày hôm nay.
        Ví dụ: nếu đã có TC001.json, TC002.json -> trả về 3.
        """
        if not os.path.exists(self.details_dir):
            return 1
        existing_files = [f for f in os.listdir(self.details_dir) if f.startswith("TC") and f.endswith(".json")]
        if not existing_files:
            return 1

        max_idx = 0
        for f in existing_files:
            m = re.match(r"^TC(\d+)\.json$", f)
            if m:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
        return max_idx + 1

    def _get_all_crawled_job_ids(self) -> Set[str]:
        """
        Quét tất cả các file TCxxx.json trong thư mục details (cả hôm nay và các ngày trước)
        để lấy danh sách các source_job_id đã cào thành công, tránh cào lại.
        Mỗi file TCxxx.json chứa một mảng [ {...}, {...} ] gồm nhiều jobs.
        """
        crawled_ids: Set[str] = set()
        details_root = os.path.join(self.base_raw_dir, "details")
        if not os.path.exists(details_root):
            return crawled_ids

        for date_folder in os.listdir(details_root):
            folder_path = os.path.join(details_root, date_folder)
            if not os.path.isdir(folder_path):
                continue
            for file_name in os.listdir(folder_path):
                if file_name.startswith("TC") and file_name.endswith(".json"):
                    file_path = os.path.join(folder_path, file_name)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    jid = str(item.get("source_job_id", ""))
                                    if jid:
                                        crawled_ids.add(jid)
                            elif isinstance(data, dict):
                                jid = str(data.get("source_job_id", ""))
                                if jid:
                                    crawled_ids.add(jid)
                    except Exception:
                        continue
        return crawled_ids

    def _save_page_listing(self, page_num: int, items: List[Dict[str, Any]]) -> str:
        """Lưu danh sách job của một trang vào listings/YYYY-MM-DD/page_XXX.json"""
        file_name = f"page_{page_num:03d}.json"
        file_path = os.path.join(self.listings_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return file_path

    def _save_batch_details(self, file_path: str, details_list: List[Dict[str, Any]]) -> None:
        """Lưu toàn bộ danh sách job chi tiết của lần cào này vào duy nhất 1 file TCxxx.json"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(details_list, f, ensure_ascii=False, indent=2)

    def fetch_job_list_page(self, page: int) -> List[Dict[str, Any]]:
        """
        Cào danh sách job từ trang tìm kiếm TopDev.
        Trích xuất đầy đủ thông tin: title, company, logo, lương, địa điểm, kinh nghiệm
        ngay từ bước listing để các job chưa cào chi tiết (pending) vẫn có dữ liệu hoàn chỉnh.
        """
        url = self.listing_url_template.format(page=page)
        self.logger.info(f"Đang quét danh sách tại trang {page}: {url}")

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                self.logger.warning(f"Trang {page} trả về HTTP status {resp.status_code}")
                return []

            # Trích xuất payload Next.js RSC
            pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', resp.text, re.DOTALL)
            decoded = "".join(pushes).encode('utf-8').decode('unicode_escape', errors='ignore')

            found_items = []
            seen = set()

            # 1. Trích xuất các object job đầy đủ từ Next.js payload bằng raw_decode
            decoder = json.JSONDecoder()
            pattern = re.compile(r'\{"id":(\d{5,8}),"title":"')

            for m in pattern.finditer(decoded):
                start = m.start()
                try:
                    obj, _ = decoder.raw_decode(decoded[start:])
                    if isinstance(obj, dict) and "id" in obj and "title" in obj and "company" in obj:
                        jid = str(obj.get("id"))
                        if jid in seen:
                            continue
                        seen.add(jid)

                        title = fix_encoding(obj.get("title", ""))
                        slug = obj.get("slug", "")
                        detail_url = obj.get("detail_url") or f"https://topdev.vn/viec-lam/{slug}-{jid}"

                        comp = obj.get("company", {})
                        comp_name = fix_encoding(comp.get("display_name", ""))
                        comp_logo = comp.get("image_logo", "") or ""

                        addr = obj.get("addresses", {})
                        loc = fix_encoding(addr.get("sort_addresses") or addr.get("address_region_list") or "")
                        loc = loc.strip(" -")

                        sal_obj = obj.get("salary", {})
                        if sal_obj.get("is_negotiable") == "1":
                            salary = "Thương lượng"
                        elif sal_obj.get("min") and sal_obj.get("max") and (sal_obj.get("min") > 0 or sal_obj.get("max") > 0):
                            currency = sal_obj.get("currency", "VND")
                            salary = f"{sal_obj['min']:,} - {sal_obj['max']:,} {currency}"
                        elif sal_obj.get("value"):
                            salary = fix_encoding(sal_obj.get("value"))
                        else:
                            salary = "Thương lượng"

                        exp = fix_encoding(obj.get("experiences_str", ""))
                        skills = fix_encoding(obj.get("skills_str") or ", ".join(obj.get("skills_arr", []) if isinstance(obj.get("skills_arr"), list) else []))
                        posted_at = obj.get("published", {}).get("date") or obj.get("created_at") or ""

                        found_items.append({
                            "source": "topdev",
                            "source_job_id": jid,
                            "job_url": detail_url,
                            "company_logo_url": comp_logo,
                            "title_raw": title,
                            "company_name_raw": comp_name,
                            "location_raw": loc,
                            "salary_raw": salary,
                            "experience_raw": exp,
                            "skills_raw": skills,
                            "posted_at_raw": str(posted_at),
                            "crawled_at": datetime.now().isoformat(),
                            "detail_status": "pending",
                            "detail_attempts": 0,
                            "detail_http_status": None,
                            "detail_error": "",
                            "detail_file": "",
                            "detail_crawled_at": None
                        })
                except Exception:
                    continue

            # 2. Fallback: Nếu còn link nào chưa được parse qua object, bổ sung qua regex slug
            matches = re.findall(r'/viec-lam/([a-zA-Z0-9\-_]+-(\d{5,8}))', decoded)
            for slug, jid in matches:
                if jid not in seen:
                    seen.add(jid)
                    found_items.append({
                        "source": "topdev",
                        "source_job_id": str(jid),
                        "job_url": f"https://topdev.vn/viec-lam/{slug}",
                        "company_logo_url": "",
                        "title_raw": slug,
                        "company_name_raw": "",
                        "location_raw": "",
                        "salary_raw": "",
                        "experience_raw": "",
                        "skills_raw": "",
                        "posted_at_raw": "",
                        "crawled_at": datetime.now().isoformat(),
                        "detail_status": "pending",
                        "detail_attempts": 0,
                        "detail_http_status": None,
                        "detail_error": "",
                        "detail_file": "",
                        "detail_crawled_at": None
                    })

            self.logger.info(f"-> Trang {page} tìm thấy {len(found_items)} jobs với đầy đủ thông tin tóm tắt.")
            return found_items

        except Exception as e:
            self.logger.error(f"Lỗi khi quét danh sách trang {page}: {e}")
            return []

    def fetch_job_detail_with_retry(
        self,
        job_item: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Cào chi tiết một job cụ thể với cơ chế Retry 3 lần:
        - Lần 1 lỗi: nghỉ 15s rồi thử lại
        - Lần 2 lỗi: nghỉ 30s rồi thử lại
        - Lần 3 lỗi: nghỉ 45s rồi thử lại
        Nếu vẫn lỗi -> đánh dấu detail_status='failed'
        """
        job_url = job_item["job_url"]
        job_id = str(job_item["source_job_id"])
        updated_listing = dict(job_item)

        last_error = ""
        last_status_code = None

        for attempt in range(1, self.max_retries + 1):
            updated_listing["detail_attempts"] = attempt
            try:
                self.logger.info(f"Đang tải chi tiết Job {job_id} (Lần thử {attempt}/{self.max_retries}): {job_url}")
                resp = self.session.get(job_url, timeout=self.timeout)
                last_status_code = resp.status_code
                updated_listing["detail_http_status"] = resp.status_code

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    ld_data = None
                    for s in soup.find_all("script", type="application/ld+json"):
                        try:
                            content = (s.string if s.string else s.text) or ""
                            d = json.loads(content)
                            if d.get("@type") == "JobPosting":
                                ld_data = d
                                break
                        except Exception:
                            continue

                    if not ld_data:
                        ld_data = {}

                    # 1. Title & Company
                    title = ld_data.get("title", "")
                    if not title:
                        h1 = soup.find("h1")
                        title = h1.get_text(strip=True) if h1 else ""

                    comp_data = ld_data.get("hiringOrganization") or {}
                    comp_name = comp_data.get("name", "")
                    comp_logo = comp_data.get("logo", "")
                    comp_url = comp_data.get("sameAs", "")

                    # 2. Header Grid: Location, Cấp bậc (Level), Kinh nghiệm (Experience)
                    location_raw = ""
                    level_raw = ""
                    experience_raw = ""

                    header_grid = soup.find("div", class_=lambda c: c and "grid-cols-2" in c and "md:gap-16" in c)
                    if header_grid:
                        items = [child.get_text(separator=" ", strip=True) for child in header_grid.children if child.name]
                        if len(items) >= 1:
                            location_raw = items[0]
                        if len(items) >= 2:
                            level_raw = items[1]
                        if len(items) >= 3:
                            experience_raw = items[2]

                    if not location_raw:
                        loc_data = ld_data.get("jobLocation") or {}
                        addr_data = loc_data.get("address") or {} if isinstance(loc_data, dict) else {}
                        location_raw = (
                            addr_data.get("addressLocality")
                            or addr_data.get("addressRegion")
                            or addr_data.get("streetAddress")
                            or ""
                        )

                    # 3. Work mode (Fulltime, Part-time, Remote, Hybrid, Onsite)
                    work_mode_raw = ""
                    full_text = soup.get_text(separator=" ", strip=True)
                    for wm in ["Fulltime", "Full-time", "Part-time", "Parttime", "Remote", "Hybrid", "Onsite"]:
                        if re.search(r'\b' + wm + r'\b', full_text, re.IGNORECASE):
                            work_mode_raw = wm
                            break

                    # 4. Salary chuẩn hóa
                    salary_raw = "Thương lượng"
                    pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', resp.text, re.DOTALL)
                    decoded = "".join(pushes).encode('utf-8').decode('unicode_escape', errors='ignore')

                    sal_match = re.search(r'"salary":\s*(\{[^}]+\})', decoded)
                    if sal_match:
                        try:
                            sal_obj = json.loads(sal_match.group(1))
                            if sal_obj.get("is_negotiable") == "1":
                                salary_raw = "Thương lượng"
                            elif sal_obj.get("min") and sal_obj.get("max") and (sal_obj.get("min") > 0 or sal_obj.get("max") > 0):
                                currency = sal_obj.get("currency", "VND")
                                salary_raw = f"{sal_obj['min']:,} - {sal_obj['max']:,} {currency}"
                            elif sal_obj.get("value") and "Th" in sal_obj.get("value"):
                                salary_raw = "Thương lượng"
                        except Exception:
                            pass

                    if salary_raw == "Thương lượng":
                        base_sal = ld_data.get("baseSalary") or {}
                        val = base_sal.get("value") if isinstance(base_sal, dict) else ""
                        if isinstance(val, dict):
                            if val.get("minValue") or val.get("maxValue"):
                                salary_raw = f"{val.get('minValue', '')} - {val.get('maxValue', '')} {val.get('unitText', '')}".strip()

                    # 5. Company Info & Overview từ RSC stream
                    comp_overview = ""
                    comp_detail_url = ""
                    comp_address_str = ""

                    comp_pattern = re.compile(r'\{"id":\d+,"display_name":"[^"]+","image_logo":')
                    decoder = json.JSONDecoder()
                    for m in comp_pattern.finditer(decoded):
                        start = m.start()
                        try:
                            c_obj, _ = decoder.raw_decode(decoded[start:])
                            if isinstance(c_obj, dict) and "display_name" in c_obj and "description" in c_obj:
                                raw_desc = c_obj.get("description", "")
                                comp_overview = fix_encoding(clean_html(raw_desc))
                                comp_detail_url = c_obj.get("detail_url") or c_obj.get("website") or ""
                                if not comp_name and c_obj.get("display_name"):
                                    comp_name = fix_encoding(c_obj.get("display_name"))
                                if not comp_logo and c_obj.get("image_logo"):
                                    comp_logo = c_obj.get("image_logo")
                                break
                        except Exception:
                            continue

                    if comp_detail_url:
                        comp_url = comp_detail_url

                    # Trích xuất địa chỉ công ty chi tiết từ RSC stream
                    m_ref = re.search(r'full_addresses":\s*"\$([a-zA-Z0-9]+)"', decoded)
                    if m_ref:
                        ref_id = m_ref.group(1)
                        m_arr = re.search(r'\b' + ref_id + r':(\[[^\]]+\])', decoded)
                        if m_arr:
                            try:
                                addrs = json.loads(m_arr.group(1))
                                comp_address_str = "; ".join([fix_encoding(a) for a in addrs if a])
                            except Exception:
                                pass

                    # 6. Company Box: Ngành nghề, Quy mô công ty, Quốc gia
                    industry_raw = ""
                    company_size_raw = ""
                    for row in soup.find_all("div", class_=lambda c: c and "items-center" in c and "justify-between" in c):
                        text = row.get_text(strip=True)
                        spans = row.find_all("span")
                        if len(spans) >= 2:
                            val_text = spans[1].get_text(separator=" ", strip=True)
                            if "Ngành nghề" in text:
                                industry_raw = val_text
                            elif "Quy mô công ty" in text:
                                company_size_raw = val_text

                    if not industry_raw:
                        industry_raw = str(ld_data.get("industry") or "Information Technology")

                    # 7. Các Section chi tiết: 1 Vai trò, 2 Kỹ năng, 3 Quyền lợi
                    responsibilities_raw = ""
                    requirements_raw = ""
                    benefits_raw = ""

                    for num, title_kw, target in [("1", "Vai trò", "resp"), ("2", "Kỹ năng", "req"), ("3", "Quyền lợi", "ben")]:
                        span = soup.find(lambda t: t.name == "span" and num in t.get_text() and title_kw in t.get_text())
                        if span:
                            parent = span.parent
                            content_el = span.find_next_sibling() or parent.find_next_sibling()
                            if content_el:
                                txt = clean_html(str(content_el))
                                if target == "resp":
                                    responsibilities_raw = txt
                                elif target == "req":
                                    requirements_raw = txt
                                elif target == "ben":
                                    benefits_raw = txt

                    # Fallback an toàn nếu tin không chia theo 3 section chuẩn
                    if not responsibilities_raw:
                        responsibilities_raw = clean_html(ld_data.get("description", ""))
                    if not benefits_raw:
                        b = ld_data.get("jobBenefits")
                        benefits_raw = clean_html(b) if isinstance(b, str) else ("\n".join(b) if isinstance(b, list) else "")
                    if not requirements_raw:
                        exp_req = ld_data.get("experienceRequirements", "")
                        requirements_raw = clean_html(exp_req) if isinstance(exp_req, str) else ""

                    # 7. Working Time & Location
                    working_time_raw = ""
                    for tag in soup.find_all(lambda t: t.name in ["div", "p", "li", "span"] and "Working time:" in t.get_text()):
                        line = tag.get_text(strip=True)
                        m = re.search(r"Working time:\s*(.*?)(?:\n|$|Working Location)", line, re.IGNORECASE)
                        if m:
                            working_time_raw = m.group(1).strip()
                            break
                        elif "Working time:" in line:
                            working_time_raw = line
                            break

                    # 8. Skills, Dates
                    skills_raw = str(ld_data.get("skills") or "")
                    if not skills_raw:
                        skill_tags = soup.find_all("a", href=lambda h: h and "/tim-kiem?skills=" in h)
                        if skill_tags:
                            skills_raw = ", ".join([s.get_text(strip=True) for s in skill_tags])

                    posted_at = str(ld_data.get("datePosted") or "")
                    deadline = str(ld_data.get("validThrough") or "")
                    now_iso = datetime.now().isoformat()

                    # Cập nhật thông tin Listing
                    updated_listing.update({
                        "company_logo_url": comp_logo,
                        "title_raw": title,
                        "company_name_raw": comp_name,
                        "location_raw": location_raw,
                        "salary_raw": salary_raw,
                        "experience_raw": experience_raw,
                        "skills_raw": skills_raw or updated_listing.get("skills_raw", ""),
                        "posted_at_raw": posted_at,
                        "detail_status": "success",
                        "detail_error": "",
                        "detail_crawled_at": now_iso
                    })

                    # Chi tiết job đầy đủ chuẩn xác
                    detail_record = {
                        "detail_id": f"topdev_{job_id}",
                        "source": "topdev",
                        "source_job_id": job_id,
                        "job_url": job_url,
                        "title_raw": title,
                        "company_name_raw": comp_name,
                        "company_url": comp_url,
                        "company_size_raw": company_size_raw,
                        "company_location_raw": comp_address_str or location_raw,
                        "industry_raw": industry_raw,
                        "salary_raw": salary_raw,
                        "experience_raw": experience_raw,
                        "education_raw": "",
                        "location_raw": location_raw,
                        "work_mode_raw": work_mode_raw or "Onsite",
                        "employment_type_raw": level_raw,
                        "working_time_raw": working_time_raw,
                        "overview_raw": comp_overview,
                        "responsibilities_raw": responsibilities_raw,
                        "requirements_raw": requirements_raw,
                        "benefits_raw": benefits_raw,
                        "required_skills_raw": skills_raw,
                        "preferred_skills_raw": "",
                        "published_at_raw": posted_at,
                        "updated_at_raw": "",
                        "deadline_raw": deadline,
                        "crawled_at": now_iso
                    }

                    # Validate với Pydantic schema
                    JobDetailRaw(**detail_record)

                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {job_id}: '{title}' | Cty: '{comp_name}' | "
                        f"Cấp bậc: '{level_raw}' | KN: '{experience_raw}' | Lương: '{salary_raw}'"
                    )
                    return detail_record, updated_listing

                elif resp.status_code == 404:
                    self.logger.warning(f"-> [EXPIRED] Job {job_id} trả về HTTP 404 (Tin đã hết hạn).")
                    updated_listing["detail_status"] = "expired"
                    updated_listing["detail_error"] = "HTTP 404 Not Found"
                    return None, updated_listing

                else:
                    raise RuntimeError(f"HTTP status code {resp.status_code}")

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"-> [LỖI LẦN {attempt}/{self.max_retries}] Job {job_id}: {last_error}")

                if attempt < self.max_retries:
                    sleep_time = self.retry_delays[attempt - 1]
                    self.logger.info(f"   Đang chờ {sleep_time}s trước khi thử lại lần {attempt + 1}...")
                    time.sleep(sleep_time)

        # Hết 3 lần thử vẫn thất bại
        self.logger.error(f"-> [THẤT BẠI] Job {job_id} sau {self.max_retries} lần thử không thành công.")
        updated_listing["detail_status"] = "failed"
        updated_listing["detail_error"] = last_error
        return None, updated_listing

    def _collect_retry_jobs(self, crawled_job_ids: Set[str]) -> List[Tuple[str, int, Dict[str, Any]]]:
        """
        Tìm tất cả các job cũ đang ở trạng thái 'failed' hoặc 'pending' trong các file page_XXX.json
        để ưu tiên retry trong phiên này.
        Trả về list các tuple: (page_file_path, item_index, job_item)
        """
        retry_items: List[Tuple[str, int, Dict[str, Any]]] = []
        listings_root = os.path.join(self.base_raw_dir, "listings")
        if not os.path.exists(listings_root):
            return retry_items

        # Quét các thư mục ngày trong listings
        for date_folder in sorted(os.listdir(listings_root)):
            folder_path = os.path.join(listings_root, date_folder)
            if not os.path.isdir(folder_path):
                continue
            for page_file in sorted(os.listdir(folder_path)):
                if page_file.startswith("page_") and page_file.endswith(".json"):
                    page_path = os.path.join(folder_path, page_file)
                    try:
                        with open(page_path, "r", encoding="utf-8") as f:
                            items = json.load(f)
                        for idx, item in enumerate(items):
                            jid = str(item.get("source_job_id", ""))
                            status = item.get("detail_status", "pending")
                            if jid and jid not in crawled_job_ids and status in ["failed", "pending"]:
                                retry_items.append((page_path, idx, item))
                    except Exception:
                        continue
        return retry_items

    def _get_next_run_index(self) -> int:
        """
        Tìm số thứ tự lần cào tiếp theo trong ngày hôm nay:
        Ví dụ: nếu đã có TC001.json hoặc page_001.json -> trả về 2.
        """
        max_idx = 0
        if os.path.exists(self.details_dir):
            for f in os.listdir(self.details_dir):
                m = re.match(r"^TC(\d+)\.json$", f)
                if m:
                    idx = int(m.group(1))
                    if idx > max_idx:
                        max_idx = idx

        if os.path.exists(self.listings_dir):
            for f in os.listdir(self.listings_dir):
                m = re.match(r"^page_(\d+)\.json$", f)
                if m:
                    idx = int(m.group(1))
                    if idx > max_idx:
                        max_idx = idx

        return max_idx + 1

    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
        """
        Thực thi quy trình cào:
        1. Tạo cấu trúc thư mục listings/YYYY-MM-DD/ và details/YYYY-MM-DD/
        2. Gom TOÀN BỘ listings của lần cào này vào DUY NHẤT 1 file: page_XXX.json
        3. Gom TOÀN BỘ details của lần cào này vào DUY NHẤT 1 file: TCXXX.json
        4. Ưu tiên cào lại các job cũ bị lỗi/pending trước đó.
        5. Nếu chưa đủ 100 job, quét các trang mới và cào tiếp cho đến khi đủ target.
        """
        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CRAWL TOPDEV - MỤC TIÊU: {target_success_count} JOBS THÀNH CÔNG")
        self.logger.info(f"Thư mục Listings: {self.listings_dir}")
        self.logger.info(f"Thư mục Details : {self.details_dir}")
        self.logger.info("=" * 70)

        # Lấy danh sách job_id đã cào thành công từ trước
        crawled_job_ids = self._get_all_crawled_job_ids()
        self.logger.info(f"Tổng số job chi tiết đã cào thành công từ trước: {len(crawled_job_ids)}")

        # Xác định số thứ tự phiên cào hôm nay
        current_run_idx = self._get_next_run_index()
        current_tc_filename = f"TC{current_run_idx:03d}.json"
        current_tc_filepath = os.path.join(self.details_dir, current_tc_filename)

        current_listing_filename = f"page_{current_run_idx:03d}.json"
        current_listing_filepath = os.path.join(self.listings_dir, current_listing_filename)

        self.logger.info(f"Tất cả listings phiên này sẽ lưu chung vào: {current_listing_filename}")
        self.logger.info(f"Tất cả details phiên này sẽ lưu chung vào : {current_tc_filename}")

        session_listings_list: List[Dict[str, Any]] = []
        session_details_list: List[Dict[str, Any]] = []
        seen_listing_ids: Set[str] = set()

        session_success_count = 0
        failed_count_session = 0

        # ==============================================================
        # GIAI ĐOẠN 1: CÀO LẠI CÁC JOB CŨ (RETRY JOBS)
        # ==============================================================
        retry_candidates = self._collect_retry_jobs(crawled_job_ids)
        if retry_candidates:
            self.logger.info(f"Phát hiện {len(retry_candidates)} job cũ cần cào lại/hoàn tất.")

        for page_file_path, item_idx, job_item in retry_candidates:
            if session_success_count >= target_success_count:
                self.logger.info(f"Đã đạt đủ {target_success_count} jobs thành công! Dừng phiên.")
                break

            jid = str(job_item["source_job_id"])
            detail_res, updated_item = self.fetch_job_detail_with_retry(job_item)

            if detail_res:
                session_details_list.append(detail_res)
                updated_item["detail_file"] = current_tc_filename
                crawled_job_ids.add(jid)
                session_success_count += 1

                # Cập nhật ghi đè file TCxxx.json của phiên này
                self._save_batch_details(current_tc_filepath, session_details_list)
                self.logger.info(
                    f"-> Đã lưu job {jid} vào {current_tc_filename} "
                    f"({len(session_details_list)} jobs trong file). Tiến độ: {session_success_count}/{target_success_count}"
                )
            else:
                failed_count_session += 1

            # Cập nhật lại file listing gốc chứa job này
            try:
                with open(page_file_path, "r", encoding="utf-8") as f:
                    page_items = json.load(f)
                page_items[item_idx] = updated_item
                with open(page_file_path, "w", encoding="utf-8") as f:
                    json.dump(page_items, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.warning(f"Không thể cập nhật lại file {page_file_path}: {e}")

            time.sleep(random.uniform(self.delay_min, self.delay_max))

        # ==============================================================
        # GIAI ĐOẠN 2: QUÉT THÊM TRANG MỚI NẾU CHƯA ĐỦ TARGET JOBS
        # ==============================================================
        current_page = self.start_page
        max_page_limit = self.start_page + self.max_pages

        while session_success_count < target_success_count and current_page <= max_page_limit:
            needed = target_success_count - session_success_count
            self.logger.info(f"Cần thêm {needed} job thành công. Đang quét trang web {current_page}...")

            page_items = self.fetch_job_list_page(current_page)
            if not page_items:
                self.logger.warning(f"Không có dữ liệu từ page {current_page}. Chuyển sang page tiếp theo.")
                current_page += 1
                continue

            # Lọc job mới chưa từng gặp
            new_jobs = []
            for itm in page_items:
                jid = str(itm["source_job_id"])
                if jid not in seen_listing_ids and jid not in crawled_job_ids:
                    seen_listing_ids.add(jid)
                    session_listings_list.append(itm)
                    new_jobs.append(itm)

            # Lưu toàn bộ listing tích lũy của phiên này vào duy nhất 1 file page_XXX.json
            with open(current_listing_filepath, "w", encoding="utf-8") as f:
                json.dump(session_listings_list, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Trang {current_page}: Thu thập thêm {len(new_jobs)} jobs mới chưa cào.")

            # Duyệt từng job mới tìm được để cào detail
            for itm in new_jobs:
                if session_success_count >= target_success_count:
                    break

                jid = str(itm["source_job_id"])
                detail_res, updated_item = self.fetch_job_detail_with_retry(itm)

                # Cập nhật thông tin trong listing item
                itm.update(updated_item)

                if detail_res:
                    session_details_list.append(detail_res)
                    itm["detail_file"] = current_tc_filename
                    crawled_job_ids.add(jid)
                    session_success_count += 1

                    # Cập nhật ghi đè file TCxxx.json của phiên này
                    self._save_batch_details(current_tc_filepath, session_details_list)
                    self.logger.info(
                        f"-> Đã lưu job {jid} vào {current_tc_filename} "
                        f"({len(session_details_list)} jobs trong file). Tiến độ: {session_success_count}/{target_success_count}"
                    )
                else:
                    failed_count_session += 1

                # Cập nhật và lưu lại file listing duy nhất của phiên này
                with open(current_listing_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_listings_list, f, ensure_ascii=False, indent=2)

                time.sleep(random.uniform(self.delay_min, self.delay_max))

            current_page += 1

        # ==============================================================
        # BÁO CÁO TỔNG KẾT
        # ==============================================================
        self.logger.info("\n" + "=" * 70)
        self.logger.info("BÁO CÁO TỔNG KẾT PHIÊN CÀO TOPDEV")
        self.logger.info("=" * 70)
        self.logger.info(f"- Số job cào thành công phiên này : {session_success_count}/{target_success_count}")
        self.logger.info(f"- Số job lỗi trong phiên này      : {failed_count_session}")
        self.logger.info(f"- File listing đã lưu             : {current_listing_filename} ({len(session_listings_list)} listings)")
        self.logger.info(f"- File detail đã lưu              : {current_tc_filename} ({len(session_details_list)} jobs)")
        self.logger.info(f"- Thư mục listings                : {self.listings_dir}")
        self.logger.info(f"- Thư mục details                 : {self.details_dir}")
        self.logger.info("=" * 70)

        return {
            "session_success_count": session_success_count,
            "failed_count": failed_count_session,
            "saved_listing_file": current_listing_filename,
            "saved_detail_file": current_tc_filename,
            "total_listings_in_file": len(session_listings_list),
            "total_jobs_in_file": len(session_details_list),
            "listings_dir": self.listings_dir,
            "details_dir": self.details_dir
        }


if __name__ == "__main__":
    crawler = TopDevCrawler()
    crawler.run(target_success_count=100)
