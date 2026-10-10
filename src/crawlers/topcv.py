import os
import sys
import re
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

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.crawlers.base import BaseCrawler
from src.schemas.job import JobListingRaw, JobDetailRaw


def clean_html(raw_html: str) -> str:
    """Loại bỏ các thẻ HTML và định dạng text gọn gàng"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


class TopCVCrawler(BaseCrawler):
    def __init__(self, config_path: str = "configs/sources.yaml"):
        # 1. Đọc file cấu hình sources.yaml
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            topcv_cfg = all_configs.get("sources", {}).get("topcv", {})

        super().__init__(topcv_cfg)

        # 2. Tham số cào & đường dẫn
        self.listing_url_template = self.config.get(
            "listing_url",
            "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?type_keyword=1&disable_auto_detect_type_keyword=1&page={page}&category_family=r257&saturday_status=0&sba=1"
        )
        pagination = self.config.get("pagination", {})
        self.start_page = int(pagination.get("start_page", 1))
        self.max_pages = int(pagination.get("max_pages", 20))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 1.0))
        self.delay_max = float(rate_limit.get("delay_max", 2.0))
        self.timeout = int(rate_limit.get("timeout", 20))

        # Cấu hình retry cho cào chi tiết: 10s, 20s, 30s
        self.retry_delays = [10, 20, 30]
        self.max_retries = len(self.retry_delays)

        # 3. Cấu trúc thư mục lưu trữ JSON thuần túy theo ngày
        # data/raw/topcv/listings/YYYY-MM-DD/
        # data/raw/topcv/details/YYYY-MM-DD/
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "topcv")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        # 4. Logger, Session & Company Overview Cache
        self.logger = self._setup_logger()
        self.session = requests.Session(impersonate="chrome124")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.topcv.vn/"
        }
        self.company_cache: Dict[str, str] = {}

    def _setup_logger(self) -> logging.Logger:
        """Thiết lập logger ghi ra cả Terminal và File log trong thư mục details của ngày hôm nay"""
        logger = logging.getLogger("TopCVCrawler")
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        log_format = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [TopCV] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # File Handler ghi vào thư mục logs chung
        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "topcv.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        return logger

    def _get_all_crawled_job_ids(self) -> Set[str]:
        """Quét tất cả các file TCVxxx.json trong thư mục details để lấy danh sách job_id đã cào"""
        crawled_ids: Set[str] = set()
        details_root = os.path.join(self.base_raw_dir, "details")
        if not os.path.exists(details_root):
            return crawled_ids

        for date_folder in os.listdir(details_root):
            folder_path = os.path.join(details_root, date_folder)
            if not os.path.isdir(folder_path):
                continue
            for file_name in os.listdir(folder_path):
                if file_name.startswith("TCV") and file_name.endswith(".json"):
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

    def _get_next_run_index(self) -> int:
        """Tìm số thứ tự phiên cào tiếp theo trong ngày hôm nay: ví dụ TCV001.json, page_001.json"""
        max_idx = 0
        if os.path.exists(self.details_dir):
            for f in os.listdir(self.details_dir):
                m = re.match(r"^TCV(\d+)\.json$", f)
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

    def fetch_job_list_page(self, page: int) -> List[Dict[str, Any]]:
        """
        Cào danh sách job từ trang tìm kiếm TopCV.
        Bóc tách đầy đủ: title, company, logo, lương, địa điểm, kinh nghiệm và skill tags ngay từ card listing.
        """
        url = self.listing_url_template.format(page=page)
        self.logger.info(f"Đang quét danh sách TopCV tại trang {page}: {url}")

        try:
            resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                self.logger.warning(f"Trang {page} trả về HTTP status {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".job-item-search-result")
            found_items = []
            seen = set()

            for card in cards:
                jid = card.get("data-job-id") or ""
                if not jid:
                    continue
                jid = str(jid).strip()
                if jid in seen:
                    continue
                seen.add(jid)

                # Tiêu đề & URL bài tuyển dụng
                title_el = card.select_one(".title a, h3 a, .job-title a")
                title = title_el.get_text(strip=True) if title_el else ""
                job_url = title_el.get("href") if title_el else ""
                if job_url and "?" in job_url:
                    job_url = job_url.split("?")[0]

                # Công ty & Logo
                comp_el = card.select_one(".company, .company-name, a.company")
                comp_name = comp_el.get_text(strip=True) if comp_el else ""
                logo_el = card.select_one("img")
                comp_logo = logo_el.get("src") if logo_el else ""

                # Mức lương
                sal_el = card.select_one(".salary, .title-salary")
                salary = sal_el.get_text(strip=True) if sal_el else "Thoả thuận"

                # Địa điểm & Kinh nghiệm
                addr_el = card.select_one(".address")
                location = addr_el.get_text(strip=True) if addr_el else ""
                # Làm sạch nhãn địa điểm nếu có chữ '(mới)'
                location = location.replace("(mới)", "").strip()

                exp_el = card.select_one(".exp")
                experience = exp_el.get_text(strip=True) if exp_el else ""

                # Trích xuất toàn bộ tags & kỹ năng từ card (item-tag và tooltip remaining-items)
                tags: List[str] = []
                tag_container = card.select_one(".tag")
                if tag_container:
                    for span in tag_container.select(".item-tag"):
                        t_text = span.get("title") or span.get_text(strip=True)
                        if t_text and t_text not in tags and not t_text.endswith("..."):
                            tags.append(t_text)
                    rem = tag_container.select_one(".remaining-items")
                    if rem:
                        rem_title = rem.get("title") or rem.get("data-original-title") or rem.get("data-bs-title") or ""
                        if rem_title:
                            for item in rem_title.split(","):
                                item = item.strip()
                                if item and item not in tags:
                                    tags.append(item)

                skills_raw = ", ".join(tags)

                # Ngày đăng bài
                posted_el = card.select_one(".label-update, .address.label-update")
                posted_at = posted_el.get_text(strip=True) if posted_el else ""

                item_rec = {
                    "source": "topcv",
                    "source_job_id": jid,
                    "job_url": job_url,
                    "company_logo_url": comp_logo or "",
                    "title_raw": title,
                    "company_name_raw": comp_name,
                    "location_raw": location,
                    "salary_raw": salary,
                    "experience_raw": experience,
                    "skills_raw": skills_raw,
                    "posted_at_raw": posted_at,
                    "crawled_at": datetime.now().isoformat(),
                    "detail_status": "pending",
                    "detail_attempts": 0,
                    "detail_http_status": None,
                    "detail_error": "",
                    "detail_file": "",
                    "detail_crawled_at": None
                }
                found_items.append(item_rec)

            self.logger.info(f"-> Trang {page} tìm thấy {len(found_items)} jobs TopCV với đầy đủ thông tin tóm tắt.")
            return found_items

        except Exception as e:
            self.logger.error(f"Lỗi khi quét danh sách TopCV trang {page}: {e}")
            return []

    def _fetch_company_overview(self, company_url: str) -> str:
        """
        Truy cập trang hồ sơ công ty (company_url) để lấy nội dung giới thiệu công ty thật.
        TopCV bị lỗi khi gán employerOverview trong JobPosting bằng chính mô tả công việc (JD).
        Sử dụng bộ nhớ cache theo company_url để tránh cào lại nhiều lần cho cùng một công ty.
        """
        if not company_url:
            return ""
        if company_url in self.company_cache:
            return self.company_cache[company_url]

        try:
            resp = self.session.get(company_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                comp_box = soup.select_one(".company-info .content, .company-info .box-body, .company-info")
                if comp_box:
                    for h in comp_box.find_all(["h1", "h2", "h3", "h4"]):
                        h.decompose()
                    for btn in comp_box.select(".load-more, .show-less, .see-more, .read-more, a.btn-see-more"):
                        btn.decompose()
                    desc = clean_html(str(comp_box))
                    # Xoá triệt để các chữ Xem thêm / Thu gọn thừa nếu còn sót
                    desc = re.sub(r'\n?\s*(Xem thêm|Thu gọn)\s*$', '', desc, flags=re.IGNORECASE).strip()
                    desc = re.sub(r'\n?\s*(Xem thêm|Thu gọn)\s*$', '', desc, flags=re.IGNORECASE).strip()
                    self.company_cache[company_url] = desc
                    return desc
        except Exception as e:
            self.logger.warning(f"Không thể lấy giới thiệu công ty từ {company_url}: {e}")

        self.company_cache[company_url] = ""
        return ""

    def fetch_job_detail_with_retry(
        self,
        job_item: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Cào chi tiết một job TopCV với cơ chế Retry 3 lần (10s, 20s, 30s):
        - Bóc tách toàn diện qua Schema JSON-LD JobPosting và DOM HTML
        - Bóc tách Mô tả (responsibilities), Yêu cầu (requirements), Quyền lợi (benefits)
        - Trích xuất thông tin công ty, trụ sở, học vấn, chế độ làm việc từ Sidebar và Thông tin chung
        """
        job_url = job_item["job_url"]
        job_id = str(job_item["source_job_id"])
        updated_listing = dict(job_item)

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            updated_listing["detail_attempts"] = attempt
            try:
                self.logger.info(f"Đang tải chi tiết Job {job_id} (Lần thử {attempt}/{self.max_retries}): {job_url}")
                resp = self.session.get(job_url, headers=self.headers, timeout=self.timeout)
                updated_listing["detail_http_status"] = resp.status_code

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    ld_data: Dict[str, Any] = {}

                    # 1. Trích xuất Schema JSON-LD JobPosting
                    for s in soup.find_all("script", type="application/ld+json"):
                        try:
                            content = (s.string if s.string else s.text) or ""
                            d = json.loads(content)
                            if d.get("@type") == "JobPosting":
                                ld_data = d
                                break
                        except Exception:
                            continue

                    # Tiêu đề & Công ty
                    title = ld_data.get("title") or job_item.get("title_raw", "")
                    hiring_org = ld_data.get("hiringOrganization") or {}
                    comp_name = hiring_org.get("name") or job_item.get("company_name_raw", "")
                    comp_url = hiring_org.get("sameAs") or ""
                    comp_logo = hiring_org.get("logo") or job_item.get("company_logo_url", "")

                    # Địa chỉ làm việc chi tiết
                    job_loc = ld_data.get("jobLocation") or {}
                    addr_dict = job_loc.get("address") or {} if isinstance(job_loc, dict) else {}
                    loc_parts = []
                    if isinstance(addr_dict, dict):
                        for k in ["streetAddress", "addressLocality", "addressRegion"]:
                            val = addr_dict.get(k)
                            if val and val not in loc_parts:
                                loc_parts.append(val)
                    location_raw = ", ".join(loc_parts) if loc_parts else job_item.get("location_raw", "")

                    # Lương & Kinh nghiệm
                    sal_obj = ld_data.get("baseSalary") or {}
                    sal_val = sal_obj.get("value") if isinstance(sal_obj, dict) else ""
                    if isinstance(sal_val, dict):
                        salary_raw = str(sal_val.get("value") or sal_val.get("minValue") or job_item.get("salary_raw", ""))
                    elif isinstance(sal_val, str) and sal_val:
                        salary_raw = sal_val
                    else:
                        salary_raw = job_item.get("salary_raw", "Thương lượng")

                    exp_req = ld_data.get("experienceRequirements") or {}
                    months_exp = exp_req.get("monthsOfExperience") if isinstance(exp_req, dict) else None
                    if months_exp:
                        years = months_exp // 12
                        experience_raw = f"{years} năm" if years > 0 else f"{months_exp} tháng"
                    else:
                        experience_raw = job_item.get("experience_raw", "")

                    # 2. Bóc tách từ Sidebar Thông tin công ty (.box-company-info-detail)
                    company_size_raw = ""
                    company_location_raw = ""
                    industry_raw = ld_data.get("industry") or ""

                    for c_item in soup.select(".box-company-info-detail__list--item"):
                        c_text = c_item.get_text(separator=" ", strip=True)
                        c_text_lower = c_text.lower()
                        if "quy mô" in c_text_lower:
                            company_size_raw = re.sub(r"^quy\s*mô\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()
                        elif "địa điểm" in c_text_lower:
                            tooltip = c_item.select_one('[data-toggle="tooltip"], [title]')
                            if tooltip and tooltip.get("title"):
                                company_location_raw = tooltip.get("title").strip()
                            else:
                                company_location_raw = re.sub(r"^địa\s*điểm\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()
                        elif "ngành nghề" in c_text_lower and not industry_raw:
                            industry_raw = re.sub(r"^ngành\s*nghề\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()

                    if not company_location_raw:
                        company_location_raw = location_raw
                    if not industry_raw:
                        industry_raw = "Công nghệ thông tin / Phần mềm"

                    # 3. Bóc tách từ Box Thông tin chung (.box-job-information-general-info-list__item)
                    education_raw = ""
                    work_mode_raw = ""
                    emp_type_raw = ld_data.get("occupationalCategory") or ""
                    working_time_raw = "Toàn thời gian" if ld_data.get("employmentType") == "FULL_TIME" else (str(ld_data.get("employmentType") or ""))

                    for g_item in soup.select(".box-job-information-general-info-list__item"):
                        g_text = g_item.get_text(separator=" ", strip=True)
                        g_text_lower = g_text.lower()
                        if "học vấn" in g_text_lower:
                            education_raw = re.sub(r"^học\s*vấn\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
                        elif "hình thức làm việc" in g_text_lower:
                            raw_wm = re.sub(r"^hình\s*thức\s*làm\s*việc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
                            if "onsite" in raw_wm.lower() or "văn phòng" in raw_wm.lower():
                                work_mode_raw = "Onsite"
                            elif "remote" in raw_wm.lower() or "từ xa" in raw_wm.lower():
                                work_mode_raw = "Remote"
                            elif "hybrid" in raw_wm.lower():
                                work_mode_raw = "Hybrid"
                            else:
                                work_mode_raw = raw_wm
                        elif "cấp bậc" in g_text_lower and not emp_type_raw:
                            emp_type_raw = re.sub(r"^cấp\s*bậc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
                        elif "loại hình làm việc" in g_text_lower:
                            working_time_raw = re.sub(r"^loại\s*hình\s*làm\s*việc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()

                    # Fallback work_mode nếu chưa có
                    if not work_mode_raw:
                        search_text = f"{title} {location_raw}"
                        for wm in ["Full-remote", "Remote", "Hybrid", "Onsite", "Làm từ xa"]:
                            if re.search(r'\b' + re.escape(wm) + r'\b', search_text, re.IGNORECASE):
                                work_mode_raw = "Remote" if "remote" in wm.lower() or "từ xa" in wm.lower() else wm
                                break
                    if not work_mode_raw:
                        work_mode_raw = "Onsite"

                    # 4. Giới thiệu công ty (overview_raw) - Cào trang hồ sơ công ty thật
                    overview_raw = self._fetch_company_overview(comp_url)

                    # Ngày đăng & Hạn nộp
                    posted_at = str(ld_data.get("datePosted") or job_item.get("posted_at_raw", ""))
                    deadline = str(ld_data.get("validThrough") or "")

                    # 5. Bóc tách 3 phần: Mô tả công việc, Yêu cầu ứng viên, Quyền lợi
                    responsibilities_raw = ""
                    requirements_raw = ""
                    benefits_raw = clean_html(ld_data.get("jobBenefits", ""))

                    desc_html = ld_data.get("description", "")
                    if desc_html:
                        desc_soup = BeautifulSoup(desc_html, "html.parser")
                        current_sec = ""
                        resp_chunks, req_chunks, ben_chunks = [], [], []

                        for el in desc_soup.children:
                            if not el.name:
                                continue
                            txt = el.get_text(strip=True)
                            if "mô tả công việc" in txt.lower():
                                current_sec = "resp"
                            elif "yêu cầu ứng viên" in txt.lower() or "yêu cầu công việc" in txt.lower():
                                current_sec = "req"
                            elif "quyền lợi" in txt.lower():
                                current_sec = "ben"
                            else:
                                if current_sec == "resp":
                                    resp_chunks.append(clean_html(str(el)))
                                elif current_sec == "req":
                                    req_chunks.append(clean_html(str(el)))
                                elif current_sec == "ben":
                                    ben_chunks.append(clean_html(str(el)))

                        responsibilities_raw = "\n".join([c for c in resp_chunks if c])
                        requirements_raw = "\n".join([c for c in req_chunks if c])
                        if not benefits_raw:
                            benefits_raw = "\n".join([c for c in ben_chunks if c])

                    # Fallback nếu không chia theo h2
                    if not responsibilities_raw:
                        responsibilities_raw = clean_html(desc_html)

                    # Kỹ năng
                    skills_raw = job_item.get("skills_raw", "")
                    now_iso = datetime.now().isoformat()

                    # Cập nhật lại bản ghi listing
                    updated_listing.update({
                        "title_raw": title,
                        "company_name_raw": comp_name,
                        "company_logo_url": comp_logo,
                        "location_raw": location_raw,
                        "salary_raw": salary_raw,
                        "experience_raw": experience_raw,
                        "skills_raw": skills_raw,
                        "posted_at_raw": posted_at,
                        "detail_status": "success",
                        "detail_error": "",
                        "detail_crawled_at": now_iso
                    })

                    # Bản ghi Detail hoàn chỉnh
                    detail_record = {
                        "detail_id": f"topcv_{job_id}",
                        "source": "topcv",
                        "source_job_id": job_id,
                        "job_url": job_url,
                        "title_raw": title,
                        "company_name_raw": comp_name,
                        "company_url": comp_url,
                        "company_size_raw": company_size_raw,
                        "company_location_raw": company_location_raw,
                        "industry_raw": industry_raw,
                        "salary_raw": salary_raw,
                        "experience_raw": experience_raw,
                        "education_raw": education_raw,
                        "location_raw": location_raw,
                        "work_mode_raw": work_mode_raw,
                        "employment_type_raw": emp_type_raw,
                        "working_time_raw": working_time_raw,
                        "overview_raw": overview_raw,
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

                    # Validate qua Pydantic schema
                    JobDetailRaw(**detail_record)

                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {job_id}: '{title}' | Cty: '{comp_name}' | "
                        f"Quy mô: '{company_size_raw}' | Trụ sở: '{company_location_raw[:35]}' | Học vấn: '{education_raw}'"
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

        self.logger.error(f"-> [THẤT BẠI] Job {job_id} sau {self.max_retries} lần thử không thành công.")
        updated_listing["detail_status"] = "failed"
        updated_listing["detail_error"] = last_error
        return None, updated_listing

    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
        """
        Thực thi quy trình cào TopCV:
        1. Tạo cấu trúc thư mục listings/YYYY-MM-DD/ và details/YYYY-MM-DD/
        2. Gom TOÀN BỘ listings phiên này vào 1 file: page_XXX.json
        3. Gom TOÀN BỘ details phiên này vào 1 file: TCVXXX.json
        4. Tự động deduplicate không cào lại job cũ đã có
        5. Phân trang cho tới khi đạt target_success_count jobs thành công
        """
        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CRAWL TOPCV - MỤC TIÊU: {target_success_count} JOBS THÀNH CÔNG")
        self.logger.info(f"Thư mục Listings: {self.listings_dir}")
        self.logger.info(f"Thư mục Details : {self.details_dir}")
        self.logger.info("=" * 70)

        crawled_job_ids = self._get_all_crawled_job_ids()
        self.logger.info(f"Tổng số job TopCV đã cào từ trước: {len(crawled_job_ids)}")

        current_run_idx = self._get_next_run_index()
        current_tcv_filename = f"TCV{current_run_idx:03d}.json"
        current_tcv_filepath = os.path.join(self.details_dir, current_tcv_filename)

        current_listing_filename = f"page_{current_run_idx:03d}.json"
        current_listing_filepath = os.path.join(self.listings_dir, current_listing_filename)

        self.logger.info(f"Tất cả listings phiên này sẽ lưu chung vào: {current_listing_filename}")
        self.logger.info(f"Tất cả details phiên này sẽ lưu chung vào : {current_tcv_filename}")

        session_listings: List[Dict[str, Any]] = []
        session_details: List[Dict[str, Any]] = []
        seen_in_session: Set[str] = set()

        session_success_count = 0
        failed_count_session = 0
        current_page = self.start_page
        max_page_limit = self.start_page + self.max_pages

        while session_success_count < target_success_count and current_page <= max_page_limit:
            needed = target_success_count - session_success_count
            self.logger.info(f"Cần thêm {needed} jobs thành công. Đang quét trang web TopCV {current_page}...")

            page_items = self.fetch_job_list_page(current_page)
            if not page_items:
                self.logger.warning(f"Không nhận được job nào ở trang {current_page}. Chuyển trang tiếp theo.")
                current_page += 1
                continue

            new_jobs = []
            for itm in page_items:
                jid = str(itm["source_job_id"])
                if jid not in seen_in_session and jid not in crawled_job_ids:
                    seen_in_session.add(jid)
                    session_listings.append(itm)
                    new_jobs.append(itm)

            # Lưu lũy kế listings của phiên
            with open(current_listing_filepath, "w", encoding="utf-8") as f:
                json.dump(session_listings, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Trang {current_page}: Thu thập được {len(new_jobs)} jobs mới chưa cào.")

            for itm in new_jobs:
                if session_success_count >= target_success_count:
                    break

                jid = str(itm["source_job_id"])
                detail_res, updated_item = self.fetch_job_detail_with_retry(itm)
                itm.update(updated_item)

                if detail_res:
                    session_details.append(detail_res)
                    itm["detail_file"] = current_tcv_filename
                    crawled_job_ids.add(jid)
                    session_success_count += 1

                    # Lưu cập nhật lũy kế details của phiên
                    with open(current_tcv_filepath, "w", encoding="utf-8") as f:
                        json.dump(session_details, f, ensure_ascii=False, indent=2)

                    self.logger.info(
                        f"-> Đã lưu job {jid} vào {current_tcv_filename} "
                        f"({len(session_details)} jobs). Tiến độ: {session_success_count}/{target_success_count}"
                    )
                else:
                    failed_count_session += 1

                # Cập nhật lại file listing
                with open(current_listing_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_listings, f, ensure_ascii=False, indent=2)

                time.sleep(random.uniform(self.delay_min, self.delay_max))

            current_page += 1

        # ==============================================================
        # BÁO CÁO TỔNG KẾT
        # ==============================================================
        self.logger.info("\n" + "=" * 70)
        self.logger.info("BÁO CÁO TỔNG KẾT PHIÊN CÀO TOPCV")
        self.logger.info("=" * 70)
        self.logger.info(f"- Số job cào thành công phiên này : {session_success_count}/{target_success_count}")
        self.logger.info(f"- Số job lỗi trong phiên này      : {failed_count_session}")
        self.logger.info(f"- File listing đã lưu             : {current_listing_filename} ({len(session_listings)} listings)")
        self.logger.info(f"- File detail đã lưu              : {current_tcv_filename} ({len(session_details)} jobs)")
        self.logger.info(f"- Thư mục listings                : {self.listings_dir}")
        self.logger.info(f"- Thư mục details                 : {self.details_dir}")
        self.logger.info("=" * 70)

        return {
            "session_success_count": session_success_count,
            "failed_count": failed_count_session,
            "saved_listing_file": current_listing_filename,
            "saved_detail_file": current_tcv_filename,
            "total_listings_in_file": len(session_listings),
            "total_jobs_in_file": len(session_details),
            "listings_dir": self.listings_dir,
            "details_dir": self.details_dir
        }


if __name__ == "__main__":
    crawler = TopCVCrawler()
    crawler.run(target_success_count=5)
