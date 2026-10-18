import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.quality.validator import QualityValidator

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


def load_raw_listings(source: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Đọc tất cả các file listing JSON trong data/raw/{source}/listings/[target_date]/
    Gắn thêm metadata: raw_file_name và raw_date.
    """
    records: List[Dict[str, Any]] = []
    listings_root = os.path.join(PROJECT_ROOT, "data", "raw", source, "listings")
    if not os.path.exists(listings_root):
        return records

    date_folders = [target_date] if target_date else sorted(os.listdir(listings_root))

    for date_folder in date_folders:
        folder_path = os.path.join(listings_root, date_folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path)):
            if fname.endswith(".json"):
                fpath = os.path.join(folder_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                item["raw_file_name"] = fname
                                item["raw_date"] = date_folder
                                records.append(item)
                except Exception as e:
                    print(f"[CANH BAO] Không thể đọc listing file {fpath}: {e}")
    return records


def load_raw_details(source: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Đọc tất cả các file detail JSON trong data/raw/{source}/details/[target_date]/
    Gắn thêm metadata: raw_file_name và raw_date.
    """
    records: List[Dict[str, Any]] = []
    details_root = os.path.join(PROJECT_ROOT, "data", "raw", source, "details")
    if not os.path.exists(details_root):
        return records

    date_folders = [target_date] if target_date else sorted(os.listdir(details_root))

    for date_folder in date_folders:
        folder_path = os.path.join(details_root, date_folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path)):
            if fname.endswith(".json"):
                fpath = os.path.join(folder_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                item["raw_file_name"] = fname
                                item["raw_date"] = date_folder
                                records.append(item)
                except Exception as e:
                    print(f"[CANH BAO] Không thể đọc detail file {fpath}: {e}")
    return records


def get_latest_date() -> Optional[str]:
    """Tìm ngày mới nhất có dữ liệu trong data/raw/"""
    found_dates = set()
    for s in ["topcv", "topdev", "vietnamworks"]:
        for sub in ["details", "listings"]:
            d_path = os.path.join(PROJECT_ROOT, "data", "raw", s, sub)
            if os.path.exists(d_path):
                for d in os.listdir(d_path):
                    if os.path.isdir(os.path.join(d_path, d)):
                        found_dates.add(d)
    return max(found_dates) if found_dates else None


def main():
    parser = argparse.ArgumentParser(
        description="IT Job Market Intelligence - Kiểm Định & Hợp Nhất Master Tích Lũy Vào Tầng Bronze"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Ngày cần kiểm định (YYYY-MM-DD). Mặc định quét toàn bộ nếu không chỉ định.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Tự động kiểm định ngày cào mới nhất.",
    )
    parser.add_argument(
        "--save-bronze",
        action="store_true",
        help="Lưu nạp tích lũy vào 2 file Master Bronze: bronze_listings_master.json & bronze_details_valid.json",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["topcv", "topdev", "vietnamworks", "all"],
        default="all",
        help="Sàn tuyển dụng cần kiểm định (mặc định: all)",
    )

    args = parser.parse_args()

    target_date = args.date
    if args.latest:
        target_date = get_latest_date()
        print(f"-> Tự động chọn ngày mới nhất: {target_date}")

    sources = ["topcv", "topdev", "vietnamworks"] if args.source == "all" else [args.source]
    validator = QualityValidator()

    mode_desc = "LƯU TÍCH LŨY VÀO 2 FILE MASTER BRONZE" if args.save_bronze else "Dry-Run (chỉ kiểm tra & in thống kê, dùng --save-bronze để lưu)"

    print("\n" + "=" * 80)
    print("BẮT ĐẦU KIỂM ĐỊNH & HỢP NHẤT DỮ LIỆU TẦNG BRONZE (MASTER ACCUMULATION)")
    print(f"Phạm vi ngày: {target_date or 'Toàn bộ lịch sử'}")
    print(f"Chế độ      : {mode_desc}")
    print("=" * 80)

    all_listings: List[Dict[str, Any]] = []
    all_valid_details: List[Dict[str, Any]] = []
    all_quarantine_details: List[Dict[str, Any]] = []
    all_invalid_details: List[Dict[str, Any]] = []

    grand_listings_scanned = 0
    grand_details_scanned = 0

    for s in sources:
        # 1. Đọc Listings
        raw_listings = load_raw_listings(s, target_date=target_date)
        all_listings.extend(raw_listings)
        grand_listings_scanned += len(raw_listings)

        # 2. Đọc Details & Kiểm định chất lượng
        raw_details = load_raw_details(s, target_date=target_date)
        if not raw_details:
            print(f"\n[{s.upper()}] Không có bản ghi detail nào trong phạm vi quét.")
            continue

        v_list, q_list, i_list, summary = validator.route_records(raw_details)
        all_valid_details.extend(v_list)
        all_quarantine_details.extend(q_list)
        all_invalid_details.extend(i_list)
        grand_details_scanned += summary["total_scanned"]

        print(f"\n--- KẾT QUẢ QUÉT: {s.upper()} ---")
        print(f"  • Listings cào được    : {len(raw_listings):,} tin")
        print(f"  • Details quét qua     : {summary['total_scanned']:,} tin")
        print(f"  • HỢP LỆ (Valid)     : {summary['valid_count']:,} ({summary['valid_rate_pct']}%)")
        print(f"  • CÁCH LY (Quarantine): {summary['quarantine_count']:,} ({summary['quarantine_rate_pct']}%)")
        print(f"  • RÁC/LỖI (Invalid)  : {summary['invalid_count']:,} ({summary['invalid_rate_pct']}%)")

        if summary["errors_breakdown"]:
            print("  • Chi tiết mã lỗi:")
            for err_code, cnt in summary["errors_breakdown"].items():
                print(f"      - {err_code}: {cnt:,} trường hợp")

    # 3. Lưu tích lũy vào tầng Bronze nếu có cờ --save-bronze
    if args.save_bronze:
        print("\n" + "-" * 80)
        print("ĐANG GHI DỮ LIỆU TÍCH LŨY VÀO TẦNG BRONZE...")

        # File 1: Listings Master
        l_file, l_new, l_total = validator.save_master_listings(all_listings)
        print(f"  [Listings Master]: {l_file}")
        print(f"     -> Thêm mới: +{l_new:,} tin | Tổng tích lũy hiện tại: {l_total:,} tin")

        # File 2: Details Valid Master
        d_file, d_new, d_total = validator.save_master_details_valid(all_valid_details)
        print(f"  [Details Valid Master]: {d_file}")
        print(f"     -> Thêm mới: +{d_new:,} tin | Tổng tích lũy hiện tại: {d_total:,} tin")

        # File 3 & 4 (nếu có Quarantine hoặc Invalid)
        if all_quarantine_details:
            q_file, q_new, q_total = validator.save_master_details_quarantine(all_quarantine_details)
            print(f"  [Details Quarantine Master]: {q_file} (+{q_new:,} mới | tổng: {q_total:,})")

        if all_invalid_details:
            i_file, i_new, i_total = validator.save_master_details_invalid(all_invalid_details)
            print(f"  [Details Invalid Master]: {i_file} (+{i_new:,} mới | tổng: {i_total:,})")

    print("\n" + "=" * 80)
    print("TỔNG KẾT PHIÊN XỬ LÝ BRONZE")
    print(f"  • Tổng Listings quét qua  : {grand_listings_scanned:,} tin")
    print(f"  • Tổng Details quét qua   : {grand_details_scanned:,} tin")
    v_pct = round(len(all_valid_details) / grand_details_scanned * 100, 2) if grand_details_scanned else 0
    print(f"  • HỢP LỆ (Valid)        : {len(all_valid_details):,} tin ({v_pct}%)")
    print(f"  • CÁCH LY (Quarantine)  : {len(all_quarantine_details):,} tin")
    print(f"  • RÁC/LỖI (Invalid)     : {len(all_invalid_details):,} tin")
    if not args.save_bronze:
        print("\n[GOI Y]: Chạy lệnh dưới đây để thực hiện lưu thật vào Bronze:")
        print("   python main_quality.py --save-bronze")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
