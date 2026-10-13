import argparse
import sys
from .db import get_db_connection
from .extractor import load_bronze_data
from .transformers.companies import transform_companies
from .loaders import load_companies

# Danh sách thứ tự phụ thuộc khóa ngoại của các bảng
PIPELINE_TABLES = [
    "companies",
    "skills",
    "jobs",
    "job_descriptions",
    "job_skills",
    "job_source_records",
    "job_snapshots",
    "dq_results"
]

def run_companies_pipeline(bronze_data, conn):
    """Thực thi pipeline trích xuất, làm sạch và nạp cho bảng companies."""
    print("\n=== [BẢNG: companies] Bắt đầu xử lý ===")
    companies_list = transform_companies(bronze_data)
    total_db = load_companies(companies_list, conn)
    print(f"=== [BẢNG: companies] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return companies_list

def main():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Bộ điều phối Silver ETL Pipeline")
    parser.add_argument(
        "--table",
        type=str,
        choices=PIPELINE_TABLES,
        help="Tên bảng cụ thể muốn chạy ETL (ví dụ: companies, skills, jobs...)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Chạy toàn bộ các bảng theo thứ tự phụ thuộc"
    )

    args = parser.parse_args()

    if not args.table and not args.all:
        print("Vui lòng chỉ định --table <tên_bảng> hoặc --all để thực thi.")
        print(f"Các bảng khả dụng: {', '.join(PIPELINE_TABLES)}")
        sys.exit(1)

    print("==================================================================")
    print("      KHỞI CHẠY SILVER ETL PIPELINE (MODULAR ARCHITECTURE)        ")
    print("==================================================================")

    # 1. Nạp dữ liệu nguồn Bronze một lần duy nhất vào bộ nhớ
    bronze_data = load_bronze_data()

    # 2. Mở kết nối database và thực thi
    with get_db_connection() as conn:
        if args.table == "companies" or (args.all and "companies" in PIPELINE_TABLES):
            run_companies_pipeline(bronze_data, conn)

        # Các bảng tiếp theo sẽ được tích hợp tuần tự tại đây:
        # if args.table == "skills" ...
        # if args.table == "jobs" ...

    print("Hoàn tất thực thi pipeline thành công.")

if __name__ == "__main__":
    main()
