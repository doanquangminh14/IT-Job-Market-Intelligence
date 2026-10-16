import argparse
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
    run_job_snapshots_pipeline,
    run_dq_results_pipeline
)


def get_current_db_job_stats() -> Dict[str, int]:
    """Lấy số lượng việc làm hiện có trong cơ sở dữ liệu PostgreSQL."""
    stats = {"total_jobs": 0, "active_jobs": 0, "total_companies": 0}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM jobs;")
                stats["total_jobs"] = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM jobs WHERE is_active = true;")
                stats["active_jobs"] = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM companies;")
                stats["total_companies"] = cur.fetchone()[0]
    except Exception as e:
        print(f"[Canh bao] Khong the truy van database PostgreSQL: {e}")
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="IT Job Market Intelligence - Bo Dieu Phoi Toan Dien (End-to-End Pipeline Runner)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        choices=["topdev", "vietnamworks", "topcv", "all"],
        help="Nguon tuyen dung can cao: topdev | vietnamworks | topcv | all (mac dinh: all)"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=100,
        help="Muc tieu so tin viec lam can lay thanh cong cho moi nguon (mac dinh: 100)"
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Bo qua buoc cao du lieu, chi chay kiem dinh Bronze va nap Silver PostgreSQL"
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Che do cao bu: Quet va thu cao lai cac tin loi cu trong listing"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Ngay can kiem dinh Bronze YYYY-MM-DD (mac dinh: toan bo lich su)"
    )

    args = parser.parse_args()

    pipeline_start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")

    print("=" * 80)
    print("   IT JOB MARKET INTELLIGENCE - END-TO-END PIPELINE RUNNER")
    print(f"   Thoi gian khoi chay : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Pham vi nguon       : {args.source.upper()}")
    print(f"   Muc tieu moi nguon  : {args.target} jobs chi tiet")
    print(f"   Che do cao bu       : {'BAT' if args.retry_failed else 'TAT'}")
    print(f"   Bo qua buoc cao     : {'BAT' if args.skip_crawl else 'TAT'}")
    print("=" * 80)

    # Thong ke Database truoc khi nap
    initial_stats = get_current_db_job_stats()
    print(f"\n[Trang thai Database ban dau]: {initial_stats['total_jobs']:,} tin tong cong ({initial_stats['active_jobs']:,} active), {initial_stats['total_companies']:,} doanh nghiep.\n")

    crawler_map = {
        "topdev": ("TopDev", TopDevCrawler),
        "vietnamworks": ("VietnamWorks", VietnamWorksCrawler),
        "topcv": ("TopCV", TopCVCrawler)
    }

    selected_sources = list(crawler_map.keys()) if args.source == "all" else [args.source]
    crawl_results: Dict[str, Any] = {}
    total_crawled_session = 0

    # -------------------------------------------------------------------------
    # GIAI DOAN 1: CRAWL DU LIEU (TIEN TRINH THU THAP DU LIEU)
    # -------------------------------------------------------------------------
    if not args.skip_crawl:
        print("\n" + "#" * 80)
        print(">>> [GIAI DOAN 1/3] THU THAP DU LIEU TU CAC SAN (CRAWLER RUNNER) <<<")
        print("#" * 80)

        for src_key in selected_sources:
            src_name, crawler_cls = crawler_map[src_key]
            print(f"\n--- [KHOI CHAY CRAWLER: {src_name.upper()}] (Target: {args.target}) ---")
            try:
                crawler = crawler_cls()
                if args.retry_failed:
                    res = crawler.retry_failed_jobs(target_date=args.date)
                else:
                    res = crawler.run(target_success_count=args.target)
                crawl_results[src_name] = res
                succ = res.get("session_success_count", 0)
                total_crawled_session += succ
                print(f"--- [HOAN TAT CRAWLER: {src_name.upper()}] Dat: {succ}/{args.target} tin thanh cong ---")
            except Exception as e:
                print(f"[LOI] Gap su co khi chay crawler {src_name}: {e}")
                crawl_results[src_name] = {"error": str(e), "session_success_count": 0}
    else:
        print("\n[GIAI DOAN 1/3]: Bo qua buoc cao du lieu theo chi dinh (--skip-crawl).")

    # -------------------------------------------------------------------------
    # GIAI DOAN 2: KIEM DINH CHAT LUONG & TICH LUY BRONZE (QUALITY VALIDATOR)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print(">>> [GIAI DOAN 2/3] KIEM DINH CHAT LUONG & TICH LUY MASTER BRONZE <<<")
    print("#" * 80)

    validator = QualityValidator()
    all_listings: List[Dict[str, Any]] = []
    all_details: List[Dict[str, Any]] = []

    for src_key in ["topcv", "topdev", "vietnamworks"]:
        l_recs = load_raw_listings(src_key, target_date=args.date)
        d_recs = load_raw_details(src_key, target_date=args.date)
        all_listings.extend(l_recs)
        all_details.extend(d_recs)
        print(f"  + Nguon {src_key:<14}: {len(l_recs):,} listings, {len(d_recs):,} details.")

    print(f"\nTong cong quet duoc: {len(all_listings):,} listings va {len(all_details):,} details.")

    valid_records, quarantine_records, invalid_records, val_summary = validator.route_records(all_details)
    print(f"Ket qua phan luong:")
    print(f"  - Hop le (Valid)     : {len(valid_records):,} ({val_summary.get('valid_rate_pct', 0)}%)")
    print(f"  - Cach ly (Quarantine): {len(quarantine_records):,}")
    print(f"  - Loi (Invalid)      : {len(invalid_records):,}")

    _, new_list_added, total_list_master = validator.save_master_listings(all_listings)
    _, new_det_added, total_det_master = validator.save_master_details_valid(valid_records)

    print(f"\nLuu nhat ky Master Bronze:")
    print(f"  - bronze_listings_master.json : +{new_list_added:,} tin moi (Tong: {total_list_master:,})")
    print(f"  - bronze_details_valid.json   : +{new_det_added:,} tin moi (Tong: {total_det_master:,})")

    # -------------------------------------------------------------------------
    # GIAI DOAN 3: CHUAN HOA & NAP VAO POSTGRESQL (SILVER & GOLD PIPELINE)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print(">>> [GIAI DOAN 3/3] CHUAN HOA & NAP VAO POSTGRESQL (SILVER & GOLD) <<<")
    print("#" * 80)

    bronze_data = load_bronze_data(force_reload=True)
    print(f"Nap Bronze Data thanh cong: {len(bronze_data['df_merged']):,} tin viec lam hop le san sang xu ly.")

    with get_db_connection() as conn:
        run_companies_pipeline(bronze_data, conn)
        run_skills_pipeline(conn)
        run_jobs_pipeline(bronze_data, conn)
        run_job_descriptions_pipeline(bronze_data, conn)
        run_job_skills_pipeline(bronze_data, conn)
        run_job_source_records_pipeline(bronze_data, conn)
        run_job_snapshots_pipeline(bronze_data, conn)
        run_dq_results_pipeline(bronze_data, conn)

    # -------------------------------------------------------------------------
    # TONG KET TOAN BO PIPELINE
    # -------------------------------------------------------------------------
    final_stats = get_current_db_job_stats()
    total_elapsed = round(time.time() - pipeline_start_time, 1)

    print("\n" + "=" * 80)
    print("   TONG KET TOAN BO PHIEN CHAY END-TO-END PIPELINE")
    print("=" * 80)
    print(f" - Thoi gian thuc thi tong cong   : {total_elapsed} giay ({round(total_elapsed / 60, 1)} phut)")
    print(f" - Tin cao duoc trong phien nay    : {total_crawled_session} tin")
    print(f" - Tin hop le tich luy Bronze      : {len(valid_records):,} tin")
    print(f" - So viec lam Database truoc do   : {initial_stats['total_jobs']:,} tin ({initial_stats['active_jobs']:,} active)")
    print(f" - So viec lam Database hien tai   : {final_stats['total_jobs']:,} tin ({final_stats['active_jobs']:,} active)")
    print(f" - Doanh nghiep dang tuyen dung    : {final_stats['total_companies']:,} cong ty")
    print(f" - So viec lam moi tang them       : +{max(0, final_stats['total_jobs'] - initial_stats['total_jobs']):,} tin")
    print("=" * 80)
    print("Pipeline da hoan tat xu ly thanh cong 100%. He thong Web da cap nhat du lieu moi nhat.")


if __name__ == "__main__":
    main()
