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
from bs4 import BeautifulSoup
from curl_cffi import requests

from src.crawlers.base import BaseCrawler, PROJECT_ROOT
from src.crawlers.topcv.parser import (
    parse_job_card,
    parse_job_detail_html,
    parse_company_overview_html
)


class TopCVCrawler(BaseCrawler):
    """
    Crawler thu thập dữ liệu tuyển dụng IT từ TopCV:
    - Cơ chế Hàng đợi Pending thông minh (ưu tiên cào sạch các job pending trước)
    - Giới hạn trang linh động & Smart Early Stopping khi hết trang web
    - Session Chrome impersonation chống 403 / Cloudflare WAF
    - Quản lý và lưu trữ file listing và detail phân đoạn sạch sẽ
    """

    def __init__(self, config_path: str = "configs/sources.yaml", output_dir: Optional[str] = None):
        full_config_path = os.path.join(PROJECT_ROOT, config_path)
        if not os.path.exists(full_config_path):
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {full_config_path}")

        with open(full_config_path, "r", encoding="utf-8") as f:
            all_configs = yaml.safe_load(f)
            topcv_cfg = all_configs.get("sources", {}).get("topcv", {})

        super().__init__(topcv_cfg)

        self.listing_url_template = self.config.get(
            "listing_url",
            "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?type_keyword=1&disable_auto_detect_type_keyword=1&page={page}&category_family=r257&saturday_status=0&sba=1"
        )
        pagination = self.config.get("pagination", {})
        self.start_page = int(pagination.get("start_page", 1))
        self.max_pages = int(pagination.get("max_pages", 50))

        rate_limit = self.config.get("rate_limit", {})
        self.delay_min = float(rate_limit.get("delay_min", 2.0))
        self.delay_max = float(rate_limit.get("delay_max", 3.5))
        self.timeout = int(rate_limit.get("timeout", 20))

        self.retry_delays = [10, 20, 30]
        self.max_retries = len(self.retry_delays)

        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.base_raw_dir = output_dir if output_dir else os.path.join(PROJECT_ROOT, "data", "raw", "topcv")
        self.listings_dir = os.path.join(self.base_raw_dir, "listings", self.today_str)
        self.details_dir = os.path.join(self.base_raw_dir, "details", self.today_str)

        os.makedirs(self.listings_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)

        self.logger = self._setup_logger()
        self.session = requests.Session(impersonate="chrome124")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.topcv.vn/"
        }
        self.company_cache: Dict[str, str] = {}

    def _setup_logger(self) -> logging.Logger:
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

        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file_path = os.path.join(logs_dir, "topcv.log")
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
                if file_name.startswith("TCV") and file_name.endswith(".json"):
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

    def fetch_job_list_page(self, page: int, max_retries: int = 3) -> List[Dict[str, Any]]:
        url = self.listing_url_template.format(page=page)
        self.logger.info(f"Đang quét danh sách TopCV tại trang {page}: {url}")

        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.select(".job-item-search-result")
                    found_items = []
                    seen = set()

                    for card in cards:
                        item_rec = parse_job_card(card, page)
                        if not item_rec:
                            continue
                        jid = item_rec["source_job_id"]
                        if jid in seen:
                            continue
                        seen.add(jid)
                        found_items.append(item_rec)

                    self.logger.info(f"-> Trang {page} tìm thấy {len(found_items)} jobs TopCV với đầy đủ thông tin tóm tắt.")
                    return found_items

                elif resp.status_code in (403, 429):
                    self.logger.warning(f"-> Trang {page} trả về HTTP status {resp.status_code} (Lần thử {attempt}/{max_retries})")
                    if attempt < max_retries:
                        backoff = 5 * attempt
                        self.logger.info(f"   Đang khởi tạo lại session sạch và chờ {backoff}s trước khi thử lại trang {page}...")
                        self.session = requests.Session(impersonate="chrome124")
                        time.sleep(backoff)
                    else:
                        self.logger.error(f"-> Thất bại khi quét trang {page} sau {max_retries} lần thử do HTTP {resp.status_code}.")
                        return []
                else:
                    self.logger.warning(f"-> Trang {page} trả về HTTP status {resp.status_code}")
                    return []

            except Exception as e:
                self.logger.warning(f"-> Lỗi khi quét danh sách TopCV trang {page} (Lần thử {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    backoff = 5 * attempt
                    self.logger.info(f"   Đang chờ {backoff}s trước khi thử lại trang {page}...")
                    self.session = requests.Session(impersonate="chrome124")
                    time.sleep(backoff)
                else:
                    self.logger.error(f"-> Thất bại khi quét trang {page} sau {max_retries} lần thử: {e}")
                    return []

        return []

    def _fetch_company_overview(self, company_url: str) -> str:
        if not company_url:
            return ""
        if company_url in self.company_cache:
            return self.company_cache[company_url]

        try:
            resp = self.session.get(company_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                desc = parse_company_overview_html(resp.text)
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
                    comp_url = ""
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for s in soup.find_all("script", type="application/ld+json"):
                        try:
                            d = json.loads((s.string if s.string else s.text) or "")
                            if d.get("@type") == "JobPosting":
                                comp_url = (d.get("hiringOrganization") or {}).get("sameAs") or ""
                                break
                        except Exception:
                            continue

                    overview_raw = self._fetch_company_overview(comp_url)
                    detail_record, updated_listing = parse_job_detail_html(
                        resp.text,
                        job_item,
                        company_overview=overview_raw
                    )

                    self.logger.info(
                        f"-> [THÀNH CÔNG] Job {job_id}: '{detail_record['title_raw']}' | Cty: '{detail_record['company_name_raw']}' | "
                        f"Quy mô: '{detail_record['company_size_raw']}' | Trụ sở: '{detail_record['company_location_raw'][:35]}' | Học vấn: '{detail_record['education_raw']}'"
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

    def _collect_pending_jobs(self, crawled_job_ids: Set[str]) -> List[Tuple[str, int, Dict[str, Any]]]:
        pending_items = []
        if not os.path.exists(self.listings_dir):
            return pending_items

        seen_jids = set()
        for f in sorted(os.listdir(self.listings_dir)):
            if f.startswith("page_") and f.endswith(".json"):
                page_path = os.path.join(self.listings_dir, f)
                try:
                    with open(page_path, "r", encoding="utf-8") as pf:
                        items = json.load(pf)
                    for idx, item in enumerate(items):
                        jid = str(item.get("source_job_id", ""))
                        status = item.get("detail_status", "pending")
                        if jid and jid not in crawled_job_ids and jid not in seen_jids and status in ("pending", "failed"):
                            seen_jids.add(jid)
                            pending_items.append((page_path, idx, item))
                except Exception:
                    continue
        return pending_items

    def run(self, target_success_count: int = 100) -> Dict[str, Any]:
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

        # GIAI ĐOẠN 1: Cào các job pending từ trước
        pending_candidates = self._collect_pending_jobs(crawled_job_ids)
        if pending_candidates:
            self.logger.info(f"Phát hiện {len(pending_candidates)} jobs đang ở trạng thái chờ (pending). Ưu tiên cào trước...")

        for page_file_path, item_idx, job_item in pending_candidates:
            if session_success_count >= target_success_count:
                self.logger.info(f"Đã đạt đủ {target_success_count} jobs mục tiêu từ hàng đợi pending! Dừng phiên sớm.")
                break

            jid = str(job_item["source_job_id"])
            detail_res, updated_item = self.fetch_job_detail_with_retry(job_item)

            if detail_res:
                session_details.append(detail_res)
                updated_item["detail_file"] = current_tcv_filename
                crawled_job_ids.add(jid)
                session_success_count += 1

                with open(current_tcv_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_details, f, ensure_ascii=False, indent=2)

                self.logger.info(
                    f"-> [PENDING -> SUCCESS] Job {jid}: '{detail_res['title_raw']}' đã lưu vào {current_tcv_filename} "
                    f"({len(session_details)} jobs). Tiến độ: {session_success_count}/{target_success_count}"
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
                self.logger.warning(f"Không thể cập nhật file listing {page_file_path}: {e}")

            time.sleep(random.uniform(self.delay_min, self.delay_max))

        # GIAI ĐOẠN 2: Quét trang mới từ web nếu chưa đủ target
        current_page = self.start_page
        max_page_limit = self.start_page + self.max_pages
        empty_page_count = 0

        while session_success_count < target_success_count and current_page <= max_page_limit:
            needed = target_success_count - session_success_count
            self.logger.info(f"Cần thêm {needed} jobs thành công. Đang quét trang web TopCV {current_page}...")

            page_items = self.fetch_job_list_page(current_page)
            if not page_items:
                empty_page_count += 1
                self.logger.warning(f"Không nhận được job nào ở trang {current_page}.")
                if empty_page_count >= 2:
                    self.logger.info(f"Đã chạm trang cuối cùng hoặc hết dữ liệu từ website (trang {current_page}). Dừng quét trang mới.")
                    break
                current_page += 1
                time.sleep(random.uniform(self.delay_min, self.delay_max))
                continue

            empty_page_count = 0

            new_jobs = []
            for itm in page_items:
                jid = str(itm["source_job_id"])
                if jid not in seen_in_session and jid not in crawled_job_ids:
                    seen_in_session.add(jid)
                    session_listings.append(itm)
                    new_jobs.append(itm)

            with open(current_listing_filepath, "w", encoding="utf-8") as f:
                json.dump(session_listings, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Trang {current_page}: Thu thập được {len(new_jobs)} jobs mới chưa cào.")

            if not new_jobs:
                self.logger.info(f"Trang {current_page}: Không có job mới chưa cào. Chuyển sang trang tiếp theo sau khi nghỉ...")
                current_page += 1
                time.sleep(random.uniform(self.delay_min, self.delay_max))
                continue

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

                    with open(current_tcv_filepath, "w", encoding="utf-8") as f:
                        json.dump(session_details, f, ensure_ascii=False, indent=2)

                    self.logger.info(
                        f"-> Đã lưu job {jid} vào {current_tcv_filename} "
                        f"({len(session_details)} jobs). Tiến độ: {session_success_count}/{target_success_count}"
                    )
                else:
                    failed_count_session += 1

                with open(current_listing_filepath, "w", encoding="utf-8") as f:
                    json.dump(session_listings, f, ensure_ascii=False, indent=2)

                time.sleep(random.uniform(self.delay_min, self.delay_max))

            current_page += 1
            time.sleep(random.uniform(self.delay_min, self.delay_max))

        # Báo cáo tổng kết
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
        self.logger.info(f"BẮT ĐẦU CÀO BÙ (RETRY FAILED) CHO TOPCV - NGÀY: {date_str}")
        self.logger.info("=" * 70)

        total_failed = 0
        recovered = 0
        still_failed = 0

        os.makedirs(detail_folder, exist_ok=True)
        detail_files = sorted([f for f in os.listdir(detail_folder) if f.startswith("TCV") and f.endswith(".json")])
        if detail_files:
            target_detail_file = detail_files[-1]
            target_detail_path = os.path.join(detail_folder, target_detail_file)
            with open(target_detail_path, "r", encoding="utf-8") as f:
                try:
                    detail_records = json.load(f)
                except Exception:
                    detail_records = []
        else:
            target_detail_file = "TCV001.json"
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
        self.logger.info("TỔNG KẾT CÀO BÙ TOPCV")
        self.logger.info("=" * 70)
        self.logger.info(f"- Tổng số job lỗi tìm thấy: {total_failed}")
        self.logger.info(f"- Cào bù thành công        : {recovered}")
        self.logger.info(f"- Vẫn thất bại            : {still_failed}")
        self.logger.info("=" * 70)

        return {"total_failed": total_failed, "recovered": recovered, "still_failed": still_failed}


if __name__ == "__main__":
    crawler = TopCVCrawler()
    crawler.run(target_success_count=5)
