from datetime import datetime
import pandas as pd

def transform_job_source_records(bronze_data):
    """
    Chuẩn hóa và ánh xạ các bản ghi thu thập gốc từ từng sàn tuyển dụng (job_source_records).
    Mỗi bản ghi lưu trữ:
      - source_record_id: Khóa chính đại diện cho bản ghi cào
      - job_id: Khóa ngoại trỏ về Golden Record trong bảng jobs
      - source_id: Mã sàn tuyển dụng (1: TopCV, 2: TopDev, 3: VietnamWorks, 4: ITViec)
      - source_job_id: Mã tin gốc trên sàn
      - source_job_url: Đường dẫn URL trực tiếp tới tin tuyển dụng
      - batch_id: Định danh đợt thu thập dữ liệu
      - crawled_at: Thời điểm crawler thu thập dữ liệu
    """
    df_merged = bronze_data["df_merged"]
    print(f"-> [Transformer: job_source_records] Chuẩn hóa {len(df_merged):,} bản ghi nguồn...")

    source_records = []
    now_iso = datetime.now().isoformat()

    for idx, row in df_merged.iterrows():
        source_record_id = idx + 1
        job_id = int(row["job_id"])
        source_id = int(row["source_id"])
        source_job_id = str(row["source_job_id"]).strip()
        source_job_url = str(row.get("job_url", "") or "").strip()
        crawled_at = str(row.get("crawled_at", "") or "").strip() or now_iso

        # Gán mã batch theo ngày thu thập (hoặc batch mặc định)
        batch_id = f"batch_{crawled_at[:10].replace('-', '')}" if crawled_at else "batch_initial"

        source_records.append({
            "source_record_id": source_record_id,
            "job_id": job_id,
            "source_id": source_id,
            "source_job_id": source_job_id,
            "source_job_url": source_job_url,
            "batch_id": batch_id,
            "crawled_at": crawled_at
        })

    source_name_map = {1: "TopCV", 2: "TopDev", 3: "VietnamWorks", 4: "ITViec"}
    counts_by_source = {}
    for r in source_records:
        name = source_name_map.get(r["source_id"], "Khác")
        counts_by_source[name] = counts_by_source.get(name, 0) + 1

    source_breakdown = ", ".join(f"{k}: {v:,}" for k, v in counts_by_source.items())
    print(f"   [Transformer: job_source_records] Đã chuẩn hóa thành công: {len(source_records):,} bản ghi.")
    print(f"   [Transformer: job_source_records] Phân bố sàn nguồn: {source_breakdown}.")

    return source_records
