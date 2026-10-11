import os
from src.profiling import DataProfiler, ReportGenerator, detect_job_language


def test_detect_job_language():
    vi_text = "Tuyển dụng kỹ sư phần mềm backend. Yêu cầu có 3 năm kinh nghiệm lập trình và bảo hiểm đầy đủ."
    assert detect_job_language(vi_text) == "vi"

    en_text = "We are looking for a Senior Software Engineer with strong experience in building scalable microservices and cloud architectures."
    assert detect_job_language(en_text) == "en"

    mixed_text = "Tuyển dụng Senior Backend. Responsibilities include designing system architecture, leading technical requirements, and mentoring team members. Chế độ phúc lợi đầy đủ."
    assert detect_job_language(mixed_text) == "mixed"


def test_profiler_with_mock_data(tmp_path):
    mock_raw = tmp_path / "data" / "raw"
    topcv_list_dir = mock_raw / "topcv" / "listings" / "2026-10-11"
    topcv_det_dir = mock_raw / "topcv" / "details" / "2026-10-11"
    topcv_list_dir.mkdir(parents=True)
    topcv_det_dir.mkdir(parents=True)

    # 1. Tạo mock listings với 1 URL trùng lặp
    import json
    mock_listings = [
        {
            "source": "topcv", "source_job_id": "1", "job_url": "https://topcv.vn/1",
            "detail_status": "success", "title_raw": "Python Dev", "company_name_raw": "Company A"
        },
        {
            "source": "topcv", "source_job_id": "1", "job_url": "https://topcv.vn/1",
            "detail_status": "success", "title_raw": "Python Dev", "company_name_raw": "Company A"
        },
        {
            "source": "topcv", "source_job_id": "2", "job_url": "https://topcv.vn/2",
            "detail_status": "failed", "title_raw": "Java Dev", "company_name_raw": "Company B"
        }
    ]
    with open(topcv_list_dir / "page_001.json", "w", encoding="utf-8") as f:
        json.dump(mock_listings, f)

    # 2. Tạo mock details (1 có lương số, 1 có lương thỏa thuận)
    mock_details = [
        {
            "detail_id": "topcv_1", "source": "topcv", "source_job_id": "1", "job_url": "https://topcv.vn/1",
            "title_raw": "Python Dev", "company_name_raw": "Company A", "salary_raw": "20 - 30 triệu",
            "deadline_raw": "2026-11-30", "responsibilities_raw": "Phát triển phần mềm", "requirements_raw": "Kinh nghiệm Python"
        },
        {
            "detail_id": "topcv_2", "source": "topcv", "source_job_id": "2", "job_url": "https://topcv.vn/2",
            "title_raw": "Java Dev", "company_name_raw": "Company B", "salary_raw": "Thỏa thuận",
            "deadline_raw": "", "responsibilities_raw": "", "requirements_raw": ""
        }
    ]
    with open(topcv_det_dir / "TCV001.json", "w", encoding="utf-8") as f:
        json.dump(mock_details, f)

    # 3. Chạy Profiler
    profiler = DataProfiler(raw_dir=str(mock_raw))
    res = profiler.run_profiling(target_date="2026-10-11")

    assert res["sources_count"] == 3
    topcv_res = res["sources"]["topcv"]
    assert topcv_res["total_listings"] == 3
    assert topcv_res["duplicate_urls"] == 1
    assert topcv_res["duplicate_job_ids"] == 1
    assert topcv_res["success_details"] == 2
    assert topcv_res["failed_details"] == 1
    assert topcv_res["salary_breakdown"]["has_numeric_range"] == 1
    assert topcv_res["salary_breakdown"]["negotiable"] == 1
    assert topcv_res["deadline_stats"]["valid_date"] == 1
    assert topcv_res["deadline_stats"]["missing"] == 1

    # 4. Chạy Reporter
    report_dir = tmp_path / "reports"
    reporter = ReportGenerator(output_dir=str(report_dir))
    md_file, csv_file = reporter.save_reports(res)

    assert os.path.exists(md_file)
    assert os.path.exists(csv_file)
