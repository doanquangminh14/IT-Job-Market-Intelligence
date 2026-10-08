import json
import os
import re
import sys
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests
import pandas as pd
from tqdm import tqdm

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join("data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n", strip=True)

# ==============================================================
# 1. CRAWL TOPDEV (50 JOBS)
# ==============================================================
def crawl_topdev(target_count: int = 50):
    topdev_details_file = os.path.join(DATA_DIR, "topdev_job_details_raw.json")
    if os.path.exists(topdev_details_file):
        with open(topdev_details_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if len(existing) >= target_count:
            print(f"[*] TopDev đã có {len(existing)} jobs trong {topdev_details_file}. Bỏ qua cào lại.")
            return

    print("="*60)
    print(f"[*] BẮT ĐẦU CRAWL TOPDEV ({target_count} JOBS MẪU)")
    print("="*60)
    
    session = requests.Session(impersonate="chrome124")
    base_url = "https://topdev.vn/viec-lam/tim-kiem?job_categories_ids=2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2C11%2C12%2C13%2C67&page={page}"
    
    # 1.1 Crawl List
    collected_slugs = []
    seen_ids = set()
    page = 1
    
    print("[1/2] Thu thập danh sách URL TopDev...")
    while len(collected_slugs) < target_count and page <= 10:
        url = base_url.format(page=page)
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            print(f"[!] Lỗi page {page}: HTTP {resp.status_code}")
            break
            
        pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', resp.text, re.DOTALL)
        decoded = "".join(pushes).encode('utf-8').decode('unicode_escape', errors='ignore')
        matches = re.findall(r'/viec-lam/([a-zA-Z0-9\-_]+-(\d{5,8}))', decoded)
        
        for slug, jid in matches:
            if jid not in seen_ids:
                seen_ids.add(jid)
                collected_slugs.append({
                    "source": "topdev",
                    "source_job_id": jid,
                    "job_url": f"https://topdev.vn/viec-lam/{slug}",
                    "crawled_at": datetime.now().isoformat()
                })
                if len(collected_slugs) >= target_count:
                    break
        print(f"  -> Page {page}: Lũy kế {len(collected_slugs)} jobs")
        page += 1
        time.sleep(random.uniform(1.2, 2.0))
        
    print(f"[+] Đã lấy đủ {len(collected_slugs)} link jobs từ TopDev.")
    
    # 1.2 Crawl Details
    print("\n[2/2] Cào chi tiết từng việc làm TopDev...")
    list_records = []
    detail_records = []
    
    for item in tqdm(collected_slugs, desc="TopDev Details"):
        job_url = item["job_url"]
        job_id = item["source_job_id"]
        
        max_retries = 3
        ld_data = None
        soup = None
        
        for attempt in range(max_retries):
            try:
                resp = session.get(job_url, timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for s in soup.find_all("script", type="application/ld+json"):
                        try:
                            d = json.loads(s.string)
                            if d.get("@type") == "JobPosting":
                                ld_data = d
                                break
                        except Exception:
                            pass
                    break
                elif resp.status_code == 429:
                    time.sleep(10 * (attempt + 1))
                else:
                    time.sleep(2 * (attempt + 1))
            except Exception as e:
                time.sleep(2 * (attempt + 1))
                
        if not ld_data:
            ld_data = {}
            
        # Parse fields
        title = ld_data.get("title") or ""
        if not title and soup and soup.title:
            title = soup.title.string.split("|")[0].replace("Tuyển dụng", "").strip()
            
        hiring_org = ld_data.get("hiringOrganization") or {}
        comp_name = hiring_org.get("name", "")
        comp_url = hiring_org.get("sameAs", "")
        comp_logo = hiring_org.get("logo", "")
        
        # Salary
        salary_info = ld_data.get("baseSalary") or {}
        val_info = salary_info.get("value") or {}
        if isinstance(val_info, dict):
            sal_val = val_info.get("value")
            if sal_val == "Negotiable":
                salary_raw = "Thương lượng"
            elif "minValue" in val_info or "maxValue" in val_info:
                min_v = val_info.get("minValue", "")
                max_v = val_info.get("maxValue", "")
                salary_raw = f"{min_v} - {max_v} {salary_info.get('currency', 'VND')}"
            else:
                salary_raw = str(sal_val or "Thương lượng")
        else:
            salary_raw = str(val_info or "Thương lượng")
            
        # Location
        job_loc = ld_data.get("jobLocation") or {}
        addr = job_loc.get("address") or {}
        loc_parts = []
        if addr.get("streetAddress"): loc_parts.append(addr.get("streetAddress"))
        if addr.get("addressLocality"): loc_parts.append(addr.get("addressLocality"))
        if addr.get("addressRegion"): loc_parts.append(addr.get("addressRegion"))
        location_raw = ", ".join(loc_parts) if loc_parts else (addr.get("addressRegion") or "")
        
        # Skills & dates
        skills_raw = str(ld_data.get("skills") or "")
        posted_at = str(ld_data.get("datePosted") or "")
        deadline = str(ld_data.get("validThrough") or "")
        
        # Desc & requirements
        desc_html = ld_data.get("description", "")
        desc_text = clean_html(desc_html)
        
        b = ld_data.get("jobBenefits")
        benefits_raw = clean_html(b) if isinstance(b, str) else ("\n".join(b) if isinstance(b, list) else "")
        exp_req = ld_data.get("experienceRequirements", "")
        exp_raw = clean_html(exp_req) if isinstance(exp_req, str) else ""
        emp_type = str(ld_data.get("employmentType") or "")
        industry = str(ld_data.get("industry") or "Information Technology")
        crawled_at = datetime.now().isoformat()
        
        # List schema
        list_records.append({
            "source": "topdev",
            "source_job_id": job_id,
            "job_url": job_url,
            "company_logo_url": comp_logo,
            "tile_raw": title,
            "company_name_raw": comp_name,
            "location_raw": location_raw,
            "salary_raw": salary_raw,
            "experience_raw": exp_raw,
            "posted_at_raw": posted_at,
            "crawled_at": crawled_at
        })
        
        # Detail schema
        detail_records.append({
            "detail_id": f"topdev_{job_id}",
            "source": "topdev",
            "source_job_id": job_id,
            "job_url": job_url,
            "title_raw": title,
            "company_name_raw": comp_name,
            "company_url": comp_url,
            "company_size_raw": "",
            "company_location_raw": location_raw,
            "industry_raw": industry,
            "salary_raw": salary_raw,
            "experience_raw": exp_raw,
            "education_raw": "",
            "location_raw": location_raw,
            "work_mode_raw": "",
            "employment_type_raw": emp_type,
            "working_time_raw": "",
            "overview_raw": "",
            "responsibilities_raw": desc_text,
            "requirements_raw": exp_raw,
            "benefits_raw": benefits_raw,
            "required_skills_raw": skills_raw,
            "preferred_skills_raw": "",
            "published_at_raw": posted_at,
            "updated_at_raw": "",
            "deadline_raw": deadline,
            "crawled_at": crawled_at
        })
        
        time.sleep(random.uniform(1.2, 2.0))
        
    df_topdev_list = pd.DataFrame(list_records)
    df_topdev_detail = pd.DataFrame(detail_records)
    
    # Save files
    df_topdev_list.to_csv(os.path.join(DATA_DIR, "topdev_jobs_raw.csv"), index=False, encoding="utf-8-sig")
    df_topdev_list.to_json(os.path.join(DATA_DIR, "topdev_jobs_raw.json"), orient="records", force_ascii=False, indent=2)
    
    df_topdev_detail.to_csv(os.path.join(DATA_DIR, "topdev_job_details_raw.csv"), index=False, encoding="utf-8-sig")
    df_topdev_detail.to_json(os.path.join(DATA_DIR, "topdev_job_details_raw.json"), orient="records", force_ascii=False, indent=2)
    
    print(f"[+] TopDev hoàn thành! Đã lưu {len(df_topdev_detail)} jobs vào:")
    print("    - data/raw/topdev_jobs_raw.csv & .json")
    print("    - data/raw/topdev_job_details_raw.csv & .json")


# ==============================================================
# 2. CRAWL VIETNAMWORKS (50 JOBS)
# ==============================================================
def crawl_vietnamworks(target_count: int = 50):
    print("\n" + "="*60)
    print(f"[*] BẮT ĐẦU CRAWL VIETNAMWORKS ({target_count} JOBS MẪU)")
    print("="*60)
    
    session = requests.Session(impersonate="chrome124")
    headers = {
        'Referer': 'https://www.vietnamworks.com/',
        'Origin': 'https://www.vietnamworks.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }
    payload = {
        "query": "it",
        "jobFunctionId": [{"parentId": 5, "childrenIds": [-1]}],
        "page": 0,
        "hitsPerPage": target_count
    }
    
    print(f"[*] Gửi request tìm kiếm IT (g=5) lấy {target_count} jobs...")
    resp = session.post("https://ms.vietnamworks.com/job-search/v1.0/search", json=payload, headers=headers, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"VNW Search thất bại: {resp.status_code} - {resp.text[:200]}")
        
    data = resp.json().get("data", [])
    print(f"[+] Nhận được {len(data)} kết quả từ VietnamWorks API.")
    
    list_records = []
    detail_records = []
    
    for item in data[:target_count]:
        job_id = str(item.get("jobId", ""))
        detail_id = f"vietnamworks_{job_id}"
        job_url = item.get("jobUrl", "")
        title = item.get("jobTitle", "")
        company_name = item.get("companyName", "")
        company_logo = item.get("companyLogo", "")
        company_url = item.get("companyUrl", "")
        
        # Salary
        pretty_sal = item.get("prettySalary") or item.get("salary") or "Thoả thuận"
        
        # Location
        locations = item.get("locations") or []
        loc_str = ", ".join([l.get("cityName", "") for l in locations if isinstance(l, dict) and l.get("cityName")]) if isinstance(locations, list) else str(locations)
        if not loc_str and item.get("address"):
            loc_str = item.get("address")
            
        # Experience
        exp_years = item.get("yearsOfExperience")
        exp_str = f"{exp_years} năm" if exp_years else "Không yêu cầu / Không xác định"
        
        # Dates
        posted_at = item.get("approvedOn", "") or item.get("createdOn", "")
        updated_at = item.get("lastUpdatedOn", "")
        deadline = item.get("expiredOn", "")
        crawled_at = datetime.now().isoformat()
        
        # List schema
        list_records.append({
            "source": "vietnamworks",
            "source_job_id": job_id,
            "job_url": job_url,
            "company_logo_url": company_logo,
            "tile_raw": title,
            "company_name_raw": company_name,
            "location_raw": loc_str,
            "salary_raw": str(pretty_sal),
            "experience_raw": exp_str,
            "posted_at_raw": str(posted_at),
            "crawled_at": crawled_at
        })
        
        # Skills
        skills_list = item.get("skills") or []
        skills_raw = ", ".join([s.get("skillName", "") for s in skills_list if isinstance(s, dict) and s.get("skillName")])
        
        # Benefits
        benefits_list = []
        for b in (item.get("benefits") or []):
            if isinstance(b, dict):
                b_name = b.get("benefitNameVI") or b.get("benefitName") or ""
                b_val = b.get("benefitValue") or ""
                benefits_list.append(f"{b_name}: {b_val}" if b_val else b_name)
        benefits_raw = "\n".join([b for b in benefits_list if b])
        
        # Mode & type
        work_type = item.get("typeWorking", {}).get("name") if isinstance(item.get("typeWorking"), dict) else ""
        emp_type = item.get("jobLevelVI") or item.get("jobLevel", "")
        comp_size = item.get("companySizeVI") or item.get("companySize", "")
        
        ind_list = item.get("industries") or []
        industries = ", ".join([ind.get("industryNameVI", "") or ind.get("industryName", "") for ind in ind_list if isinstance(ind, dict)])
        
        desc_text = clean_html(item.get("jobDescription", ""))
        req_text = clean_html(item.get("jobRequirement", ""))
        
        detail_records.append({
            "detail_id": detail_id,
            "source": "vietnamworks",
            "source_job_id": job_id,
            "job_url": job_url,
            "title_raw": title,
            "company_name_raw": company_name,
            "company_url": company_url,
            "company_size_raw": comp_size,
            "company_location_raw": loc_str,
            "industry_raw": industries,
            "salary_raw": str(pretty_sal),
            "experience_raw": exp_str,
            "education_raw": "",
            "location_raw": loc_str,
            "work_mode_raw": work_type,
            "employment_type_raw": emp_type,
            "working_time_raw": "",
            "overview_raw": item.get("summary", "") or "",
            "responsibilities_raw": desc_text,
            "requirements_raw": req_text,
            "benefits_raw": benefits_raw,
            "required_skills_raw": skills_raw,
            "preferred_skills_raw": "",
            "published_at_raw": str(posted_at),
            "updated_at_raw": str(updated_at),
            "deadline_raw": str(deadline),
            "crawled_at": crawled_at
        })
        
    df_vnw_list = pd.DataFrame(list_records)
    df_vnw_detail = pd.DataFrame(detail_records)
    
    # Save files
    df_vnw_list.to_csv(os.path.join(DATA_DIR, "vietnamworks_jobs_raw.csv"), index=False, encoding="utf-8-sig")
    df_vnw_list.to_json(os.path.join(DATA_DIR, "vietnamworks_jobs_raw.json"), orient="records", force_ascii=False, indent=2)
    
    df_vnw_detail.to_csv(os.path.join(DATA_DIR, "vietnamworks_job_details_raw.csv"), index=False, encoding="utf-8-sig")
    df_vnw_detail.to_json(os.path.join(DATA_DIR, "vietnamworks_job_details_raw.json"), orient="records", force_ascii=False, indent=2)
    
    print(f"[+] VietnamWorks hoàn thành! Đã lưu {len(df_vnw_detail)} jobs vào:")
    print("    - data/raw/vietnamworks_jobs_raw.csv & .json")
    print("    - data/raw/vietnamworks_job_details_raw.csv & .json")

if __name__ == "__main__":
    crawl_topdev(50)
    crawl_vietnamworks(50)
    print("\n[V] ĐÃ HOÀN TẤT THU THẬP MẪU 50 JOBS CHO CẢ TOPDEV VÀ VIETNAMWORKS!")
