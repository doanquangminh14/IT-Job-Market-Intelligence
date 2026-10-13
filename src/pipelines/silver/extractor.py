import os
import json
import pandas as pd

_CACHED_BRONZE = None

def get_bronze_paths():
    """Xác định đường dẫn chuẩn tới các tệp dữ liệu Bronze."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    details_path = os.path.join(project_root, "data", "bronze", "bronze_details_valid.json")
    listings_path = os.path.join(project_root, "data", "bronze", "bronze_listings_master.json")
    return details_path, listings_path

def load_bronze_data(force_reload=False):
    """
    Nạp dữ liệu Bronze một lần và lưu vào bộ nhớ cache.
    Trả về từ điển gồm:
      - df_details: DataFrame chi tiết công việc hợp lệ (2,509 dòng)
      - df_listings: DataFrame danh sách tin tổng hợp
      - df_merged: DataFrame kết hợp inner join theo ['source', 'source_job_id']
    """
    global _CACHED_BRONZE
    if _CACHED_BRONZE is not None and not force_reload:
        return _CACHED_BRONZE

    details_path, listings_path = get_bronze_paths()

    if not os.path.exists(details_path):
        raise FileNotFoundError(f"Không tìm thấy tệp Bronze Details: {details_path}")
    if not os.path.exists(listings_path):
        raise FileNotFoundError(f"Không tìm thấy tệp Bronze Listings: {listings_path}")

    print(f"-> Nạp dữ liệu nguồn Bronze từ đĩa...")
    with open(details_path, "r", encoding="utf-8") as f:
        details_data = json.load(f)
    with open(listings_path, "r", encoding="utf-8") as f:
        listings_data = json.load(f)

    df_details = pd.DataFrame(details_data)
    df_listings = pd.DataFrame(listings_data)

    df_merged = pd.merge(
        df_listings,
        df_details,
        on=["source", "source_job_id"],
        how="inner",
        suffixes=("_list", "_detail")
    )
    df_merged["job_id"] = df_merged.index + 1

    source_map = {"topcv": 1, "topdev": 2, "vietnamworks": 3, "itviec": 4}
    df_merged["source_id"] = df_merged["source"].map(source_map).fillna(1).astype(int)

    _CACHED_BRONZE = {
        "df_details": df_details,
        "df_listings": df_listings,
        "df_merged": df_merged
    }
    print(f"   Đã nạp thành công {len(df_merged):,} bản ghi đồng bộ vào bộ nhớ.")
    return _CACHED_BRONZE
