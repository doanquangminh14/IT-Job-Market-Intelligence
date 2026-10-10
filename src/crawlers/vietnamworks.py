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
    """Loại bỏ các thẻ HTML và định dạng text xuống dòng gọn gàng"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


class VietnamWorksCrawler(BaseCrawler):
    def __init__(self, config_path: str = "configs/sources.yaml"):
        # 1. Đọc file cấu hình sources.yaml
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            vnw_cfg = all_configs.get("sources", {}).get("vietnamworks", {})

        super().__init__(vnw_cfg)

        # 2. Tham số API & Pagination
        self.api_endpoint = self.config.get(
            "api_endpoint",
            "https://ms.vietnamworks.com/job-search/v1.0/search"
        )
        self.default_headers = self.config.get("headers", {
            "Content-Type": "application/json",
            "Origin": "https://www.vietnamworks.com",
            "Referer": "https://www.vietnamworks.com/"
        })
        self.default_payload = self.config.get("default_payload", {
            "query": "it",
            "jobFunctionId": [{"parentId": 5, "childrenIds": [-1]}]
        })

        pagination = self.config.get("pagination", {})
        self.start_page = int(pagination.get("start_page", 0))
        self.hits_per_page = int(pagination.get("hits_per_page", 50))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 0.5))
        self.delay_max = float(rate_limit.get("delay_max", 1.0))
        self.timeout = int(rate_limit.get("timeout", 20))

        # Cấu hình retry cho API request
        self.retry_delays = [5, 10, 20]
        self.max_retries = len(self.retry_delays)

        # 3. Thư mục lưu trữ JSON thuần túy theo ngày
        # data/raw/vietnamworks/listings/YYYY-MM-DD/
        # data/raw/vietnamworks/details/YYYY-MM-DD/
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "vietnamworks")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        # 4. Logger & Session
        self.logger = self._setup_logger()
        self.session = requests.Session(impersonate="chrome124")

    def _setup_logger(self) -> logging.Logger:
        """Thiết lập logger ghi cả Terminal và File log trong thư mục details của ngày hôm nay"""
        logger = logging.getLogger("VietnamWorksCrawler")
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        log_format = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [VietnamWorks] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # File Handler ghi vào thư mục logs chung
        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "vietnamworks.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        return logger

    def _get_all_crawled_job_ids(self) -> Set[str]:
        """
        Quét tất cả các file VNWxxx.json trong thư mục details (cả hôm nay và các ngày trước)
        để lấy danh sách các source_job_id đã cào thành công, tránh trùng lặp.
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
                if file_name.startswith("VNW") and file_name.endswith(".json"):
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
        """
        Tìm số thứ tự phiên cào tiếp theo trong ngày hôm nay:
        Ví dụ: nếu đã có VNW001.json hoặc page_001.json -> trả về 2.
        """
        max_idx = 0
        if os.path.exists(self.details_dir):
            for f in os.listdir(self.details_dir):
                m = re.match(r"^VNW(\d+)\.json$", f)
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

    def fetch_api_page(self, page: int, hits_per_page: int) -> List[Dict[str, Any]]:
        """
        Gửi POST request đến VietnamWorks search API với cơ chế retry.
        Trả về danh sách raw job objects trong `data`.
        """
        payload = dict(self.default_payload)
        payload["page"] = page
        payload["hitsPerPage"] = hits_per_page

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    f"Gửi request API trang {page} (hits: {hits_per_page}) - Lần thử {attempt}/{self.max_retries}"
                )
                resp = self.session.post(
                    self.api_endpoint,
                    json=payload,
                    headers=self.default_headers,
                    timeout=self.timeout
                )

                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    self.logger.info(f"-> Trang {page} nhận thành công {len(data)} jobs.")
                    return data
                else:
                    self.logger.warning(
                        f"-> Trang {page} trả về HTTP status {resp.status_code}: {resp.text[:200]}"
                    )

            except Exception as e:
                self.logger.warning(f"-> Lỗi kết nối trang {page} (Lần thử {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                sleep_time = self.retry_delays[attempt - 1]
                self.logger.info(f"   Đang chờ {sleep_time}s trước khi thử lại...")
                time.sleep(sleep_time)

        self.logger.error(f"-> Thất bại khi tải trang {page} sau {self.max_retries} lần thử.")
        return []

    def parse_job_item(
        self,
        item: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Chuyển đổi 1 raw job object từ VietnamWorks API thành cặp bản ghi:
        - listing_record (JobListingRaw)
        - detail_record (JobDetailRaw)
        Đồng thời validate qua Pydantic schema.
        """
        job_id = str(item.get("jobId", ""))
        alias = item.get("alias", "")
        job_url = item.get("jobUrl", "") or f"https://www.vietnamworks.com/{alias}-{job_id}-jv"
        title = item.get("jobTitle", "") or ""
        comp_name = item.get("companyName", "") or ""
        comp_logo = item.get("companyLogo", "") or ""

        # 1. Company URL & Info
        comp_id = item.get("companyId")
        company_info = item.get("companyInfo") or {}
        comp_url = item.get("companyUrl") or company_info.get("companyProfileUrl") or ""
        if not comp_url and comp_id:
            import unicodedata
            nfkd = unicodedata.normalize('NFKD', comp_name)
            slug = re.sub(r'[^\w\s-]', '', nfkd).strip().lower()
            slug = re.sub(r'[-\s]+', '-', slug)
            comp_url = f"https://www.vietnamworks.com/nha-tuyen-dung/{slug}-c{comp_id}"

        # 2. Địa điểm làm việc (Ưu tiên workingLocations chi tiết)
        working_locs = item.get("workingLocations") or []
        loc_list = []
        for wl in working_locs:
            if isinstance(wl, dict):
                addr = (wl.get("address") or "").strip()
                city = (wl.get("cityNameVI") or wl.get("cityName") or "").strip()
                if addr and addr not in loc_list:
                    loc_list.append(addr)
                elif city and city not in loc_list:
                    loc_list.append(city)

        if not loc_list:
            locations = item.get("locations") or []
            if isinstance(locations, list):
                for l in locations:
                    if isinstance(l, dict) and (l.get("cityNameVI") or l.get("cityName")):
                        loc_list.append(l.get("cityNameVI") or l.get("cityName"))
                    elif isinstance(l, str) and l:
                        loc_list.append(l)
            if not loc_list and item.get("address"):
                loc_list.append(str(item.get("address")))

        loc_str = "; ".join(loc_list)
        comp_loc = (company_info.get("address") or item.get("address") or loc_str or "").strip()

        # 3. Lương & Kinh nghiệm
        salary = str(item.get("prettySalary") or item.get("salary") or "Thương lượng")
        exp_years = item.get("yearsOfExperience")
        exp_str = f"{exp_years} năm" if exp_years is not None and exp_years != "" else "Không yêu cầu"

        posted_at = str(item.get("approvedOn") or item.get("createdOn") or "")
        updated_at = str(item.get("lastUpdatedOn") or "")
        deadline = str(item.get("expiredOn") or "")
        now_iso = datetime.now().isoformat()

        # 4. Kỹ năng (Skills)
        skills_list = item.get("skills") or []
        skills_raw = ", ".join([
            s.get("skillName", "") for s in skills_list
            if isinstance(s, dict) and s.get("skillName")
        ])

        # 1. Listing Record
        listing_record = {
            "source": "vietnamworks",
            "source_job_id": job_id,
            "job_url": job_url,
            "company_logo_url": comp_logo,
            "title_raw": title,
            "company_name_raw": comp_name,
            "location_raw": loc_str,
            "salary_raw": salary,
            "experience_raw": exp_str,
            "skills_raw": skills_raw,
            "posted_at_raw": posted_at,
            "crawled_at": now_iso,
            "detail_status": "success",
            "detail_attempts": 1,
            "detail_http_status": 200,
            "detail_error": "",
            "detail_crawled_at": now_iso
        }
        JobListingRaw(**listing_record)

        # 5. Benefits, Description, Requirements
        benefits_list = []
        for b in (item.get("benefits") or []):
            if isinstance(b, dict):
                b_name = b.get("benefitNameVI") or b.get("benefitName") or ""
                b_val = b.get("benefitValue") or ""
                benefits_list.append(f"{b_name}: {b_val}" if b_val else b_name)
        benefits_raw = "\n".join([b for b in benefits_list if b])

        desc_text = clean_html(item.get("jobDescription", ""))
        req_text = clean_html(item.get("jobRequirement", ""))

        # 6. Lĩnh vực (IndustriesV3) & Ngành nghề (jobFunction)
        ind_v3 = [
            i.get("industryV3NameVI") or i.get("industryV3Name")
            for i in (item.get("industriesV3") or [])
            if isinstance(i, dict) and (i.get("industryV3NameVI") or i.get("industryV3Name"))
        ]
        job_func = item.get("jobFunction") or {}
        parent_fn = job_func.get("parentNameVI") or job_func.get("parentName") or ""
        child_fns = [
            c.get("nameVI") or c.get("name")
            for c in job_func.get("children", [])
            if isinstance(c, dict) and (c.get("nameVI") or c.get("name"))
        ]
        func_str = f"{parent_fn} > {', '.join(child_fns)}" if parent_fn and child_fns else parent_fn

        if ind_v3 and func_str:
            industry_raw = f"{', '.join(ind_v3)} ({func_str})"
        elif ind_v3:
            industry_raw = ", ".join(ind_v3)
        elif func_str:
            industry_raw = func_str
        else:
            ind_list = item.get("industries") or []
            industry_raw = ", ".join([
                ind.get("industryNameVI", "") or ind.get("industryName", "")
                for ind in ind_list
                if isinstance(ind, dict) and (ind.get("industryNameVI") or ind.get("industryName"))
            ])

        # 7. Trình độ học vấn (highestDegreeId mapping)
        degree_mapping = {
            1: "Trung học",
            2: "Trung cấp",
            3: "Cao đẳng",
            4: "Cử nhân",
            5: "Thạc sĩ",
            6: "Tiến sĩ",
            7: "Khác"
        }
        education_raw = degree_mapping.get(item.get("highestDegreeId"), "")

        # 8. Loại hình làm việc & Thời gian làm việc
        working_type_mapping = {
            1: "Toàn thời gian",
            2: "Bán thời gian",
            3: "Thực tập",
            4: "Tạm thời / Dự án",
            5: "Khác"
        }
        working_time_raw = working_type_mapping.get(item.get("typeWorkingId"), "")
        if not working_time_raw and isinstance(item.get("typeWorking"), dict):
            working_time_raw = item.get("typeWorking", {}).get("name", "")

        emp_type = item.get("jobLevelVI") or item.get("jobLevel") or ""
        comp_size = item.get("companySizeVI") or item.get("companySize") or ""

        # 9. Chế độ làm việc (Work mode: Remote / Hybrid / Onsite)
        search_wm = f"{title} {desc_text} {req_text} {loc_str}"
        work_mode_raw = ""
        for wm in ["Full-remote", "Remote", "Hybrid", "Onsite", "Làm từ xa"]:
            if re.search(r'\b' + re.escape(wm) + r'\b', search_wm, re.IGNORECASE):
                work_mode_raw = "Remote" if "remote" in wm.lower() or "từ xa" in wm.lower() else wm
                break
        if not work_mode_raw:
            work_mode_raw = "Onsite"

        # 10. Giới thiệu công ty / Tổng quan
        overview_raw = str(
            item.get("companyProfile")
            or item.get("summary")
            or company_info.get("companyProfile")
            or ""
        ).strip()

        detail_record = {
            "detail_id": f"vietnamworks_{job_id}",
            "source": "vietnamworks",
            "source_job_id": job_id,
            "job_url": job_url,
            "title_raw": title,
            "company_name_raw": comp_name,
            "company_url": comp_url,
            "company_size_raw": comp_size,
            "company_location_raw": comp_loc,
            "industry_raw": industry_raw,
            "salary_raw": salary,
            "experience_raw": exp_str,
            "education_raw": education_raw,
            "location_raw": loc_str,
            "work_mode_raw": work_mode_raw,
            "employment_type_raw": emp_type,
            "working_time_raw": working_time_raw,
            "overview_raw": overview_raw,
            "responsibilities_raw": desc_text,
            "requirements_raw": req_text,
            "benefits_raw": benefits_raw,
            "required_skills_raw": skills_raw,
            "preferred_skills_raw": "",
            "published_at_raw": posted_at,
            "updated_at_raw": updated_at,
            "deadline_raw": deadline,
            "crawled_at": now_iso
        }
        JobDetailRaw(**detail_record)

        return listing_record, detail_record

    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
        """
        Thực thi quy trình cào VietnamWorks:
        1. Tạo cấu trúc thư mục listings/YYYY-MM-DD/ và details/YYYY-MM-DD/
        2. Gom TOÀN BỘ listings của phiên này vào DUY NHẤT 1 file: page_XXX.json
        3. Gom TOÀN BỘ details của phiên này vào DUY NHẤT 1 file: VNWXXX.json
        4. Tự động kiểm tra deduplicate từ các file VNWxxx.json cũ
        5. Phân trang API cho đến khi đạt target_success_count jobs
        """
        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CRAWL VIETNAMWORKS - MỤC TIÊU: {target_success_count} JOBS THÀNH CÔNG")
        self.logger.info(f"Thư mục Listings: {self.listings_dir}")
        self.logger.info(f"Thư mục Details : {self.details_dir}")
        self.logger.info("=" * 70)

        # Lấy danh sách job_id đã cào từ trước để tránh cào lại
        crawled_job_ids = self._get_all_crawled_job_ids()
        self.logger.info(f"Tổng số job VietnamWorks đã cào từ trước: {len(crawled_job_ids)}")

        # Xác định số thứ tự phiên cào hôm nay
        current_run_idx = self._get_next_run_index()
        current_vnw_filename = f"VNW{current_run_idx:03d}.json"
        current_vnw_filepath = os.path.join(self.details_dir, current_vnw_filename)

        current_listing_filename = f"page_{current_run_idx:03d}.json"
        current_listing_filepath = os.path.join(self.listings_dir, current_listing_filename)

        self.logger.info(f"Tất cả listings phiên này sẽ lưu chung vào: {current_listing_filename}")
        self.logger.info(f"Tất cả details phiên này sẽ lưu chung vào : {current_vnw_filename}")

        session_listings: List[Dict[str, Any]] = []
        session_details: List[Dict[str, Any]] = []
        seen_in_session: Set[str] = set()

        session_success_count = 0
        current_page = self.start_page

        while session_success_count < target_success_count:
            needed = target_success_count - session_success_count
            fetch_size = min(self.hits_per_page, needed)

            raw_jobs = self.fetch_api_page(page=current_page, hits_per_page=fetch_size)
            if not raw_jobs:
                self.logger.warning(f"Không nhận được thêm job nào ở page {current_page}. Kết thúc crawl sớm.")
                break

            new_in_page = 0
            for itm in raw_jobs:
                jid = str(itm.get("jobId", ""))
                if not jid:
                    continue

                if jid in crawled_job_ids or jid in seen_in_session:
                    continue

                try:
                    listing_rec, detail_rec = self.parse_job_item(itm)
                    listing_rec["detail_file"] = current_vnw_filename

                    session_listings.append(listing_rec)
                    session_details.append(detail_rec)
                    seen_in_session.add(jid)
                    crawled_job_ids.add(jid)

                    session_success_count += 1
                    new_in_page += 1

                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {jid}: '{detail_rec['title_raw']}' | "
                        f"Cty: '{detail_rec['company_name_raw']}' | "
                        f"Tiến độ: {session_success_count}/{target_success_count}"
                    )

                    if session_success_count >= target_success_count:
                        break
                except Exception as e:
                    self.logger.error(f"Lỗi khi parse job {jid}: {e}")

            # Lưu cập nhật theo từng trang để đảm bảo dữ liệu không bị mất nếu có sự cố
            with open(current_listing_filepath, "w", encoding="utf-8") as f:
                json.dump(session_listings, f, ensure_ascii=False, indent=2)

            with open(current_vnw_filepath, "w", encoding="utf-8") as f:
                json.dump(session_details, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Đã cập nhật file: {current_vnw_filename} ({len(session_details)} jobs), "
                f"{current_listing_filename} ({len(session_listings)} listings)."
            )

            current_page += 1
            time.sleep(random.uniform(self.delay_min, self.delay_max))

        # ==============================================================
        # BÁO CÁO TỔNG KẾT
        # ==============================================================
        self.logger.info("\n" + "=" * 70)
        self.logger.info("BÁO CÁO TỔNG KẾT PHIÊN CÀO VIETNAMWORKS")
        self.logger.info("=" * 70)
        self.logger.info(f"- Số job cào thành công phiên này : {session_success_count}/{target_success_count}")
        self.logger.info(f"- File listing đã lưu             : {current_listing_filename} ({len(session_listings)} listings)")
        self.logger.info(f"- File detail đã lưu              : {current_vnw_filename} ({len(session_details)} jobs)")
        self.logger.info(f"- Thư mục listings                : {self.listings_dir}")
        self.logger.info(f"- Thư mục details                 : {self.details_dir}")
        self.logger.info("=" * 70)

        return {
            "session_success_count": session_success_count,
            "saved_listing_file": current_listing_filename,
            "saved_detail_file": current_vnw_filename,
            "total_listings_in_file": len(session_listings),
            "total_jobs_in_file": len(session_details),
            "listings_dir": self.listings_dir,
            "details_dir": self.details_dir
        }


if __name__ == "__main__":
    crawler = VietnamWorksCrawler()
    crawler.run(target_success_count=10)
