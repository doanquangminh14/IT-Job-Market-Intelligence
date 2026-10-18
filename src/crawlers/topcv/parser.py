import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag

from src.crawlers.base import clean_html, parse_relative_deadline
from src.schemas.job import JobDetailRaw


def parse_job_card(card: Tag, page: int) -> Optional[Dict[str, Any]]:
    """
    Bóc tách 1 thẻ tin tuyển dụng từ trang tìm kiếm TopCV.
    Trả về dict raw listing chứa đầy đủ thông tin tóm tắt.
    """
    jid = card.get("data-job-id") or ""
    if not jid:
        return None
    jid = str(jid).strip()

    # Tiêu đề & URL bài tuyển dụng
    title_el = card.select_one(".title a, h3 a, .job-title a")
    title = title_el.get_text(strip=True) if title_el else ""
    job_url = title_el.get("href") if title_el else ""
    if job_url and "?" in job_url:
        job_url = job_url.split("?")[0]

    # Công ty & Logo
    comp_el = card.select_one(".company, .company-name, a.company")
    comp_name = comp_el.get_text(strip=True) if comp_el else ""
    logo_el = card.select_one("img")
    comp_logo = logo_el.get("src") if logo_el else ""

    # Mức lương
    sal_el = card.select_one(".salary, .title-salary")
    salary = sal_el.get_text(strip=True) if sal_el else "Thoả thuận"

    # Địa điểm & Kinh nghiệm
    addr_el = card.select_one(".address")
    location = addr_el.get_text(strip=True) if addr_el else ""
    location = location.replace("(mới)", "").strip()

    exp_el = card.select_one(".exp")
    experience = exp_el.get_text(strip=True) if exp_el else ""

    # Trích xuất tags & kỹ năng từ card
    tags: List[str] = []
    tag_container = card.select_one(".tag")
    if tag_container:
        for span in tag_container.select(".item-tag"):
            t_text = span.get("title") or span.get_text(strip=True)
            if t_text and t_text not in tags and not t_text.endswith("..."):
                tags.append(t_text)
        rem = tag_container.select_one(".remaining-items")
        if rem:
            rem_title = rem.get("title") or rem.get("data-original-title") or rem.get("data-bs-title") or ""
            if rem_title:
                for item in rem_title.split(","):
                    item = item.strip()
                    if item and item not in tags:
                        tags.append(item)

    skills_raw = ", ".join(tags)

    # Ngày đăng bài
    posted_el = card.select_one(".label-update, .address.label-update")
    posted_at = posted_el.get_text(strip=True) if posted_el else ""

    return {
        "source": "topcv",
        "source_job_id": jid,
        "job_url": job_url,
        "company_logo_url": comp_logo or "",
        "title_raw": title,
        "company_name_raw": comp_name,
        "location_raw": location,
        "salary_raw": salary,
        "experience_raw": experience,
        "skills_raw": skills_raw,
        "posted_at_raw": posted_at,
        "crawled_at": datetime.now().isoformat(),
        "detail_status": "pending",
        "detail_attempts": 0,
        "detail_http_status": None,
        "detail_error": "",
        "detail_file": "",
        "detail_crawled_at": None
    }


def parse_company_overview_html(html: str) -> str:
    """Bóc tách giới thiệu công ty từ HTML trang hồ sơ công ty TopCV."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    box_desc = soup.select_one(".box-company-description, .company-intro, .box-description")
    if box_desc:
        desc = clean_html(str(box_desc))
        if desc:
            return desc
    return ""


def parse_job_detail_html(
    html: str,
    job_item: Dict[str, Any],
    company_overview: str = ""
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Bóc tách trang chi tiết TopCV:
    - Trích xuất Schema JSON-LD JobPosting
    - Trích xuất Sidebar Thông tin công ty & Box Thông tin chung
    - Bóc tách Mô tả, Yêu cầu, Quyền lợi
    - Trích xuất Deadline (với cơ chế Fallback)
    - Validate bằng JobDetailRaw schema
    Trả về (detail_record, updated_listing_record)
    """
    soup = BeautifulSoup(html, "html.parser")
    ld_data: Dict[str, Any] = {}

    # 1. Trích xuất Schema JSON-LD JobPosting
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            content = (s.string if s.string else s.text) or ""
            d = json.loads(content)
            if d.get("@type") == "JobPosting":
                ld_data = d
                break
        except Exception:
            continue

    job_id = str(job_item["source_job_id"])
    job_url = job_item["job_url"]

    # Tiêu đề & Công ty
    title = ld_data.get("title") or job_item.get("title_raw", "")
    hiring_org = ld_data.get("hiringOrganization") or {}
    comp_name = hiring_org.get("name") or job_item.get("company_name_raw", "")
    comp_url = hiring_org.get("sameAs") or ""
    comp_logo = hiring_org.get("logo") or job_item.get("company_logo_url", "")

    # Địa chỉ làm việc chi tiết
    job_loc = ld_data.get("jobLocation") or {}
    addr_dict = job_loc.get("address") or {} if isinstance(job_loc, dict) else {}
    loc_parts = []
    if isinstance(addr_dict, dict):
        for k in ["streetAddress", "addressLocality", "addressRegion"]:
            val = addr_dict.get(k)
            if val and val not in loc_parts:
                loc_parts.append(val)
    location_raw = ", ".join(loc_parts) if loc_parts else job_item.get("location_raw", "")

    # Lương & Kinh nghiệm
    sal_obj = ld_data.get("baseSalary") or {}
    sal_val = sal_obj.get("value") if isinstance(sal_obj, dict) else ""
    if isinstance(sal_val, dict):
        min_v = sal_val.get("minValue")
        max_v = sal_val.get("maxValue")
        val = sal_val.get("value")
        if min_v is not None and max_v is not None and min_v != "" and max_v != "":
            if min_v == max_v:
                salary_raw = str(min_v)
            else:
                salary_raw = f"{min_v} - {max_v}"
        elif min_v is not None and min_v != "":
            salary_raw = f"Từ {min_v}"
        elif max_v is not None and max_v != "":
            salary_raw = f"Lên tới {max_v}"
        elif val is not None and val != "":
            salary_raw = str(val)
        else:
            salary_raw = job_item.get("salary_raw", "")
    elif isinstance(sal_val, str) and sal_val:
        salary_raw = sal_val
    else:
        salary_raw = job_item.get("salary_raw", "Thương lượng")

    exp_req = ld_data.get("experienceRequirements") or {}
    months_exp = exp_req.get("monthsOfExperience") if isinstance(exp_req, dict) else None
    if months_exp:
        years = months_exp // 12
        experience_raw = f"{years} năm" if years > 0 else f"{months_exp} tháng"
    else:
        experience_raw = job_item.get("experience_raw", "")

    # 2. Bóc tách từ Sidebar Thông tin công ty (.box-company-info-detail)
    company_size_raw = ""
    company_location_raw = ""
    industry_raw = ld_data.get("industry") or ""

    for c_item in soup.select(".box-company-info-detail__list--item"):
        c_text = c_item.get_text(separator=" ", strip=True)
        c_text_lower = c_text.lower()
        if "quy mô" in c_text_lower:
            company_size_raw = re.sub(r"^quy\s*mô\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()
        elif "địa điểm" in c_text_lower:
            tooltip = c_item.select_one('[data-toggle="tooltip"], [title]')
            if tooltip and tooltip.get("title"):
                company_location_raw = tooltip.get("title").strip()
            else:
                company_location_raw = re.sub(r"^địa\s*điểm\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()
        elif "ngành nghề" in c_text_lower and not industry_raw:
            industry_raw = re.sub(r"^ngành\s*nghề\s*:?\s*", "", c_text, flags=re.IGNORECASE).strip()

    if not company_location_raw:
        company_location_raw = location_raw
    if not industry_raw:
        industry_raw = "Công nghệ thông tin / Phần mềm"

    # 3. Bóc tách từ Box Thông tin chung (.box-job-information-general-info-list__item)
    education_raw = ""
    work_mode_raw = ""
    emp_type_raw = ld_data.get("occupationalCategory") or ""
    working_time_raw = "Toàn thời gian" if ld_data.get("employmentType") == "FULL_TIME" else (str(ld_data.get("employmentType") or ""))

    for g_item in soup.select(".box-job-information-general-info-list__item"):
        g_text = g_item.get_text(separator=" ", strip=True)
        g_text_lower = g_text.lower()
        if "học vấn" in g_text_lower:
            education_raw = re.sub(r"^học\s*vấn\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
        elif "hình thức làm việc" in g_text_lower:
            raw_wm = re.sub(r"^hình\s*thức\s*làm\s*việc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
            if "onsite" in raw_wm.lower() or "văn phòng" in raw_wm.lower():
                work_mode_raw = "Onsite"
            elif "remote" in raw_wm.lower() or "từ xa" in raw_wm.lower():
                work_mode_raw = "Remote"
            elif "hybrid" in raw_wm.lower():
                work_mode_raw = "Hybrid"
            else:
                work_mode_raw = raw_wm
        elif "cấp bậc" in g_text_lower and not emp_type_raw:
            emp_type_raw = re.sub(r"^cấp\s*bậc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()
        elif "loại hình làm việc" in g_text_lower:
            working_time_raw = re.sub(r"^loại\s*hình\s*làm\s*việc\s*:?\s*", "", g_text, flags=re.IGNORECASE).strip()

    # Fallback work_mode nếu chưa có
    if not work_mode_raw:
        search_text = f"{title} {location_raw}"
        for wm in ["Full-remote", "Remote", "Hybrid", "Onsite", "Làm từ xa"]:
            if re.search(r'\b' + re.escape(wm) + r'\b', search_text, re.IGNORECASE):
                work_mode_raw = "Remote" if "remote" in wm.lower() or "từ xa" in wm.lower() else wm
                break
    if not work_mode_raw:
        work_mode_raw = "Onsite"

    # Ngày đăng & Hạn nộp
    posted_at = str(ld_data.get("datePosted") or job_item.get("posted_at_raw", ""))
    deadline = str(ld_data.get("validThrough") or "")
    if not deadline:
        deadline = parse_relative_deadline(soup.get_text(separator=" ", strip=True))

    # 4. Bóc tách 3 phần: Mô tả công việc, Yêu cầu ứng viên, Quyền lợi
    responsibilities_raw = ""
    requirements_raw = ""
    benefits_raw = clean_html(ld_data.get("jobBenefits", ""))

    desc_html = ld_data.get("description", "")
    if desc_html:
        desc_soup = BeautifulSoup(desc_html, "html.parser")
        current_sec = ""
        resp_chunks, req_chunks, ben_chunks = [], [], []

        for el in desc_soup.children:
            if not el.name:
                continue
            txt = el.get_text(strip=True)
            if "mô tả công việc" in txt.lower():
                current_sec = "resp"
            elif "yêu cầu ứng viên" in txt.lower() or "yêu cầu công việc" in txt.lower():
                current_sec = "req"
            elif "quyền lợi" in txt.lower():
                current_sec = "ben"
            else:
                if current_sec == "resp":
                    resp_chunks.append(clean_html(str(el)))
                elif current_sec == "req":
                    req_chunks.append(clean_html(str(el)))
                elif current_sec == "ben":
                    ben_chunks.append(clean_html(str(el)))

        responsibilities_raw = "\n".join([c for c in resp_chunks if c])
        requirements_raw = "\n".join([c for c in req_chunks if c])
        if not benefits_raw:
            benefits_raw = "\n".join([c for c in ben_chunks if c])

    if not responsibilities_raw:
        for item in soup.select(".job-description__item, .job-data, .job-description"):
            t = item.get_text(separator=" ", strip=True).lower()
            if "mô tả" in t:
                responsibilities_raw = clean_html(str(item))
            elif "yêu cầu" in t and not requirements_raw:
                requirements_raw = clean_html(str(item))
            elif "quyền lợi" in t and not benefits_raw:
                benefits_raw = clean_html(str(item))

    if not responsibilities_raw:
        responsibilities_raw = clean_html(desc_html)

    skills_raw = job_item.get("skills_raw", "")
    now_iso = datetime.now().isoformat()

    # Cập nhật lại bản ghi listing
    updated_listing = dict(job_item)
    updated_listing.update({
        "title_raw": title,
        "company_name_raw": comp_name,
        "company_logo_url": comp_logo,
        "location_raw": location_raw,
        "salary_raw": salary_raw,
        "experience_raw": experience_raw,
        "skills_raw": skills_raw,
        "posted_at_raw": posted_at,
        "detail_status": "success",
        "detail_error": "",
        "detail_crawled_at": now_iso
    })

    # Bản ghi Detail hoàn chỉnh
    detail_record = {
        "detail_id": f"topcv_{job_id}",
        "source": "topcv",
        "source_job_id": job_id,
        "job_url": job_url,
        "title_raw": title,
        "company_name_raw": comp_name,
        "company_url": comp_url,
        "company_size_raw": company_size_raw,
        "company_location_raw": company_location_raw,
        "industry_raw": industry_raw,
        "salary_raw": salary_raw,
        "experience_raw": experience_raw,
        "education_raw": education_raw,
        "location_raw": location_raw,
        "work_mode_raw": work_mode_raw,
        "employment_type_raw": emp_type_raw,
        "working_time_raw": working_time_raw,
        "overview_raw": company_overview,
        "responsibilities_raw": responsibilities_raw,
        "requirements_raw": requirements_raw,
        "benefits_raw": benefits_raw,
        "required_skills_raw": skills_raw,
        "preferred_skills_raw": "",
        "published_at_raw": posted_at,
        "updated_at_raw": "",
        "deadline_raw": deadline,
        "crawled_at": now_iso
    }

    # Validate qua Pydantic schema
    JobDetailRaw(**detail_record)

    return detail_record, updated_listing
