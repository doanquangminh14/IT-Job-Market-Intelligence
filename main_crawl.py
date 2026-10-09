import argparse
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.crawlers.topdev import TopDevCrawler

def main():
    parser = argparse.ArgumentParser(description="IT Job Market Intelligence Crawler Runner")
    parser.add_argument(
        "--source",
        type=str,
        default="topdev",
        choices=["topdev", "vietnamworks", "all"],
        help="Nguồn tuyển dụng cần cào (mặc định: topdev)"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=100,
        help="Số lượng jobs thành công cần cào mỗi lần chạy (mặc định: 100)"
    )
    args = parser.parse_args()

    if args.source in ["topdev", "all"]:
        print(f"[*] Khởi động crawler TopDev với mục tiêu {args.target} jobs...")
        crawler = TopDevCrawler()
        crawler.run(target_success_count=args.target)

    # Sau này bổ sung vietnamworks crawler tại đây

if __name__ == "__main__":
    main()
