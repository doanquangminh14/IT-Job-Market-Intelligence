from src.crawlers.vietnamworks.parser import parse_job_item


def test_vietnamworks_parse_job_item(sample_vnw_job_item):
    listing, detail = parse_job_item(sample_vnw_job_item)

    assert listing["source"] == "vietnamworks"
    assert listing["source_job_id"] == "987654"
    assert "Backend Golang Engineer" in listing["title_raw"]
    assert listing["company_name_raw"] == "Fintech Vietnam"
    assert "$2000 - $3000" in listing["salary_raw"]
    assert "Golang, PostgreSQL, Docker" in listing["skills_raw"]

    assert detail["source_job_id"] == "987654"
    assert "microservices" in detail["responsibilities_raw"]
    assert "Tối thiểu 3 năm kinh nghiệm" in detail["requirements_raw"]
    assert "13th month salary" in detail["benefits_raw"]
    assert "2026-11-01" in detail["deadline_raw"]
