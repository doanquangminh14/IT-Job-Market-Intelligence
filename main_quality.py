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


def load_raw_details(source: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
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
        description="IT Job Market Intelligence - Động cơ Phân Luồng Chất Lượng Dữ Liệu (Valid / Quarantine / Invalid)"
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
        "--save-all",
        action="store_true",
        help="Lưu cả 3 luồng vào đúng các thư mục (data/bronze/, data/quarantine/, data/invalid/).",
    )
    parser.add_argument(
        "--save-bronze",
        action="store_true",
        help="Chỉ lưu các bản ghi HỢP LỆ (VALID) vào data/bronze/.",
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

    mode_desc = "Chế độ Dry-Run (chỉ kiểm tra & in thống kê)"
    if args.save_all:
        mode_desc = "Lưu cả 3 luồng (Bronze / Quarantine / Invalid)"
    elif args.save_bronze:
        mode_desc = "Chỉ lưu luồng Hợp Lệ vào Bronze"

    print("\n" + "=" * 78)
    print("🚀 BẮT ĐẦU PHÂN LUỒNG CHẤT LƯỢNG DỮ LIỆU: VALID | QUARANTINE | INVALID")
    print(f"📌 Phạm vi ngày: {target_date or 'Toàn bộ lịch sử'}")
    print(f"📌 Chế độ lưu  : {mode_desc}")
    print("=" * 78)

    grand_scanned = 0
    grand_valid = 0
    grand_quarantine = 0
    grand_invalid = 0

    for s in sources:
        raw_records = load_raw_details(s, target_date=target_date)
        if not raw_records:
            print(f"\n📂 [{s.upper()}] Không có bản ghi thô nào để kiểm định.")
            continue

        valid_list, quarantine_list, invalid_list, summary = validator.route_records(raw_records)

        grand_scanned += summary["total_scanned"]
        grand_valid += summary["valid_count"]
        grand_quarantine += summary["quarantine_count"]
        grand_invalid += summary["invalid_count"]

        print(f"\n--- 📊 KẾT QUẢ PHÂN LUỒNG: {s.upper()} ---")
        print(f"  • Tổng số bản ghi quét : {summary['total_scanned']:,}")
        print(f"  • 🟢 HỢP LỆ (Valid)     : {summary['valid_count']:,} ({summary['valid_rate_pct']}%)")
        print(f"  • 🟡 CÁCH LY (Quarantine): {summary['quarantine_count']:,} ({summary['quarantine_rate_pct']}%)")
        print(f"  • 🔴 RÁC/LỖI (Invalid)  : {summary['invalid_count']:,} ({summary['invalid_rate_pct']}%)")

        if summary["errors_breakdown"]:
            print("  • Chi tiết các mã lỗi phát hiện:")
            for err_code, cnt in summary["errors_breakdown"].items():
                print(f"      - {err_code}: {cnt:,} trường hợp")

        # Lưu dữ liệu nếu được yêu cầu
        should_save_bronze = args.save_all or args.save_bronze
        should_save_others = args.save_all

        def _group_by_date(recs):
            buckets: Dict[str, List[Dict[str, Any]]] = {}
            for r in recs:
                d = r.get("_raw_date", target_date or datetime.now().strftime("%Y-%m-%d"))
                buckets.setdefault(d, []).append(r)
            return buckets

        if should_save_bronze and valid_list:
            for d_str, b_recs in _group_by_date(valid_list).items():
                p = validator.save_valid_to_bronze(b_recs, s, d_str, f"{s}_bronze_valid")
                print(f"  💾 [Bronze] Đã lưu {len(b_recs):,} bản ghi Valid: {p}")

        if should_save_others and quarantine_list:
            for d_str, q_recs in _group_by_date(quarantine_list).items():
                p = validator.save_to_quarantine(q_recs, s, d_str, f"{s}_quarantine")
                print(f"  ⚠️ [Quarantine] Đã lưu {len(q_recs):,} bản ghi Cách ly: {p}")

        if should_save_others and invalid_list:
            for d_str, i_recs in _group_by_date(invalid_list).items():
                p = validator.save_to_invalid(i_recs, s, d_str, f"{s}_invalid")
                print(f"  ❌ [Invalid] Đã lưu {len(i_recs):,} bản ghi Rác/Lỗi: {p}")

    print("\n" + "=" * 78)
    print("🏁 TỔNG KẾT TOÀN BỘ PHIÊN PHÂN LUỒNG")
    print(f"  • Tổng quét qua       : {grand_scanned:,} tin")
    v_pct = round(grand_valid / grand_scanned * 100, 2) if grand_scanned else 0
    q_pct = round(grand_quarantine / grand_scanned * 100, 2) if grand_scanned else 0
    i_pct = round(grand_invalid / grand_scanned * 100, 2) if grand_scanned else 0
    print(f"  • 🟢 HỢP LỆ (Valid)     : {grand_valid:,} tin ({v_pct}%) -> Chuẩn bị vào Bronze")
    print(f"  • 🟡 CÁCH LY (Quarantine): {grand_quarantine:,} tin ({q_pct}%) -> Giữ lại làm sạch ở Silver")
    print(f"  • 🔴 RÁC/LỖI (Invalid)  : {grand_invalid:,} tin ({i_pct}%) -> Loại bỏ khỏi luồng chính")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
