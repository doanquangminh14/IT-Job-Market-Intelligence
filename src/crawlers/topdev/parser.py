import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from src.crawlers.base import clean_html, fix_encoding, parse_relative_deadline
from src.schemas.job import JobDetailRaw


def decode_nextjs_payload(html: str) -> str:
    """Trích xuất và giải mã luồng Next.js RSC stream (self.__next_f.push) từ trang HTML TopDev."""
    if not html:
        return ""
    pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
    if not pushes:
        return ""
    return "".join(pushes).encode('utf-8').decode('unicode_escape', errors='ignore')


def parse_job_listings_from_html(html: str, page: int) -> List[Dict[str, Any]]:
    """
    Bóc tách danh sách job từ luồng Next.js RSC của trang tìm kiếm TopDev.
    Trích xuất đầy đủ: title, company, logo, lương, địa điểm, kinh nghiệm ngay từ listing.
    """
    decoded = decode_nextjs_payload(html)
    found_items: List[Dict[str, Any]] = []
    seen: set = set()

    # 1. Trích xuất các object job đầy đủ từ Next.js payload bằng raw_decode
    decoder = json.JSONDecoder()
    pattern = re.compile(r'\{"id":(\d{5,8}),"title":"')

    for m in pattern.finditer(decoded):
        start = m.start()
        try:
            obj, _ = decoder.raw_decode(decoded[start:])
            if isinstance(obj, dict) and "id" in obj and "title" in obj and "company" in obj:
                jid = str(obj.get("id"))
                if jid in seen:
                    continue
                seen.add(jid)

                title = fix_encoding(obj.get("title", ""))
                slug = obj.get("slug", "")
                detail_url = obj.get("detail_url") or f"https://topdev.vn/viec-lam/{slug}-{jid}"

                comp = obj.get("company", {})
                comp_name = fix_encoding(comp.get("display_name", ""))
                comp_logo = comp.get("image_logo", "") or ""

                addr = obj.get("addresses", {})
                loc = fix_encoding(addr.get("sort_addresses") or addr.get("address_region_list") or "")
                loc = loc.strip(" -")

                sal_obj = obj.get("salary", {})
                if sal_obj.get("is_negotiable") == "1":
                    salary = "Thương lượng"
                elif sal_obj.get("min") and sal_obj.get("max") and (sal_obj.get("min") > 0 or sal_obj.get("max") > 0):
                    currency = sal_obj.get("currency", "VND")
                    salary = f"{sal_obj['min']:,} - {sal_obj['max']:,} {currency}"
                elif sal_obj.get("value"):
                    salary = fix_encoding(sal_obj.get("value"))
                else:
                    salary = "Thương lượng"

                exp = fix_encoding(obj.get("experiences_str", ""))
                skills = fix_encoding(obj.get("skills_str") or ", ".join(obj.get("skills_arr", []) if isinstance(obj.get("skills_arr"), list) else []))
                posted_at = obj.get("published", {}).get("date") or obj.get("created_at") or ""

                found_items.append({
                    "source": "topdev",
                    "source_job_id": jid,
                    "job_url": detail_url,
                    "company_logo_url": comp_logo,
                    "title_raw": title,
                    "company_name_raw": comp_name,
                    "location_raw": loc,
                    "salary_raw": salary,
                    "experience_raw": exp,
                    "skills_raw": skills,
                    "posted_at_raw": str(posted_at),
                    "crawled_at": datetime.now().isoformat(),
                    "detail_status": "pending",
                    "detail_attempts": 0,
                    "detail_http_status": None,
                    "detail_error": "",
                    "detail_file": "",
                    "detail_crawled_at": None
                })
        except Exception:
            continue

    # 2. Fallback: Nếu còn link nào chưa được parse qua object, bổ sung qua regex slug
    matches = re.findall(r'/viec-lam/([a-zA-Z0-9\-_]+-(\d{5,8}))', decoded)
    for slug, jid in matches:
        if jid not in seen:
            seen.add(jid)
            found_items.append({
                "source": "topdev",
                "source_job_id": jid,
                "job_url": f"https://topdev.vn/viec-lam/{slug}",
                "company_logo_url": "",
                "title_raw": "",
                "company_name_raw": "",
                "location_raw": "",
                "salary_raw": "Thương lượng",
                "experience_raw": "",
                "skills_raw": "",
                "posted_at_raw": "",
                "crawled_at": datetime.now().isoformat(),
                "detail_status": "pending",
                "detail_attempts": 0,
                "detail_http_status": None,
                "detail_error": "",
                "detail_file": "",
                "detail_crawled_at": None
            })

    return found_items


def parse_job_detail_html(
    html: str,
    job_item: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Bóc tách trang chi tiết TopDev kết hợp từ Schema JSON-LD, luồng Next.js RSC và DOM:
    - Bóc tách tiêu đề, công ty, logo, địa chỉ chi tiết
    - Bóc tách mức lương, cấp bậc, kinh nghiệm, chế độ làm việc
    - Trích xuất 3 mục: Vai trò, Kỹ năng, Quyền lợi
    - Bóc tách Hạn nộp (với fallback)
    - Validate qua JobDetailRaw schema
    Trả về (detail_record, updated_listing)
    """
    soup = BeautifulSoup(html, "html.parser")
    decoded = decode_nextjs_payload(html)

    job_id = str(job_item["source_job_id"])
    job_url = job_item["job_url"]
    updated_listing = dict(job_item)

    # 1. Trích xuất Schema JSON-LD JobPosting
    ld_data: Dict[str, Any] = {}
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            content = (s.string if s.string else s.text) or ""
            d = json.loads(content)
            if d.get("@type") == "JobPosting":
                ld_data = d
                break
        except Exception:
            continue

    # Tiêu đề & Công ty
    title = ld_data.get("title", "")
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

    comp_data = ld_data.get("hiringOrganization") or {}
    comp_name = comp_data.get("name", "") or job_item.get("company_name_raw", "")
    comp_logo = comp_data.get("logo", "") or job_item.get("company_logo_url", "")
    comp_url = comp_data.get("sameAs", "")

    # 2. Header Grid: Location, Cấp bậc (Level), Kinh nghiệm (Experience)
    location_raw = ""
    level_raw = ""
    experience_raw = ""

    header_grid = soup.find("div", class_=lambda c: c and "grid-cols-2" in c and "md:gap-16" in c)
    if header_grid:
        items = [child.get_text(separator=" ", strip=True) for child in header_grid.children if child.name]
        if len(items) >= 1:
            location_raw = items[0]
        if len(items) >= 2:
            level_raw = items[1]
        if len(items) >= 3:
            experience_raw = items[2]

    if not location_raw:
        loc_data = ld_data.get("jobLocation") or {}
        addr_data = loc_data.get("address") or {} if isinstance(loc_data, dict) else {}
        location_raw = (
            addr_data.get("addressLocality")
            or addr_data.get("addressRegion")
            or addr_data.get("streetAddress")
            or ""
        )

    # 3. Chế độ làm việc (Work mode)
    work_mode_raw = ""
    full_text = soup.get_text(separator=" ", strip=True)
    for wm in ["Fulltime", "Full-time", "Part-time", "Parttime", "Remote", "Hybrid", "Onsite"]:
        if re.search(r'\b' + wm + r'\b', full_text, re.IGNORECASE):
            work_mode_raw = wm
            break

    # 4. Mức lương chuẩn hóa
    salary_raw = "Thương lượng"
    sal_match = re.search(r'"salary":\s*(\{[^}]+\})', decoded)
    if sal_match:
        try:
            sal_obj = json.loads(sal_match.group(1))
            if sal_obj.get("is_negotiable") == "1":
                salary_raw = "Thương lượng"
            elif sal_obj.get("min") and sal_obj.get("max") and (sal_obj.get("min") > 0 or sal_obj.get("max") > 0):
                currency = sal_obj.get("currency", "VND")
                salary_raw = f"{sal_obj['min']:,} - {sal_obj['max']:,} {currency}"
            elif sal_obj.get("value") and "Th" in sal_obj.get("value"):
                salary_raw = "Thương lượng"
        except Exception:
            pass

    if salary_raw == "Thương lượng":
        base_sal = ld_data.get("baseSalary") or {}
        val = base_sal.get("value") if isinstance(base_sal, dict) else ""
        if isinstance(val, dict):
            if val.get("minValue") or val.get("maxValue"):
                salary_raw = f"{val.get('minValue', '')} - {val.get('maxValue', '')} {val.get('unitText', '')}".strip()

    # 5. Company Info & Overview từ RSC stream
    comp_overview = ""
    comp_detail_url = ""
    comp_address_str = ""

    comp_pattern = re.compile(r'\{"id":\d+,"display_name":"[^"]+","image_logo":')
    decoder = json.JSONDecoder()
    for m in comp_pattern.finditer(decoded):
        start = m.start()
        try:
            c_obj, _ = decoder.raw_decode(decoded[start:])
            if isinstance(c_obj, dict) and "display_name" in c_obj and "description" in c_obj:
                raw_desc = c_obj.get("description", "")
                comp_overview = fix_encoding(clean_html(raw_desc))
                comp_detail_url = c_obj.get("detail_url") or c_obj.get("website") or ""
                if not comp_name and c_obj.get("display_name"):
                    comp_name = fix_encoding(c_obj.get("display_name"))
                if not comp_logo and c_obj.get("image_logo"):
                    comp_logo = c_obj.get("image_logo")
                break
        except Exception:
            continue

    if comp_detail_url:
        comp_url = comp_detail_url

    # Trích xuất địa chỉ công ty chi tiết từ RSC stream
    m_ref = re.search(r'full_addresses":\s*"\$([a-zA-Z0-9]+)"', decoded)
    if m_ref:
        ref_id = m_ref.group(1)
        m_arr = re.search(r'\b' + ref_id + r':(\[[^\]]+\])', decoded)
        if m_arr:
            try:
                addrs = json.loads(m_arr.group(1))
                comp_address_str = "; ".join([fix_encoding(a) for a in addrs if a])
            except Exception:
                pass

    # 6. Company Box: Ngành nghề, Quy mô công ty
    industry_raw = ""
    company_size_raw = ""
    for row in soup.find_all("div", class_=lambda c: c and "items-center" in c and "justify-between" in c):
        text = row.get_text(strip=True)
        spans = row.find_all("span")
        if len(spans) >= 2:
            val_text = spans[1].get_text(separator=" ", strip=True)
            if "Ngành nghề" in text:
                industry_raw = val_text
            elif "Quy mô công ty" in text:
                company_size_raw = val_text

    if not industry_raw:
        industry_raw = str(ld_data.get("industry") or "Information Technology")

    # 7. Các Section chi tiết: 1 Vai trò, 2 Kỹ năng, 3 Quyền lợi
    responsibilities_raw = ""
    requirements_raw = ""
    benefits_raw = ""

    for num, title_kw, target in [("1", "Vai trò", "resp"), ("2", "Kỹ năng", "req"), ("3", "Quyền lợi", "ben")]:
        span = soup.find(lambda t: t.name == "span" and num in t.get_text() and title_kw in t.get_text())
        if span:
            parent = span.parent
            content_el = span.find_next_sibling() or parent.find_next_sibling()
            if content_el:
                txt = clean_html(str(content_el))
                if target == "resp":
                    responsibilities_raw = txt
                elif target == "req":
                    requirements_raw = txt
                elif target == "ben":
                    benefits_raw = txt

    # Fallback an toàn nếu tin không chia theo 3 section chuẩn
    if not responsibilities_raw:
        responsibilities_raw = clean_html(ld_data.get("description", ""))
    if not responsibilities_raw:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            txt = heading.get_text(strip=True).lower()
            if "job description" in txt or "mô tả công việc" in txt:
                container = heading.find_next_sibling() or heading.parent
                if container:
                    responsibilities_raw = clean_html(str(container))
                    break
    if not benefits_raw:
        b = ld_data.get("jobBenefits")
        benefits_raw = clean_html(b) if isinstance(b, str) else ("\n".join(b) if isinstance(b, list) else "")
    if not requirements_raw:
        exp_req = ld_data.get("experienceRequirements", "")
        requirements_raw = clean_html(exp_req) if isinstance(exp_req, str) else ""
    if not requirements_raw:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            txt = heading.get_text(strip=True).lower()
            if "job requirements" in txt or "yêu cầu công việc" in txt:
                container = heading.find_next_sibling() or heading.parent
                if container:
                    requirements_raw = clean_html(str(container))
                    break

    # 8. Working Time & Location
    working_time_raw = ""
    for tag in soup.find_all(lambda t: t.name in ["div", "p", "li", "span"] and "Working time:" in t.get_text()):
        line = tag.get_text(strip=True)
        m = re.search(r"Working time:\s*(.*?)(?:\n|$|Working Location)", line, re.IGNORECASE)
        if m:
            working_time_raw = m.group(1).strip()
            break
        elif "Working time:" in line:
            working_time_raw = line
            break

    # 9. Skills & Dates
    skills_raw = str(ld_data.get("skills") or "")
    if not skills_raw:
        skill_tags = soup.find_all("a", href=lambda h: h and "/tim-kiem?skills=" in h)
        if skill_tags:
            skills_raw = ", ".join([s.get_text(strip=True) for s in skill_tags])

    posted_at = str(ld_data.get("datePosted") or "")
    deadline = str(ld_data.get("validThrough") or "")
    if not deadline:
        deadline = parse_relative_deadline(full_text)
    now_iso = datetime.now().isoformat()

    # Cập nhật thông tin Listing
    updated_listing.update({
        "company_logo_url": comp_logo,
        "title_raw": title,
        "company_name_raw": comp_name,
        "location_raw": location_raw,
        "salary_raw": salary_raw,
        "experience_raw": experience_raw,
        "skills_raw": skills_raw or updated_listing.get("skills_raw", ""),
        "posted_at_raw": posted_at,
        "detail_status": "success",
        "detail_error": "",
        "detail_crawled_at": now_iso
    })

    # Chi tiết job đầy đủ chuẩn xác
    detail_record = {
        "detail_id": f"topdev_{job_id}",
        "source": "topdev",
        "source_job_id": job_id,
        "job_url": job_url,
        "title_raw": title,
        "company_name_raw": comp_name,
        "company_url": comp_url,
        "company_size_raw": company_size_raw,
        "company_location_raw": comp_address_str or location_raw,
        "industry_raw": industry_raw,
        "salary_raw": salary_raw,
        "experience_raw": experience_raw,
        "education_raw": "",
        "location_raw": location_raw,
        "work_mode_raw": work_mode_raw,
        "employment_type_raw": level_raw,
        "working_time_raw": working_time_raw,
        "overview_raw": comp_overview,
        "responsibilities_raw": responsibilities_raw,
        "requirements_raw": requirements_raw,
        "benefits_raw": benefits_raw,
        "required_skills_raw": skills_raw or updated_listing.get("skills_raw", ""),
        "preferred_skills_raw": "",
        "published_at_raw": posted_at,
        "updated_at_raw": "",
        "deadline_raw": deadline,
        "crawled_at": now_iso
    }

    # Validate qua Pydantic schema
    JobDetailRaw(**detail_record)

    return detail_record, updated_listing
