import argparse
import sys
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.crawlers.topdev import TopDevCrawler
from src.crawlers.vietnamworks import VietnamWorksCrawler
from src.crawlers.topcv import TopCVCrawler


def main():
    parser = argparse.ArgumentParser(
        description="IT Job Market Intelligence - Bộ điều phối cào dữ liệu đa nền tảng"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        choices=["topdev", "vietnamworks", "topcv", "all"],
        help="Nguồn tuyển dụng cần cào: topdev | vietnamworks | topcv | all (mặc định: all)"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=100,
        help="Số lượng jobs chi tiết thành công cần cào cho mỗi nguồn (mặc định: 100)"
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Chế độ cào bù: Quét và thử cào lại tất cả các jobs bị lỗi (failed) trong file listing"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Ngày cần cào bù định dạng YYYY-MM-DD (mặc định: ngày hôm nay)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục lưu trữ dữ liệu raw tùy chọn (mặc định: data/raw/<source>)"
    )
    args = parser.parse_args()

    crawler_map = {
        "topdev": ("TopDev", TopDevCrawler),
        "vietnamworks": ("VietnamWorks", VietnamWorksCrawler),
        "topcv": ("TopCV", TopCVCrawler),
    }

    selected_sources = list(crawler_map.keys()) if args.source == "all" else [args.source]

    # XỬ LÝ CHẾ ĐỘ CÀO BÙ (RETRY FAILED)
    if args.retry_failed:
        print("=" * 70)
        print(" IT JOB MARKET INTELLIGENCE - CHẾ ĐỘ CÀO BÙ (RETRY FAILED) ")
        print(f" Thời gian bắt đầu : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" Nguồn chỉ định    : {', '.join([crawler_map[s][0] for s in selected_sources])}")
        print("=" * 70 + "\n")

        overall_results = {}
        for src_key in selected_sources:
            src_name, crawler_cls = crawler_map[src_key]
            print(f"\n>>> [CÀO BÙ NGUỒN: {src_name.upper()}] <<<")
            try:
                crawler = crawler_cls(output_dir=args.output_dir)
                result = crawler.retry_failed_jobs(target_date=args.date)
                overall_results[src_name] = result
            except Exception as e:
                print(f"[X] Gặp lỗi khi cào bù crawler {src_name}: {e}")
                overall_results[src_name] = {"error": str(e)}

        print("\n" + "=" * 70)
        print(" TỔNG KẾT TOÀN BỘ PHIÊN CÀO BÙ ")
        print("=" * 70)
        for src_name, res in overall_results.items():
            if "error" in res:
                print(f"- {src_name:<15}: [THẤT BẠI] Lỗi: {res['error']}")
            else:
                tf = res.get("total_failed", 0)
                rc = res.get("recovered", 0)
                sf = res.get("still_failed", 0)
                print(f"- {src_name:<15}: Tổng lỗi tìm thấy: {tf} | Cứu thành công: {rc} | Vẫn lỗi: {sf}")
        print("=" * 70)
        return

    print("=" * 70)
    print(" IT JOB MARKET INTELLIGENCE - CRAWLER RUNNER ")
    print(f" Thời gian bắt đầu : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Nguồn chỉ định    : {', '.join([crawler_map[s][0] for s in selected_sources])}")
    print(f" Mục tiêu mỗi nguồn: {args.target} jobs thành công")
    if args.output_dir:
        print(f" Thư mục output tùy chọn : {args.output_dir}")
    print("=" * 70 + "\n")

    overall_results = {}

    for src_key in selected_sources:
        src_name, crawler_cls = crawler_map[src_key]
        print(f"\n>>> [BẮT ĐẦU NGUỒN: {src_name.upper()}] (Target: {args.target} jobs) <<<")
        try:
            crawler = crawler_cls(output_dir=args.output_dir)
            result = crawler.run(target_success_count=args.target)
            overall_results[src_name] = result
        except Exception as e:
            print(f"[X] Gặp lỗi nghiêm trọng khi chạy crawler {src_name}: {e}")
            overall_results[src_name] = {"error": str(e), "session_success_count": 0}

    print("\n" + "=" * 70)
    print(" TỔNG KẾT TOÀN BỘ PHIÊN CHẠY CRAWLER ")
    print("=" * 70)
    for src_name, res in overall_results.items():
        if "error" in res:
            print(f"- {src_name:<15}: [THẤT BẠI] Lỗi: {res['error']}")
        else:
            success = res.get("session_success_count", 0)
            failed = res.get("failed_count", 0)
            p_succ = res.get("pending_success_count", 0)
            n_succ = res.get("new_success_count", 0)
            r_pend = res.get("remaining_pending_count", 0)
            saved_file = res.get("saved_detail_file", "")
            breakdown_str = f" [Hàng đợi cũ: {p_succ} | Web mới: {n_succ} | Còn chờ: {r_pend}]"
            print(f"- {src_name:<15}: {success}/{args.target} thành công (Lỗi: {failed}){breakdown_str} | File: {saved_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
