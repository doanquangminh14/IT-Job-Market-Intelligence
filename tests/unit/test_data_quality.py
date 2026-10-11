import json
import os
import pytest
from src.quality.rules import (
    ERR_CONTENT_TOO_SHORT,
    ERR_MISSING_JOB_ID,
    ERR_MISSING_JOB_URL,
    ERR_MISSING_SOURCE,
    ERR_MISSING_TITLE,
    evaluate_valid_rules,
)
from src.quality.validator import QualityValidator


@pytest.fixture
def sample_valid_job():
    return {
        "detail_id": "topcv_123456",
        "source": "topcv",
        "source_job_id": "123456",
        "job_url": "https://www.topcv.vn/viec-lam/python-developer/123456.html",
        "title_raw": "Senior Python Developer",
        "company_name_raw": "Tech Innovations Vietnam",
        "overview_raw": "Công ty phần mềm hàng đầu chuyên về các giải pháp trí tuệ nhân tạo và dữ liệu lớn tại TP.HCM.",
        "responsibilities_raw": "Phát triển các hệ thống backend chịu tải cao bằng Python, FastAPI, Docker và Kubernetes.",
        "requirements_raw": "Tối thiểu 3 năm kinh nghiệm với Python, thành thạo RESTful API, PostgreSQL và CI/CD.",
        "benefits_raw": "Lương tháng 13, bảo hiểm sức khỏe cao cấp, thưởng hiệu suất hàng quý, du lịch hàng năm.",
        "salary_raw": "25 - 40 triệu",
        "crawled_at": "2026-10-11T10:00:00",
    }


def test_valid_record_passes(sample_valid_job):
    is_valid, errors = evaluate_valid_rules(sample_valid_job)
    assert is_valid is True
    assert errors == []


def test_missing_or_invalid_job_url(sample_valid_job):
    # Rỗng
    bad_job = dict(sample_valid_job, job_url="")
    is_valid, errors = evaluate_valid_rules(bad_job)
    assert is_valid is False
    assert ERR_MISSING_JOB_URL in errors

    # Không phải URL
    bad_job2 = dict(sample_valid_job, job_url="not_a_url")
    is_valid2, errors2 = evaluate_valid_rules(bad_job2)
    assert is_valid2 is False
    assert ERR_MISSING_JOB_URL in errors2


def test_missing_title(sample_valid_job):
    bad_job = dict(sample_valid_job, title_raw="   ")
    is_valid, errors = evaluate_valid_rules(bad_job)
    assert is_valid is False
    assert ERR_MISSING_TITLE in errors

    bad_job2 = dict(sample_valid_job, title_raw="A")
    is_valid2, errors2 = evaluate_valid_rules(bad_job2)
    assert is_valid2 is False
    assert ERR_MISSING_TITLE in errors2


def test_missing_or_invalid_source(sample_valid_job):
    bad_job = dict(sample_valid_job, source="unknown_portal")
    is_valid, errors = evaluate_valid_rules(bad_job)
    assert is_valid is False
    assert ERR_MISSING_SOURCE in errors


def test_missing_job_id(sample_valid_job):
    bad_job = dict(sample_valid_job, source_job_id="", detail_id="")
    is_valid, errors = evaluate_valid_rules(bad_job)
    assert is_valid is False
    assert ERR_MISSING_JOB_ID in errors


def test_content_too_short(sample_valid_job):
    # Nội dung quá ngắn (dấu hiệu trang lỗi captcha / bot block)
    bad_job = dict(
        sample_valid_job,
        overview_raw="Chặn truy cập",
        responsibilities_raw="",
        requirements_raw="",
        benefits_raw="",
    )
    is_valid, errors = evaluate_valid_rules(bad_job, min_content_length=100)
    assert is_valid is False
    assert ERR_CONTENT_TOO_SHORT in errors


def test_validator_enrich_and_filter(sample_valid_job, tmp_path):
    validator = QualityValidator(bronze_dir=str(tmp_path))

    # Test validate_record
    enriched = validator.validate_record(sample_valid_job)
    assert enriched["_dq_status"] == "valid"
    assert enriched["_dq_errors"] == []
    assert "_dq_checked_at" in enriched

    # Test filter_valid_records
    invalid_job = dict(sample_valid_job, title_raw="")
    records = [sample_valid_job, invalid_job]

    valid_list, summary = validator.filter_valid_records(records)
    assert len(valid_list) == 1
    assert summary["total_scanned"] == 2
    assert summary["valid_count"] == 1
    assert summary["invalid_count"] == 1
    assert summary["valid_rate_pct"] == 50.0
    assert ERR_MISSING_TITLE in summary["errors_breakdown"]


def test_validator_save_to_bronze(sample_valid_job, tmp_path):
    validator = QualityValidator(bronze_dir=str(tmp_path))
    valid_list = [validator.validate_record(sample_valid_job)]

    saved_path = validator.save_valid_to_bronze(
        valid_records=valid_list,
        source="topcv",
        target_date="2026-10-11",
        file_prefix="bronze_001",
    )

    assert os.path.exists(saved_path)
    with open(saved_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["title_raw"] == "Senior Python Developer"
    assert data[0]["_dq_status"] == "valid"
