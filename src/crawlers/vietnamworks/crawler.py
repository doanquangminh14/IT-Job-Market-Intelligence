import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import yaml
from curl_cffi import requests

from src.crawlers.base import BaseCrawler, PROJECT_ROOT
from src.crawlers.vietnamworks.parser import parse_job_item


class VietnamWorksCrawler(BaseCrawler):
    """
    Crawler thu thập dữ liệu tuyển dụng IT từ VietnamWorks qua API:
    - POST API endpoint: ms.vietnamworks.com/job-search/v1.0/search
    - Phân trang hits_per_page linh động, có max_pages và Smart Stop
    - Tự động kiểm tra deduplicate các job đã cào
    """

    def __init__(self, config_path: str = "configs/sources.yaml"):
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            vnw_cfg = all_configs.get("sources", {}).get("vietnamworks", {})

        super().__init__(vnw_cfg)

        self.api_endpoint = self.config.get(
            "api_endpoint",
            "https://ms.vietnamworks.com/job-search/v1.0/search"
        )
        self.default_headers = self.config.get("headers", {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
        self.max_pages = int(pagination.get("max_pages", 50))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 0.5))
        self.delay_max = float(rate_limit.get("delay_max", 1.0))
        self.timeout = int(rate_limit.get("timeout", 20))

        self.retry_delays = [5, 10, 20]
        self.max_retries = len(self.retry_delays)

        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw", "vietnamworks")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        self.logger = self._setup_logger()
        self.session = requests.Session(impersonate="chrome124")

    def _setup_logger(self) -> logging.Logger:
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

        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "vietnamworks.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        return logger

    def _get_all_crawled_job_ids(self) -> Set[str]:
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
                            records = json.load(f)
                            for rec in records:
                                jid = str(rec.get("source_job_id", ""))
                                if jid:
                                    crawled_ids.add(jid)
                    except Exception:
                        pass
        return crawled_ids

    def _get_next_run_index(self) -> int:
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

    def fetch_api_page(self, page: int, hits_per_page: Optional[int] = None) -> List[Dict[str, Any]]:
        hits = hits_per_page or self.hits_per_page
        payload = dict(self.default_payload)
        payload.update({
            "page": page,
            "hitsPerPage": hits
        })

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    f"Gửi request API trang {page} (hits: {hits}) - Lần thử {attempt}/{self.max_retries}"
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

    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CRAWL VIETNAMWORKS - MỤC TIÊU: {target_success_count} JOBS THÀNH CÔNG")
        self.logger.info(f"Thư mục Listings: {self.listings_dir}")
        self.logger.info(f"Thư mục Details : {self.details_dir}")
        self.logger.info("=" * 70)

        crawled_job_ids = self._get_all_crawled_job_ids()
        self.logger.info(f"Tổng số job VietnamWorks đã cào từ trước: {len(crawled_job_ids)}")

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
        max_page_limit = self.start_page + self.max_pages

        while session_success_count < target_success_count and current_page <= max_page_limit:
            needed = target_success_count - session_success_count
            fetch_size = min(self.hits_per_page, needed)

            raw_jobs = self.fetch_api_page(page=current_page, hits_per_page=fetch_size)
            if not raw_jobs:
                self.logger.info(f"Đã chạm trang cuối cùng hoặc hết dữ liệu từ VietnamWorks API (page {current_page}). Dừng phiên sớm.")
                break

            for itm in raw_jobs:
                jid = str(itm.get("jobId", ""))
                if not jid:
                    continue

                if jid in crawled_job_ids or jid in seen_in_session:
                    continue

                try:
                    listing_rec, detail_rec = parse_job_item(itm)
                    listing_rec["detail_file"] = current_vnw_filename

                    session_listings.append(listing_rec)
                    session_details.append(detail_rec)
                    seen_in_session.add(jid)
                    crawled_job_ids.add(jid)

                    session_success_count += 1

                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {jid}: '{detail_rec['title_raw']}' | "
                        f"Cty: '{detail_rec['company_name_raw']}' | "
                        f"Tiến độ: {session_success_count}/{target_success_count}"
                    )

                    if session_success_count >= target_success_count:
                        break
                except Exception as e:
                    self.logger.error(f"Lỗi khi parse job {jid}: {e}")

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

        # Báo cáo tổng kết
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
            "failed_count": 0,
            "saved_listing_file": current_listing_filename,
            "saved_detail_file": current_vnw_filename,
            "total_listings_in_file": len(session_listings),
            "total_jobs_in_file": len(session_details),
            "listings_dir": self.listings_dir,
            "details_dir": self.details_dir
        }

    def retry_failed_jobs(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """VietnamWorks tải trực tiếp thông tin chi tiết qua API nên không có job pending."""
        self.logger.info("VietnamWorks: Tất cả jobs được cào trực tiếp qua API nên không có job lỗi cần cào bù.")
        return {"total_failed": 0, "recovered": 0, "still_failed": 0}


if __name__ == "__main__":
    crawler = VietnamWorksCrawler()
    crawler.run(target_success_count=5)
