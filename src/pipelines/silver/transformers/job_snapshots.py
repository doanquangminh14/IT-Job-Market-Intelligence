import hashlib
from datetime import datetime
import pandas as pd
from .jobs import clean_job_title, normalize_location_city, parse_salary

def transform_job_snapshots(bronze_data):
    """
    Tạo các bản ghi chụp trạng thái định kỳ (Periodic Snapshot Fact Table) cho bảng job_snapshots.
    Mỗi bản ghi lưu trữ thuộc tính quan sát tại thời điểm crawler quét qua:
      - snapshot_id: Mã định danh duy nhất của snapshot
      - job_id: Khóa ngoại liên kết tới bảng jobs
      - observed_at: Thời điểm quan sát (crawled_at)
      - batch_id: Mã đợt thu thập dữ liệu (batch_YYYYMMDD)
      - title_normalized: Chức danh việc làm đã làm sạch
      - city: Địa điểm làm việc chuẩn hóa cấp tỉnh/thành
      - salary_min, salary_max, salary_min_vnd, salary_max_vnd, salary_type: Khung lương chuẩn hóa
      - is_active: Trạng thái còn hạn tại thời điểm quan sát
      - content_hash: Mã băm SHA-256 toàn bộ nội dung để nhận diện biến động nội dung tin
    """
    df_merged = bronze_data["df_merged"]
    print(f"-> [Transformer: job_snapshots] Xây dựng snapshot chuỗi thời gian từ {len(df_merged):,} tin việc làm...")

    today_str = datetime.now().strftime('%Y-%m-%d')
    snapshots = []

    for idx, row in df_merged.iterrows():
        snapshot_id = idx + 1
        job_id = int(row["job_id"])
        crawled_at = str(row.get("crawled_at", "") or "").strip()
        obs_date = crawled_at[:10] if crawled_at else today_str
        batch_id = f"batch_{obs_date.replace('-', '')}"

        title_raw = str(row.get("title_raw", "") or "").strip()
        title_norm = clean_job_title(title_raw)
        city = normalize_location_city(row.get("location_raw", ""), row.get("work_mode_raw", ""))

        sal_res = parse_salary(row.get("salary_raw", ""))

        deadline_str = str(row.get("deadline_raw", "") or "").strip()
        is_act = True
        if deadline_str:
            is_act = (deadline_str[:10] >= today_str)

        # Tính toán SHA-256 content_hash để phát hiện sửa đổi JD
        hash_payload = f"{title_raw}|{row.get('salary_raw', '')}|{row.get('location_raw', '')}|{row.get('requirements_raw', '')}"
        c_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        snapshots.append({
            "snapshot_id": snapshot_id,
            "job_id": job_id,
            "observed_at": crawled_at or datetime.now().isoformat(),
            "batch_id": batch_id,
            "title_normalized": title_norm,
            "city": city,
            "salary_min": sal_res["salary_min"],
            "salary_max": sal_res["salary_max"],
            "salary_min_vnd": sal_res["salary_min_vnd"],
            "salary_max_vnd": sal_res["salary_max_vnd"],
            "salary_type": sal_res["salary_type"],
            "is_active": is_act,
            "content_hash": c_hash
        })

    active_cnt = sum(1 for s in snapshots if s["is_active"])
    batch_counts = {}
    for s in snapshots:
        b = s["batch_id"]
        batch_counts[b] = batch_counts.get(b, 0) + 1

    batch_summary = ", ".join(f"{k}: {v:,}" for k, v in sorted(batch_counts.items()))
    print(f"   [Transformer: job_snapshots] Đã tạo thành công: {len(snapshots):,} bản ghi snapshot.")
    print(f"   [Transformer: job_snapshots] Phân bố đợt quan sát: {batch_summary}.")
    print(f"   [Transformer: job_snapshots] Trạng thái: {active_cnt:,} hoạt động ({active_cnt/len(snapshots)*100:.1f}%), {len(snapshots)-active_cnt:,} hết hạn.")

    return snapshots
