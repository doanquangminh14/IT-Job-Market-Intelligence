from bs4 import BeautifulSoup
from src.crawlers.topcv.parser import parse_job_card, parse_job_detail_html


def test_topcv_parse_job_card(sample_topcv_card_html):
    soup = BeautifulSoup(sample_topcv_card_html, "html.parser")
    box = soup.find("div", class_="job-item-2")
    job = parse_job_card(box, page=1)

    assert job is not None
    assert job["source_job_id"] == "123456"
    assert "Senior Python Developer" in job["title_raw"]
    assert job["company_name_raw"] == "Tech Corp"
    assert "25 - 35 triệu" in job["salary_raw"]
    assert "Hà Nội" in job["location_raw"]
    assert "3 năm" in job["experience_raw"]
    assert "Python" in job["skills_raw"]


def test_topcv_parse_detail(sample_topcv_detail_html):
    job_item = {
        "source": "topcv",
        "source_job_id": "123456",
        "job_url": "https://www.topcv.vn/viec-lam/123456.html",
        "title_raw": "Senior Python Developer",
        "company_name_raw": "Tech Corp",
        "salary_raw": "25 - 35 triệu",
        "location_raw": "Hà Nội",
        "experience_raw": "3 năm",
        "skills_raw": "Python",
        "company_logo_url": ""
    }

    detail, updated_listing = parse_job_detail_html(
        html=sample_topcv_detail_html,
        job_item=job_item,
        company_overview="Tech Corp Overview"
    )

    assert detail is not None
    assert detail["source_job_id"] == "123456"
    assert "Senior Python Developer" in detail["title_raw"]
    assert "Tech Corp" in detail["company_name_raw"]
    assert "FastAPI" in detail["responsibilities_raw"]
    assert "3 năm kinh nghiệm" in detail["requirements_raw"]
    assert "Lương tháng 13" in detail["benefits_raw"]
    assert detail["deadline_raw"] == "2026-11-30"
