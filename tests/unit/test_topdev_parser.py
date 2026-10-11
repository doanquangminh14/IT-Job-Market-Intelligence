from src.crawlers.topdev.parser import decode_nextjs_payload, parse_job_detail_html


def test_topdev_decode_nextjs_payload():
    html = '<script>self.__next_f.push([1,"1:{\\"name\\":\\"TopDev\\"}\\n"])</script>'
    decoded = decode_nextjs_payload(html)
    assert '{"name":"TopDev"}' in decoded


def test_topdev_parse_detail(sample_topdev_detail_html):
    job_item = {
        "source": "topdev",
        "source_job_id": "999",
        "job_url": "https://topdev.vn/viec-lam/data-engineer-999",
        "title_raw": "Data Engineer (PySpark)",
        "company_name_raw": "Data Solutions Ltd",
        "company_logo_url": "",
        "location_raw": "Hồ Chí Minh",
        "salary_raw": "Thương lượng",
        "experience_raw": "3 năm",
        "skills_raw": "Python, Spark"
    }

    detail, updated_listing = parse_job_detail_html(
        html=sample_topdev_detail_html,
        job_item=job_item
    )

    assert detail is not None
    assert detail["source_job_id"] == "999"
    assert "Data Engineer" in detail["title_raw"]
    assert "Data Solutions Ltd" in detail["company_name_raw"]
    assert "Apache Spark" in detail["responsibilities_raw"]
    assert "Python, SQL, Spark" in detail["requirements_raw"]
    assert detail["deadline_raw"] != ""  # Parsed from 'Còn 15 ngày'
