import os
import sys
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.crawlers.topdev import TopDevCrawler
from src.crawlers.vietnamworks import VietnamWorksCrawler
from src.crawlers.topcv import TopCVCrawler
from src.quality.validator import QualityValidator
from main_quality import load_raw_listings, load_raw_details
from src.pipelines.silver.db import get_db_connection
from src.pipelines.silver.extractor import load_bronze_data
from src.pipelines.silver.runner import (
    run_companies_pipeline,
    run_skills_pipeline,
    run_jobs_pipeline,
    run_job_descriptions_pipeline,
    run_job_skills_pipeline,
    run_job_source_records_pipeline,
    run_job_snapshots_pipeline
)

router = APIRouter(prefix="/api/crawler", tags=["Crawler & Data Sync"])

# Bộ nhớ trạng thái tiến trình cào và đồng bộ dữ liệu
_SYNC_LOCK = threading.Lock()
_SYNC_STATE: Dict[str, Any] = {
    "status": "idle",       # idle | running | completed | error
    "progress": 0,          # 0 - 100
    "step": "Sẵn sàng",
    "logs": [],
    "summary": None,
    "started_at": None,
    "finished_at": None,
    "error_message": None
}

class MemoryLogHandler(logging.Handler):
    """Handler thu thập log thời gian thực vào bộ nhớ để phục vụ Frontend."""
    def __init__(self, logs_list: List[Dict[str, str]], lock: threading.Lock):
        super().__init__()
        self.logs_list = logs_list
        self.lock = lock

    def emit(self, record):
        try:
            msg = self.format(record)
            now_str = datetime.now().strftime("%H:%M:%S")
            with self.lock:
                self.logs_list.append({"time": now_str, "level": record.levelname, "message": msg})
                # Giữ tối đa 300 dòng log gần nhất
                if len(self.logs_list) > 300:
                    del self.logs_list[: len(self.logs_list) - 300]
        except Exception:
            pass

def _add_log(msg: str, level: str = "INFO"):
    now_str = datetime.now().strftime("%H:%M:%S")
    with _SYNC_LOCK:
        _SYNC_STATE["logs"].append({"time": now_str, "level": level, "message": msg})
        if len(_SYNC_STATE["logs"]) > 300:
            del _SYNC_STATE["logs"][: len(_SYNC_STATE["logs"]) - 300]

class CrawlSyncRequest(BaseModel):
    source: str = Field(default="all", description="Nguồn cào: all, topdev, vietnamworks, topcv")
    target: int = Field(default=5, ge=1, le=50, description="Mục tiêu số tin cần cào cho mỗi nguồn (1-50)")
    run_etl: bool = Field(default=True, description="Tự động chạy Silver ETL nạp vào PostgreSQL")

def _run_sync_worker(source: str, target: int, run_etl: bool):
    global _SYNC_STATE
    start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")

    crawler_map = {
        "topdev": ("TopDev", TopDevCrawler),
        "vietnamworks": ("VietnamWorks", VietnamWorksCrawler),
        "topcv": ("TopCV", TopCVCrawler)
    }

    selected_keys = list(crawler_map.keys()) if source == "all" else [source]
    total_sources = len(selected_keys)

    mem_handler = MemoryLogHandler(_SYNC_STATE["logs"], _SYNC_LOCK)
    mem_handler.setFormatter(logging.Formatter("%(message)s"))

    # Đăng ký handler vào các logger của crawler
    for name in ["TopDev", "VietnamWorks", "TopCV"]:
        lg = logging.getLogger(name)
        lg.addHandler(mem_handler)

    try:
        _add_log(f"Bắt đầu quy trình thu thập dữ liệu tự động. Nguồn: {', '.join(selected_keys)}, Mục tiêu: {target} tin/nguồn.")

        # Lấy tổng số jobs trước khi nạp
        jobs_before = 0
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM jobs;")
                    jobs_before = cur.fetchone()[0]
        except Exception as e:
            _add_log(f"Không thể kiểm tra số lượng việc làm ban đầu: {e}", "WARNING")

        crawl_results = {}
        total_scraped_session = 0

        # GIAI ĐOẠN 1: CÀO DỮ LIỆU TỪ CÁC SÀN
        for idx, s_key in enumerate(selected_keys):
            s_name, c_cls = crawler_map[s_key]
            step_progress = int(10 + (idx / total_sources) * 40)
            with _SYNC_LOCK:
                _SYNC_STATE["progress"] = step_progress
                _SYNC_STATE["step"] = f"Đang cào dữ liệu từ sàn {s_name}..."

            _add_log(f">>> [BƯỚC 1/{total_sources}] Khởi động Crawler cho {s_name} (Mục tiêu: {target} tin) <<<")

            try:
                crawler = c_cls()
                res = crawler.run(target_success_count=target)
                crawl_results[s_name] = res
                succ = res.get("session_success_count", 0)
                total_scraped_session += succ
                _add_log(f"-> Thu thập thành công {succ} tin từ {s_name}.")
            except Exception as e:
                _add_log(f"Lỗi khi cào dữ liệu từ {s_name}: {e}", "ERROR")
                crawl_results[s_name] = {"error": str(e), "session_success_count": 0}

        # GIAI ĐOẠN 2: KIỂM ĐỊNH CHẤT LƯỢNG DỮ LIỆU & NẠP VÀO BRONZE
        with _SYNC_LOCK:
            _SYNC_STATE["progress"] = 55
            _SYNC_STATE["step"] = "Đang kiểm định chất lượng dữ liệu tầng Bronze (QualityValidator)..."

        _add_log(">>> [BƯỚC 2] Bắt đầu kiểm định chất lượng dữ liệu tầng Bronze <<<")
        validator = QualityValidator()
        all_today_listings = []
        all_today_details = []

        for s_key in selected_keys:
            listings = load_raw_listings(s_key, target_date=today_str)
            details = load_raw_details(s_key, target_date=today_str)
            all_today_listings.extend(listings)
            all_today_details.extend(details)

        _add_log(f"Tổng hợp đợt cào hôm nay: {len(all_today_listings)} listings và {len(all_today_details)} details.")

        valid_records, quarantine_records, invalid_records, val_summary = validator.route_records(all_today_details)
        _add_log(f"Kết quả kiểm định: {len(valid_records)} tin Valid, {len(quarantine_records)} tin Quarantine, {len(invalid_records)} tin Invalid.")

        _, new_listings_added, total_listings_master = validator.save_master_listings(all_today_listings)
        _, new_details_added, total_details_master = validator.save_master_details_valid(valid_records)

        _add_log(f"Đã lưu tích lũy Master Bronze: Bổ sung {new_details_added} tin chi tiết hợp lệ mới (Tổng Bronze: {total_details_master:,}).")

        # GIAI ĐOẠN 3: NẠP VÀO CƠ SỞ DỮ LIỆU SILVER & GOLD POSTGRESQL
        jobs_after = jobs_before
        if run_etl:
            with _SYNC_LOCK:
                _SYNC_STATE["progress"] = 70
                _SYNC_STATE["step"] = "Đang làm sạch và nạp dữ liệu vào PostgreSQL (Silver & Gold)..."

            _add_log(">>> [BƯỚC 3] Bắt đầu nạp dữ liệu chuẩn hóa vào PostgreSQL <<<")
            bronze_data = load_bronze_data(force_reload=True)
            _add_log(f"Nạp Bronze Data thành công: {len(bronze_data['df_merged']):,} tin việc làm cần xử lý.")

            with get_db_connection() as conn:
                run_companies_pipeline(bronze_data, conn)
                with _SYNC_LOCK:
                    _SYNC_STATE["progress"] = 78

                run_jobs_pipeline(bronze_data, conn)
                with _SYNC_LOCK:
                    _SYNC_STATE["progress"] = 85

                run_job_descriptions_pipeline(bronze_data, conn)
                run_job_skills_pipeline(bronze_data, conn)
                with _SYNC_LOCK:
                    _SYNC_STATE["progress"] = 92

                run_job_source_records_pipeline(bronze_data, conn)
                run_job_snapshots_pipeline(bronze_data, conn)

                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM jobs;")
                    jobs_after = cur.fetchone()[0]

            _add_log(f"Nạp Silver Database thành công! Số việc làm hiện tại: {jobs_after:,} (Tăng thêm: {jobs_after - jobs_before:,} tin).")

        elapsed_sec = round(time.time() - start_time, 1)
        summary_data = {
            "sources": selected_keys,
            "target_per_source": target,
            "scraped_count": total_scraped_session,
            "valid_count": len(valid_records),
            "new_bronze_details": new_details_added,
            "total_bronze_master": total_details_master,
            "jobs_before_db": jobs_before,
            "jobs_after_db": jobs_after,
            "new_jobs_added_db": max(0, jobs_after - jobs_before),
            "elapsed_seconds": elapsed_sec,
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with _SYNC_LOCK:
            _SYNC_STATE["progress"] = 100
            _SYNC_STATE["status"] = "completed"
            _SYNC_STATE["step"] = "Hoàn tất thu thập và cập nhật dữ liệu thành công!"
            _SYNC_STATE["finished_at"] = summary_data["finished_at"]
            _SYNC_STATE["summary"] = summary_data

        _add_log(f"Hoàn thành toàn bộ quy trình trong {elapsed_sec}s! Sẵn sàng phục vụ người dùng.")

    except Exception as e:
        err_msg = str(e)
        _add_log(f"Gặp lỗi trong quá trình thu thập/cập nhật dữ liệu: {err_msg}", "ERROR")
        with _SYNC_LOCK:
            _SYNC_STATE["status"] = "error"
            _SYNC_STATE["step"] = "Gặp lỗi trong quá trình thực thi"
            _SYNC_STATE["error_message"] = err_msg
            _SYNC_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    finally:
        for name in ["TopDev", "VietnamWorks", "TopCV"]:
            lg = logging.getLogger(name)
            lg.removeHandler(mem_handler)

@router.post("/trigger")
def trigger_crawl_and_sync(payload: CrawlSyncRequest, background_tasks: BackgroundTasks):
    """
    Kích hoạt tiến trình cào dữ liệu mới từ các sàn và tự động chuẩn hóa, nạp vào CSDL.
    Chạy bất đồng bộ dưới nền (Background Thread), cho phép Frontend theo dõi tiến trình qua SSE/polling.
    """
    global _SYNC_STATE
    with _SYNC_LOCK:
        if _SYNC_STATE["status"] == "running":
            return {
                "success": False,
                "message": "Một tác vụ thu thập và đồng bộ đang được thực hiện. Vui lòng đợi hoàn tất.",
                "state": _SYNC_STATE
            }

        _SYNC_STATE["status"] = "running"
        _SYNC_STATE["progress"] = 5
        _SYNC_STATE["step"] = "Khởi tạo môi trường cào dữ liệu..."
        _SYNC_STATE["logs"] = []
        _SYNC_STATE["summary"] = None
        _SYNC_STATE["error_message"] = None
        _SYNC_STATE["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _SYNC_STATE["finished_at"] = None

    worker_thread = threading.Thread(
        target=_run_sync_worker,
        args=(payload.source, payload.target, payload.run_etl),
        daemon=True
    )
    worker_thread.start()

    return {
        "success": True,
        "message": f"Đã bắt đầu tiến trình cào dữ liệu từ nguồn '{payload.source}' (Mục tiêu: {payload.target} tin).",
        "state": _SYNC_STATE
    }

@router.get("/status")
def get_sync_status():
    """Lấy trạng thái hiện tại của tác vụ cào và cập nhật dữ liệu."""
    with _SYNC_LOCK:
        return {
            "status": _SYNC_STATE["status"],
            "progress": _SYNC_STATE["progress"],
            "step": _SYNC_STATE["step"],
            "logs_count": len(_SYNC_STATE["logs"]),
            "logs": _SYNC_STATE["logs"][-50:],  # Trả về 50 dòng log gần nhất
            "summary": _SYNC_STATE["summary"],
            "started_at": _SYNC_STATE["started_at"],
            "finished_at": _SYNC_STATE["finished_at"],
            "error_message": _SYNC_STATE["error_message"]
        }

@router.post("/reset")
def reset_sync_status():
    """Đặt lại trạng thái về idle sau khi hoàn tất hoặc lỗi."""
    global _SYNC_STATE
    with _SYNC_LOCK:
        if _SYNC_STATE["status"] != "running":
            _SYNC_STATE["status"] = "idle"
            _SYNC_STATE["progress"] = 0
            _SYNC_STATE["step"] = "Sẵn sàng"
            _SYNC_STATE["logs"] = []
            _SYNC_STATE["summary"] = None
            _SYNC_STATE["error_message"] = None
            _SYNC_STATE["started_at"] = None
            _SYNC_STATE["finished_at"] = None
            return {"success": True, "message": "Đã đặt lại trạng thái về sẵn sàng."}
        else:
            return {"success": False, "message": "Tiến trình đang chạy, không thể đặt lại."}
