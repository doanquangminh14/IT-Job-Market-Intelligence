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


def load_raw_details(source: str, target_date: Optional[str] = None) -> List[Tuple_record := Dict[str, Any]]:
    """
    Đọc tất cả các file detail JSON trong data/raw/{source}/details/[target_date]/
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
                                # Gắn kèm metadata tracking ngày nếu cần
                                item["_raw_date"] = date_folder
                                records.append(item)
                except Exception as e:
                    print(f"⚠️ Không thể đọc file {fpath}: {e}")
    return records


def get_latest_date() -> Optional[str]:
    """Tìm ngày mới nhất có dữ liệu trong data/raw/"""
    found_dates = set()
    for s in ["topcv", "topdev", "vietnamworks"]:
        d_path = os.path.join(PROJECT_ROOT, "data", "raw", s, "details")
        if os.path.exists(d_path):
            for d in os.listdir(d_path):
                if os.path.isdir(os.path.join(d_path, d)):
                    found_dates.add(d)
    return max(found_dates) if found_dates else None


def main():
    parser = argparse.ArgumentParser(
        description="IT Job Market Intelligence - Động cơ Kiểm định & Lọc Luồng Hợp Lệ (Data Quality Gate -> Bronze)"
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
        help="Lưu các bản ghi HỢP LỆ (VALID) vào tầng data/bronze/.",
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
        print(f"📅 Tự động chọn ngày mới nhất: {target_date}")

    sources = ["topcv", "topdev", "vietnamworks"] if args.source == "all" else [args.source]
    validator = QualityValidator()

    print("\n" + "=" * 75)
    print("🚀 BẮT ĐẦU KIỂM ĐỊNH CHẤT LƯỢNG DỮ LIỆU - LUỒNG HỢP LỆ (VALID GATE)")
    print(f"📌 Phạm vi ngày: {target_date or 'Toàn bộ lịch sử'}")
    print(f"📌 Chế độ lưu  : {'Lưu vào tầng data/bronze/' if args.save_bronze else 'Chế độ Dry-Run (chỉ kiểm tra & in thống kê)'}")
    print("=" * 75)

    grand_total_scanned = 0
    grand_total_valid = 0
    grand_total_invalid = 0

    for s in sources:
        raw_records = load_raw_details(s, target_date=target_date)
        if not raw_records:
            print(f"\n📂 [{s.upper()}] Không có bản ghi thô nào để kiểm định.")
            continue

        valid_records, summary = validator.filter_valid_records(raw_records)

        grand_total_scanned += summary["total_scanned"]
        grand_total_valid += summary["valid_count"]
        grand_total_invalid += summary["invalid_count"]

        print(f"\n--- 📊 KẾT QUẢ KIỂM ĐỊNH: {s.upper()} ---")
        print(f"  • Tổng số bản ghi quét : {summary['total_scanned']:,}")
        print(f"  • 🟢 Đạt chuẩn (VALID)   : {summary['valid_count']:,} ({summary['valid_rate_pct']}%)")
        print(f"  • 🔴 Không đạt (INVALID) : {summary['invalid_count']:,}")

        if summary["errors_breakdown"]:
            print("  • Chi tiết các mã lỗi vi phạm:")
            for err_code, cnt in summary["errors_breakdown"].items():
                print(f"      - {err_code}: {cnt:,} lỗi")

        if args.save_bronze and valid_records:
            # Nhóm theo ngày thực tế của record để lưu đúng folder
            date_buckets: Dict[str, List[Dict[str, Any]]] = {}
            for r in valid_records:
                r_date = r.get("_raw_date", target_date or datetime.now().strftime("%Y-%m-%d"))
                date_buckets.setdefault(r_date, []).append(r)

            for d_str, b_records in date_buckets.items():
                out_path = validator.save_valid_to_bronze(
                    valid_records=b_records,
                    source=s,
                    target_date=d_str,
                    file_prefix=f"{s}_bronze_valid",
                )
                print(f"  💾 Đã lưu {len(b_records):,} bản ghi Valid vào Bronze: {out_path}")

    print("\n" + "=" * 75)
    print("🏁 TỔNG KẾT TOÀN BỘ PHIÊN KIỂM ĐỊNH")
    print(f"  • Tổng quét qua   : {grand_total_scanned:,} tin")
    overall_rate = round((grand_total_valid / grand_total_scanned * 100), 2) if grand_total_scanned > 0 else 0
    print(f"  • 🟢 Tổng HỢP LỆ  : {grand_total_valid:,} tin ({overall_rate}%)")
    print(f"  • 🔴 Tổng BỊ LOẠI : {grand_total_invalid:,} tin")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
