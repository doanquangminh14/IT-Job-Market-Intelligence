import re
from urllib.parse import urlparse
import pandas as pd
from ..extractor import load_bronze_data

PORTAL_DOMAINS = {"topcv.vn", "vietnamworks.com", "topdev.vn", "saramin.vn", "itviec.com"}

def clean_company_name(name):
    """
    Làm sạch tên công ty: loại bỏ tiền tố pháp nhân (Công ty TNHH, Cổ phần, Tập đoàn...),
    loại bỏ hậu tố chi nhánh và chuẩn hóa khoảng trắng thừa.
    """
    if not name or pd.isna(name):
        return "Unknown Company"
    name = str(name).strip()
    prefixes = [
        r"^CÔNG TY TNHH MTV\s+", r"^CÔNG TY TNHH\s+", r"^Công ty TNHH MTV\s+", r"^Công ty TNHH\s+",
        r"^CÔNG TY CỔ PHẦN\s+", r"^Công ty Cổ phần\s+", r"^Công Ty Cổ Phần\s+", r"^Công Ty TNHH\s+",
        r"^TẬP ĐOÀN\s+", r"^Tập đoàn\s+", r"^TỔNG CÔNG TY\s+", r"^Tổng Công ty\s+",
        r"^Chi nhánh\s+", r"^CHI NHÁNH\s+",
    ]
    for p in prefixes:
        name = re.sub(p, "", name, flags=re.IGNORECASE)
    suffixes = [
        r"\s+-\s+Chi nhánh.*$", r"\s+-\s+CN.*$", r"\s+JSC$", r"\s+Co\.,\s*Ltd\.?$",
    ]
    for s in suffixes:
        name = re.sub(s, "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip(" -|/,")

def extract_website_domain(url_str):
    """
    Trích xuất hostname tên miền từ URL công ty.
    Nếu là đường dẫn trỏ về trang sàn tuyển dụng thì loại bỏ (trả về None).
    """
    if not url_str or pd.isna(url_str):
        return None
    u = str(url_str).strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in PORTAL_DOMAINS:
            return None
        return domain if "." in domain else None
    except Exception:
        return None

def parse_company_size(size_str):
    """
    Bóc tách quy mô nhân sự thành 2 số nguyên (size_min, size_max).
    Hỗ trợ dạng khoảng (100-499), dạng trên (1000+), dạng dưới (< 20).
    """
    if not size_str or pd.isna(size_str):
        return None, None
    s = str(size_str).strip()
    s_clean = s.replace(".", "")
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)", s_clean)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    plus_match = re.search(r"(\d+)\s*\+", s_clean)
    if plus_match:
        return int(plus_match.group(1)), None
    more_match = re.search(r"(?:hơn|trên)\s*(\d+)", s_clean, re.IGNORECASE)
    if more_match:
        return int(more_match.group(1)), None
    less_match = re.search(r"(?:ít hơn|dưới|<\s*)(\d+)", s_clean, re.IGNORECASE)
    if less_match:
        return 1, int(less_match.group(1))
    return None, None

def normalize_company_city(loc_str, comp_loc_str=""):
    """
    Chuẩn hóa địa bàn trụ sở chính của công ty.
    """
    combined = (str(comp_loc_str) + " " + str(loc_str)).lower()
    if any(k in combined for k in ["hồ chí minh", "tp.hcm", "hcm", "sài gòn", "saigon"]):
        return "Hồ Chí Minh"
    if any(k in combined for k in ["hà nội", "ha noi", "hn"]):
        return "Hà Nội"
    if any(k in combined for k in ["đà nẵng", "da nang"]):
        return "Đà Nẵng"
    if any(k in combined for k in ["hải phòng", "hai phong"]):
        return "Hải Phòng"
    if any(k in combined for k in ["cần thơ", "can tho"]):
        return "Cần Thơ"
    return "Khác / Chưa rõ"

def transform_companies(bronze_data=None):
    """
    Chuyển đổi dữ liệu Bronze thành danh sách các bản ghi chuẩn hóa cho bảng companies.
    Thực hiện khử trùng lặp thực thể (Entity Deduplication) theo lower(company_name_normalized).
    """
    if bronze_data is None:
        bronze_data = load_bronze_data()

    df_det = bronze_data["df_details"]
    df_list = bronze_data["df_listings"]

    company_raw_cols = [
        "source", "source_job_id", "company_name_raw", "company_url",
        "company_size_raw", "company_location_raw", "industry_raw", "location_raw"
    ]
    df_comp_base = df_det[company_raw_cols].copy()
    df_logos = df_list[["source", "source_job_id", "company_logo_url"]].drop_duplicates(subset=["source", "source_job_id"])
    df_comp_merged = pd.merge(df_comp_base, df_logos, on=["source", "source_job_id"], how="left")

    print(f"-> [Transformer: companies] Xử lý làm sạch và khử trùng lặp từ {len(df_comp_merged):,} tin gốc...")
    company_map = {}
    company_id_counter = 1

    for _, row in df_comp_merged.iterrows():
        raw_name = str(row.get("company_name_raw", "") or "").strip()
        norm_name = clean_company_name(raw_name)
        if not norm_name or norm_name == "Unknown Company":
            continue

        comp_url = str(row.get("company_url", "") or "").strip()
        comp_logo = str(row.get("company_logo_url", "") or "").strip()
        comp_size_raw = str(row.get("company_size_raw", "") or "").strip()
        comp_loc_raw = str(row.get("company_location_raw", "") or "").strip()
        loc_raw = str(row.get("location_raw", "") or "").strip()
        ind_raw = str(row.get("industry_raw", "") or "").strip()

        domain = extract_website_domain(comp_url)
        comp_key = norm_name.lower()

        if comp_key not in company_map:
            size_min, size_max = parse_company_size(comp_size_raw)
            city = normalize_company_city(loc_raw, comp_loc_raw)

            company_map[comp_key] = {
                "company_id": company_id_counter,
                "company_name_raw": raw_name,
                "company_name_normalized": norm_name,
                "website_domain": domain,
                "company_url": comp_url if comp_url else None,
                "company_logo_url": comp_logo if comp_logo else None,
                "company_size_raw": comp_size_raw if comp_size_raw else None,
                "company_size_min": size_min,
                "company_size_max": size_max,
                "company_location_raw": comp_loc_raw if comp_loc_raw else (loc_raw if loc_raw else None),
                "company_city": city,
                "industry_raw": ind_raw if ind_raw else None,
                "industry_normalized": ind_raw if ind_raw else "Công nghệ thông tin / IT"
            }
            company_id_counter += 1
        else:
            # Bổ sung thông tin còn thiếu nếu các tin sau có dữ liệu đầy đủ hơn
            existing = company_map[comp_key]
            if not existing["company_logo_url"] and comp_logo:
                existing["company_logo_url"] = comp_logo
            if not existing["company_url"] and comp_url:
                existing["company_url"] = comp_url
                existing["website_domain"] = domain
            if existing["company_size_min"] is None and comp_size_raw:
                s_min, s_max = parse_company_size(comp_size_raw)
                existing["company_size_min"] = s_min
                existing["company_size_max"] = s_max
                existing["company_size_raw"] = comp_size_raw

    companies_list = list(company_map.values())
    print(f"   [Transformer: companies] Đã chuẩn hóa thành công: {len(companies_list):,} công ty độc nhất.")
    return companies_list
