import argparse
import sys
from .db import get_db_connection
from .extractor import load_bronze_data
from .transformers.companies import transform_companies
from .transformers.skills import transform_skills
from .transformers.jobs import transform_jobs
from .transformers.job_descriptions import transform_job_descriptions
from .transformers.job_skills import transform_job_skills
from .transformers.job_source_records import transform_job_source_records
from .loaders import (
    load_companies, load_skills, load_jobs, load_job_descriptions,
    load_job_skills, load_job_source_records
)

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

def run_skills_pipeline(conn):
    """Thực thi pipeline chuẩn hóa taxonomy và nạp cho bảng skills."""
    print("\n=== [BẢNG: skills] Bắt đầu xử lý ===")
    skills_list = transform_skills()
    total_db = load_skills(skills_list, conn)
    print(f"=== [BẢNG: skills] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return skills_list

def run_jobs_pipeline(bronze_data, conn):
    """Thực thi pipeline trích xuất, làm sạch và nạp cho bảng jobs."""
    print("\n=== [BẢNG: jobs] Bắt đầu xử lý ===")
    jobs_list = transform_jobs(bronze_data, conn)
    total_db = load_jobs(jobs_list, conn)
    print(f"=== [BẢNG: jobs] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return jobs_list

def run_job_descriptions_pipeline(bronze_data, conn):
    """Thực thi pipeline trích xuất, làm sạch và nạp cho bảng job_descriptions."""
    print("\n=== [BẢNG: job_descriptions] Bắt đầu xử lý ===")
    desc_list = transform_job_descriptions(bronze_data)
    total_db = load_job_descriptions(desc_list, conn)
    print(f"=== [BẢNG: job_descriptions] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return desc_list

def run_job_skills_pipeline(bronze_data, conn):
    """Thực thi pipeline trích xuất quan hệ N-N và nạp cho bảng job_skills."""
    print("\n=== [BẢNG: job_skills] Bắt đầu xử lý ===")
    job_skills_list = transform_job_skills(bronze_data)
    total_db = load_job_skills(job_skills_list, conn)
    print(f"=== [BẢNG: job_skills] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return job_skills_list

def run_job_source_records_pipeline(bronze_data, conn):
    """Thực thi pipeline ánh xạ đa nguồn và nạp cho bảng job_source_records."""
    print("\n=== [BẢNG: job_source_records] Bắt đầu xử lý ===")
    source_records_list = transform_job_source_records(bronze_data)
    total_db = load_job_source_records(source_records_list, conn)
    print(f"=== [BẢNG: job_source_records] Hoàn thành: {total_db:,} bản ghi trong database ===\n")
    return source_records_list

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

        if args.table == "skills" or (args.all and "skills" in PIPELINE_TABLES):
            run_skills_pipeline(conn)

        if args.table == "jobs" or (args.all and "jobs" in PIPELINE_TABLES):
            run_jobs_pipeline(bronze_data, conn)

        if args.table == "job_descriptions" or (args.all and "job_descriptions" in PIPELINE_TABLES):
            run_job_descriptions_pipeline(bronze_data, conn)

        if args.table == "job_skills" or (args.all and "job_skills" in PIPELINE_TABLES):
            run_job_skills_pipeline(bronze_data, conn)

        if args.table == "job_source_records" or (args.all and "job_source_records" in PIPELINE_TABLES):
            run_job_source_records_pipeline(bronze_data, conn)

    print("Hoàn tất thực thi pipeline thành công.")

if __name__ == "__main__":
    main()
