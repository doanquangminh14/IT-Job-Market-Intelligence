import argparse
import sys
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.profiling import DataProfiler, ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="IT Job Market Intelligence - Bộ Kiểm Kê & Profiling Chất Lượng Dữ Liệu Thô (Raw Data)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Ngày cần kiểm kê định dạng YYYY-MM-DD (mặc định: toàn bộ kho dữ liệu nếu không chỉ định)"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Tự động kiểm kê ngày cào mới nhất tìm thấy trong thư mục data/raw/"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        choices=["topcv", "topdev", "vietnamworks"],
        help="Lọc kiểm kê riêng 1 nguồn: topcv | topdev | vietnamworks (mặc định: toàn bộ 3 nguồn)"
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Đường dẫn thư mục data/raw tùy chọn"
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="Đường dẫn thư mục lưu báo cáo (mặc định: reports/profiling)"
    )

    args = parser.parse_args()

    profiler = DataProfiler(raw_dir=args.raw_dir)
    available_dates = profiler.get_available_dates()

    target_date = args.date
    if args.latest:
        if not available_dates:
            print("[X] Không tìm thấy bất kỳ ngày nào có dữ liệu cào trong thư mục raw.")
            sys.exit(1)
        target_date = available_dates[-1]
        print(f"[*] Chế độ --latest: Chọn ngày mới nhất có dữ liệu: {target_date}")

    if target_date and target_date not in available_dates:
        print(f"[!] Cảnh báo: Ngày {target_date} không nằm trong danh sách các ngày có dữ liệu ({', '.join(available_dates)}). Vẫn tiếp tục quét...")

    print(f"[*] Đang đọc và kiểm kê dữ liệu... (Phạm vi: {target_date or 'TOÀN BỘ LỊCH SỬ'})...")
    profile_result = profiler.run_profiling(target_date=target_date, source_filter=args.source)

    # 1. Hiển thị Console
    reporter = ReportGenerator(output_dir=args.report_dir)
    reporter.print_console_summary(profile_result)

    # 2. Xuất file Markdown & CSV
    md_file, csv_file = reporter.save_reports(profile_result)
    print(f"✅ Báo cáo chi tiết đã lưu tại : {md_file}")
    print(f"📈 Chỉ số lịch sử đã cập nhật tại: {csv_file}")


if __name__ == "__main__":
    main()
