import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from curl_cffi import requests

from src.crawlers.base import BaseCrawler, PROJECT_ROOT
from src.crawlers.topdev.parser import (
    parse_job_listings_from_html,
    parse_job_detail_html
)


class TopDevCrawler(BaseCrawler):
    """
    Crawler thu thập dữ liệu tuyển dụng IT từ TopDev:
    - Bóc tách dữ liệu gốc từ Next.js App Router (RSC stream)
    - Quản lý hàng đợi job pending & cào bù tự động
    - Giới hạn trang linh động với cơ chế Smart Stop khi hết dữ liệu
    """

    def __init__(self, config_path: str = "configs/sources.yaml", output_dir: Optional[str] = None):
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            topdev_cfg = all_configs.get("sources", {}).get("topdev", {})

        super().__init__(topdev_cfg)

        self.listing_url_template = self.config.get(
            "listing_url",
            "https://topdev.vn/viec-lam/tim-kiem?job_categories_ids=2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2C11%2C12%2C13%2C67&page={page}"
        )
        pagination = self.config.get("pagination", {})
        self.start_page = int(pagination.get("start_page", 1))
        self.max_pages = int(pagination.get("max_pages", 50))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 1.2))
        self.delay_max = float(rate_limit.get("delay_max", 2.0))
        self.timeout = int(rate_limit.get("timeout", 20))

        self.retry_delays = [15, 30, 45]
        self.max_retries = len(self.retry_delays)

        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = output_dir if output_dir else os.path.join(PROJECT_ROOT, "data", "raw", "topdev")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        self.logger = self._setup_logger()
        self.session = requests.Session(impersonate="chrome124")

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("TopDevCrawler")
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        log_format = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [TopDev] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "topdev.log")
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
                if file_name.startswith("TC") and file_name.endswith(".json"):
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

    def _collect_retry_jobs(self, crawled_job_ids: Set[str]) -> List[Tuple[str, int, Dict[str, Any]]]:
        retry_items = []
        if not os.path.exists(self.listings_dir):
            return retry_items

        for f in sorted(os.listdir(self.listings_dir)):
            if f.startswith("page_") and f.endswith(".json"):
                page_path = os.path.join(self.listings_dir, f)
                try:
                    with open(page_path, "r", encoding="utf-8") as pf:
                        items = json.load(pf)
                    for idx, item in enumerate(items):
                        jid = str(item.get("source_job_id", ""))
                        status = item.get("detail_status", "pending")
                        if jid and jid not in crawled_job_ids and status in ["failed", "pending"]:
                            retry_items.append((page_path, idx, item))
                except Exception:
                    continue
        return retry_items

    def _get_next_run_index(self) -> int:
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

    def fetch_job_list_page(self, page: int) -> List[Dict[str, Any]]:
        url = self.listing_url_template.format(page=page)
        self.logger.info(f"Đang quét danh sách tại trang {page}: {url}")

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                self.logger.warning(f"Trang {page} trả về HTTP status {resp.status_code}")
                return []

            items = parse_job_listings_from_html(resp.text, page)
            self.logger.info(f"-> Trang {page} tìm thấy {len(items)} jobs với đầy đủ thông tin tóm tắt.")
            return items
        except Exception as e:
            self.logger.error(f"Lỗi khi cào trang listing {page}: {e}")
            return []

    def fetch_job_detail_with_retry(
        self,
        job_item: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        job_url = job_item["job_url"]
        job_id = str(job_item["source_job_id"])
        updated_listing = dict(job_item)

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            updated_listing["detail_attempts"] = attempt
            try:
                self.logger.info(f"Đang tải chi tiết Job {job_id} (Lần thử {attempt}/{self.max_retries}): {job_url}")
                resp = self.session.get(job_url, timeout=self.timeout)
                updated_listing["detail_http_status"] = resp.status_code

                if resp.status_code == 200:
                    detail_record, updated_listing = parse_job_detail_html(resp.text, job_item)
                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {job_id}: '{detail_record['title_raw']}' | Cty: '{detail_record['company_name_raw']}' | "
                        f"Cấp bậc: '{detail_record['employment_type_raw']}' | KN: '{detail_record['experience_raw']}' | Lương: '{detail_record['salary_raw']}'"
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
        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CRAWL TOPDEV - MỤC TIÊU: {target_success_count} JOBS THÀNH CÔNG")
        self.logger.info(f"Thư mục Listings: {self.listings_dir}")
        self.logger.info(f"Thư mục Details : {self.details_dir}")
        self.logger.info("=" * 70)

        crawled_job_ids = self._get_all_crawled_job_ids()
        self.logger.info(f"Tổng số job chi tiết đã cào thành công từ trước: {len(crawled_job_ids)}")

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

        # GIAI ĐOẠN 1: Cào các job pending / retry cũ
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

                with open(current_tc_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_details_list, f, ensure_ascii=False, indent=2)

                self.logger.info(
                    f"-> Đã lưu job {jid} vào {current_tc_filename} "
                    f"({len(session_details_list)} jobs trong file). Tiến độ: {session_success_count}/{target_success_count}"
                )
            else:
                failed_count_session += 1

            try:
                with open(page_file_path, "r", encoding="utf-8") as f:
                    page_items = json.load(f)
                page_items[item_idx] = updated_item
                with open(page_file_path, "w", encoding="utf-8") as f:
                    json.dump(page_items, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.warning(f"Không thể cập nhật lại file {page_file_path}: {e}")

            time.sleep(random.uniform(self.delay_min, self.delay_max))

        # GIAI ĐOẠN 2: Quét thêm trang mới nếu chưa đủ target
        current_page = self.start_page
        max_page_limit = self.start_page + self.max_pages
        empty_page_count = 0

        while session_success_count < target_success_count and current_page <= max_page_limit:
            needed = target_success_count - session_success_count
            self.logger.info(f"Cần thêm {needed} job thành công. Đang quét trang web {current_page}...")

            page_items = self.fetch_job_list_page(current_page)
            if not page_items:
                empty_page_count += 1
                self.logger.warning(f"Không có dữ liệu từ page {current_page}.")
                if empty_page_count >= 2:
                    self.logger.info(f"Đã chạm trang cuối cùng của website TopDev (trang {current_page}). Tự động dừng quét trang mới.")
                    break
                current_page += 1
                time.sleep(random.uniform(self.delay_min, self.delay_max))
                continue

            empty_page_count = 0

            new_jobs = []
            for itm in page_items:
                jid = str(itm["source_job_id"])
                if jid not in seen_listing_ids and jid not in crawled_job_ids:
                    seen_listing_ids.add(jid)
                    session_listings_list.append(itm)
                    new_jobs.append(itm)

            with open(current_listing_filepath, "w", encoding="utf-8") as f:
                json.dump(session_listings_list, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Trang {current_page}: Thu thập thêm {len(new_jobs)} jobs mới chưa cào.")

            for itm in new_jobs:
                if session_success_count >= target_success_count:
                    break

                jid = str(itm["source_job_id"])
                detail_res, updated_item = self.fetch_job_detail_with_retry(itm)
                itm.update(updated_item)

                if detail_res:
                    session_details_list.append(detail_res)
                    itm["detail_file"] = current_tc_filename
                    crawled_job_ids.add(jid)
                    session_success_count += 1

                    with open(current_tc_filepath, "w", encoding="utf-8") as f:
                        json.dump(session_details_list, f, ensure_ascii=False, indent=2)

                    self.logger.info(
                        f"-> Đã lưu job {jid} vào {current_tc_filename} "
                        f"({len(session_details_list)} jobs trong file). Tiến độ: {session_success_count}/{target_success_count}"
                    )
                else:
                    failed_count_session += 1

                with open(current_listing_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_listings_list, f, ensure_ascii=False, indent=2)

                time.sleep(random.uniform(self.delay_min, self.delay_max))

            current_page += 1

        # Báo cáo tổng kết
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

    def retry_failed_jobs(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        date_str = target_date or self.today_str
        listing_folder = os.path.join(self.base_raw_dir, "listings", date_str)
        detail_folder = os.path.join(self.base_raw_dir, "details", date_str)

        if not os.path.exists(listing_folder):
            self.logger.warning(f"Không tìm thấy thư mục listings của ngày {date_str}: {listing_folder}")
            return {"total_failed": 0, "recovered": 0, "still_failed": 0}

        listing_files = sorted([f for f in os.listdir(listing_folder) if f.startswith("page_") and f.endswith(".json")])
        if not listing_files:
            self.logger.warning(f"Không có file listings nào trong ngày {date_str}.")
            return {"total_failed": 0, "recovered": 0, "still_failed": 0}

        self.logger.info("=" * 70)
        self.logger.info(f"BẮT ĐẦU CÀO BÙ (RETRY FAILED) CHO TOPDEV - NGÀY: {date_str}")
        self.logger.info("=" * 70)

        total_failed = 0
        recovered = 0
        still_failed = 0

        os.makedirs(detail_folder, exist_ok=True)
        detail_files = sorted([f for f in os.listdir(detail_folder) if f.startswith("TC") and f.endswith(".json")])
        if detail_files:
            target_detail_file = detail_files[-1]
            target_detail_path = os.path.join(detail_folder, target_detail_file)
            with open(target_detail_path, "r", encoding="utf-8") as f:
                try:
                    detail_records = json.load(f)
                except Exception:
                    detail_records = []
        else:
            target_detail_file = "TC001.json"
            target_detail_path = os.path.join(detail_folder, target_detail_file)
            detail_records = []

        for lf in listing_files:
            lpath = os.path.join(listing_folder, lf)
            with open(lpath, "r", encoding="utf-8") as f:
                try:
                    items = json.load(f)
                except Exception:
                    continue

            failed_items = [itm for itm in items if itm.get("detail_status") == "failed"]
            if not failed_items:
                continue

            self.logger.info(f"File {lf} có {len(failed_items)} jobs bị lỗi cần cào lại...")
            total_failed += len(failed_items)

            modified = False
            for itm in failed_items:
                jid = str(itm["source_job_id"])
                title = itm.get("title_raw", "")
                self.logger.info(f"-> Đang cào bù Job {jid}: '{title}'...")

                detail_res, updated_item = self.fetch_job_detail_with_retry(itm)
                itm.update(updated_item)

                if detail_res:
                    detail_records.append(detail_res)
                    itm["detail_status"] = "success"
                    itm["detail_file"] = target_detail_file
                    itm["detail_error"] = ""
                    itm["detail_crawled_at"] = datetime.now().isoformat()
                    recovered += 1
                    modified = True

                    with open(target_detail_path, "w", encoding="utf-8") as df_file:
                        json.dump(detail_records, df_file, ensure_ascii=False, indent=2)

                    self.logger.info(f"   [CÀO BÙ THÀNH CÔNG] Đã lưu vào {target_detail_file}.")
                else:
                    still_failed += 1
                    modified = True
                    self.logger.warning(f"   [VẪN THẤT BẠI] Job {jid} vẫn chưa cào được.")

                time.sleep(random.uniform(self.delay_min, self.delay_max))

            if modified:
                with open(lpath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)

        self.logger.info("\n" + "=" * 70)
        self.logger.info("TỔNG KẾT CÀO BÙ TOPDEV")
        self.logger.info("=" * 70)
        self.logger.info(f"- Tổng số job lỗi tìm thấy: {total_failed}")
        self.logger.info(f"- Cào bù thành công        : {recovered}")
        self.logger.info(f"- Vẫn thất bại            : {still_failed}")
        self.logger.info("=" * 70)

        return {"total_failed": total_failed, "recovered": recovered, "still_failed": still_failed}


if __name__ == "__main__":
    crawler = TopDevCrawler()
    crawler.run(target_success_count=5)
