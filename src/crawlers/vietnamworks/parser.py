import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Tuple

from src.crawlers.base import clean_html, parse_relative_deadline
from src.schemas.job import JobDetailRaw, JobListingRaw


def parse_job_item(item: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Chuyển đổi 1 raw job object từ VietnamWorks API thành cặp bản ghi:
    - listing_record (JobListingRaw)
    - detail_record (JobDetailRaw)
    Đồng thời validate qua Pydantic schema.
    """
    job_id = str(item.get("jobId", ""))
    alias = item.get("alias", "")
    job_url = item.get("jobUrl", "") or f"https://www.vietnamworks.com/{alias}-{job_id}-jv"
    title = item.get("jobTitle", "") or ""
    comp_name = item.get("companyName", "") or ""
    comp_logo = item.get("companyLogo", "") or ""

    # 1. Company URL & Info
    comp_id = item.get("companyId")
    company_info = item.get("companyInfo") or {}
    comp_url = item.get("companyUrl") or company_info.get("companyProfileUrl") or ""
    if not comp_url and comp_id:
        nfkd = unicodedata.normalize('NFKD', comp_name)
        slug = re.sub(r'[^\w\s-]', '', nfkd).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)
        comp_url = f"https://www.vietnamworks.com/nha-tuyen-dung/{slug}-c{comp_id}"

    # 2. Địa điểm làm việc
    working_locs = item.get("workingLocations") or []
    loc_list = []
    for wl in working_locs:
        if isinstance(wl, dict):
            addr = (wl.get("address") or "").strip()
            city = (wl.get("cityNameVI") or wl.get("cityName") or "").strip()
            if addr and addr not in loc_list:
                loc_list.append(addr)
            elif city and city not in loc_list:
                loc_list.append(city)

    if not loc_list:
        locations = item.get("locations") or []
        if isinstance(locations, list):
            for l in locations:
                if isinstance(l, dict) and (l.get("cityNameVI") or l.get("cityName")):
                    loc_list.append(l.get("cityNameVI") or l.get("cityName"))
                elif isinstance(l, str) and l:
                    loc_list.append(l)
        if not loc_list and item.get("address"):
            loc_list.append(str(item.get("address")))

    loc_str = "; ".join(loc_list)
    comp_loc = (company_info.get("address") or item.get("address") or loc_str or "").strip()

    # 3. Lương & Kinh nghiệm
    salary = str(item.get("prettySalary") or item.get("salary") or "Thương lượng")
    exp_years = item.get("yearsOfExperience")
    exp_str = f"{exp_years} năm" if exp_years is not None and exp_years != "" else "Không yêu cầu"

    posted_at = str(item.get("approvedOn") or item.get("createdOn") or "")
    updated_at = str(item.get("lastUpdatedOn") or "")
    deadline = str(item.get("expiredOn") or "")
    if not deadline:
        search_deadline_text = f"{item.get('expiredIn', '')} {item.get('jobDescription', '')}"
        deadline = parse_relative_deadline(search_deadline_text)
    now_iso = datetime.now().isoformat()

    # 4. Kỹ năng (Skills)
    skills_list = item.get("skills") or []
    skills_raw = ", ".join([
        s.get("skillName", "") for s in skills_list
        if isinstance(s, dict) and s.get("skillName")
    ])

    # 5. Listing Record
    listing_record = {
        "source": "vietnamworks",
        "source_job_id": job_id,
        "job_url": job_url,
        "company_logo_url": comp_logo,
        "title_raw": title,
        "company_name_raw": comp_name,
        "location_raw": loc_str,
        "salary_raw": salary,
        "experience_raw": exp_str,
        "skills_raw": skills_raw,
        "posted_at_raw": posted_at,
        "crawled_at": now_iso,
        "detail_status": "success",
        "detail_attempts": 1,
        "detail_http_status": 200,
        "detail_error": "",
        "detail_crawled_at": now_iso
    }
    JobListingRaw(**listing_record)

    # 6. Benefits, Description, Requirements
    benefits_list = []
    for b in (item.get("benefits") or []):
        if isinstance(b, dict):
            b_name = b.get("benefitNameVI") or b.get("benefitName") or ""
            b_val = b.get("benefitValue") or ""
            benefits_list.append(f"{b_name}: {b_val}" if b_val else b_name)
    benefits_raw = "\n".join([b for b in benefits_list if b])

    desc_text = clean_html(item.get("jobDescription", ""))
    req_text = clean_html(item.get("jobRequirement", ""))

    # 7. Lĩnh vực (IndustriesV3) & Ngành nghề (jobFunction)
    ind_v3 = [
        i.get("industryV3NameVI") or i.get("industryV3Name")
        for i in (item.get("industriesV3") or [])
        if isinstance(i, dict) and (i.get("industryV3NameVI") or i.get("industryV3Name"))
    ]
    job_func = item.get("jobFunction") or {}
    parent_fn = job_func.get("parentNameVI") or job_func.get("parentName") or ""
    child_fns = [
        c.get("nameVI") or c.get("name")
        for c in job_func.get("children", [])
        if isinstance(c, dict) and (c.get("nameVI") or c.get("name"))
    ]
    func_str = f"{parent_fn} > {', '.join(child_fns)}" if parent_fn and child_fns else parent_fn

    if ind_v3 and func_str:
        industry_raw = f"{', '.join(ind_v3)} ({func_str})"
    elif ind_v3:
        industry_raw = ", ".join(ind_v3)
    elif func_str:
        industry_raw = func_str
    else:
        ind_list = item.get("industries") or []
        industry_raw = ", ".join([
            ind.get("industryNameVI", "") or ind.get("industryName", "")
            for ind in ind_list
            if isinstance(ind, dict) and (ind.get("industryNameVI") or ind.get("industryName"))
        ])

    # 8. Trình độ học vấn
    degree_mapping = {
        1: "Trung học",
        2: "Trung cấp",
        3: "Cao đẳng",
        4: "Cử nhân",
        5: "Thạc sĩ",
        6: "Tiến sĩ",
        7: "Khác"
    }
    education_raw = degree_mapping.get(item.get("highestDegreeId"), "")

    # 9. Loại hình làm việc & Thời gian làm việc
    working_type_mapping = {
        1: "Toàn thời gian",
        2: "Bán thời gian",
        3: "Thực tập",
        4: "Tạm thời / Dự án",
        5: "Khác"
    }
    working_time_raw = working_type_mapping.get(item.get("typeWorkingId"), "")
    if not working_time_raw and isinstance(item.get("typeWorking"), dict):
        working_time_raw = item.get("typeWorking", {}).get("name", "")

    emp_type = item.get("jobLevelVI") or item.get("jobLevel") or ""
    comp_size = item.get("companySizeVI") or item.get("companySize") or ""

    # 10. Chế độ làm việc (Work mode)
    search_wm = f"{title} {desc_text} {req_text} {loc_str}"
    work_mode_raw = ""
    for wm in ["Full-remote", "Remote", "Hybrid", "Onsite", "Làm từ xa"]:
        if re.search(r'\b' + re.escape(wm) + r'\b', search_wm, re.IGNORECASE):
            work_mode_raw = "Remote" if "remote" in wm.lower() or "từ xa" in wm.lower() else wm
            break
    if not work_mode_raw:
        work_mode_raw = "Onsite"

    # 11. Giới thiệu công ty
    overview_raw = str(
        item.get("companyProfile")
        or item.get("summary")
        or company_info.get("companyProfile")
        or ""
    ).strip()

    detail_record = {
        "detail_id": f"vietnamworks_{job_id}",
        "source": "vietnamworks",
        "source_job_id": job_id,
        "job_url": job_url,
        "title_raw": title,
        "company_name_raw": comp_name,
        "company_url": comp_url,
        "company_size_raw": comp_size,
        "company_location_raw": comp_loc,
        "industry_raw": industry_raw,
        "salary_raw": salary,
        "experience_raw": exp_str,
        "education_raw": education_raw,
        "location_raw": loc_str,
        "work_mode_raw": work_mode_raw,
        "employment_type_raw": emp_type,
        "working_time_raw": working_time_raw,
        "overview_raw": overview_raw,
        "responsibilities_raw": desc_text,
        "requirements_raw": req_text,
        "benefits_raw": benefits_raw,
        "required_skills_raw": skills_raw,
        "preferred_skills_raw": "",
        "published_at_raw": posted_at,
        "updated_at_raw": updated_at,
        "deadline_raw": deadline,
        "crawled_at": now_iso
    }
    JobDetailRaw(**detail_record)

    return listing_record, detail_record
