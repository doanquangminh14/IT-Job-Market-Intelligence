import json
import os
import pytest
from src.quality.rules import (
    ERR_CONTENT_TOO_SHORT,
    ERR_DATE_DEADLINE_BEFORE_PUBLISHED,
    ERR_DATE_FAR_PAST,
    ERR_MISSING_JOB_ID,
    ERR_MISSING_JOB_URL,
    ERR_MISSING_SOURCE,
    ERR_MISSING_TITLE,
    ERR_SALARY_INVERTED,
    ERR_SALARY_NEGATIVE,
    ERR_SALARY_OUTLIER,
    evaluate_invalid_rules,
    evaluate_quarantine_rules,
    evaluate_valid_rules,
    route_single_record,
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
        "published_at_raw": "2026-09-28",
        "deadline_raw": "2026-10-28",
        "crawled_at": "2026-10-11T10:00:00",
    }


# ==============================================================================
# 1. TEST CÁC QUY TẮC INVALID
# ==============================================================================

def test_valid_record_passes_all(sample_valid_job):
    status, errors = route_single_record(sample_valid_job)
    assert status == "valid"
    assert errors == []


def test_invalid_missing_job_url(sample_valid_job):
    bad_job = dict(sample_valid_job, job_url="")
    status, errors = route_single_record(bad_job)
    assert status == "invalid"
    assert ERR_MISSING_JOB_URL in errors


def test_invalid_missing_title(sample_valid_job):
    bad_job = dict(sample_valid_job, title_raw="   ")
    status, errors = route_single_record(bad_job)
    assert status == "invalid"
    assert ERR_MISSING_TITLE in errors


def test_invalid_missing_source(sample_valid_job):
    bad_job = dict(sample_valid_job, source="unknown_portal")
    status, errors = route_single_record(bad_job)
    assert status == "invalid"
    assert ERR_MISSING_SOURCE in errors


def test_invalid_missing_job_id(sample_valid_job):
    bad_job = dict(sample_valid_job, source_job_id="", detail_id="")
    status, errors = route_single_record(bad_job)
    assert status == "invalid"
    assert ERR_MISSING_JOB_ID in errors


def test_invalid_content_too_short(sample_valid_job):
    bad_job = dict(
        sample_valid_job,
        overview_raw="Chặn truy cập",
        responsibilities_raw="",
        requirements_raw="",
        benefits_raw="",
    )
    status, errors = route_single_record(bad_job, min_content_length=100)
    assert status == "invalid"
    assert ERR_CONTENT_TOO_SHORT in errors


# ==============================================================================
# 2. TEST CÁC QUY TẮC QUARANTINE (LOGIC BẤT THƯỜNG)
# ==============================================================================

def test_quarantine_salary_inverted(sample_valid_job):
    # Lương min lớn hơn lương max (40 - 20 triệu)
    bad_job = dict(sample_valid_job, salary_raw="40 - 20 triệu")
    status, errors = route_single_record(bad_job)
    assert status == "quarantine"
    assert ERR_SALARY_INVERTED in errors


def test_quarantine_salary_negative(sample_valid_job):
    bad_job = dict(sample_valid_job, salary_raw="-15 - 20 triệu")
    status, errors = route_single_record(bad_job)
    assert status == "quarantine"
    assert ERR_SALARY_NEGATIVE in errors


def test_quarantine_salary_outlier(sample_valid_job):
    bad_job = dict(sample_valid_job, salary_raw="1,000 - 80,000 USD")
    status, errors = route_single_record(bad_job)
    assert status == "quarantine"
    assert ERR_SALARY_OUTLIER in errors


def test_quarantine_deadline_before_published(sample_valid_job):
    # Hạn nộp ngày 01/09 nhưng đăng ngày 28/09
    bad_job = dict(sample_valid_job, published_at_raw="2026-09-28", deadline_raw="2026-09-01")
    status, errors = route_single_record(bad_job)
    assert status == "quarantine"
    assert ERR_DATE_DEADLINE_BEFORE_PUBLISHED in errors


def test_quarantine_date_far_past(sample_valid_job):
    bad_job = dict(sample_valid_job, published_at_raw="2018-05-10")
    status, errors = route_single_record(bad_job)
    assert status == "quarantine"
    assert ERR_DATE_FAR_PAST in errors


# ==============================================================================
# 3. TEST VALIDATOR 3-WAY ROUTING & PERSISTENCE
# ==============================================================================

def test_validator_route_records(sample_valid_job, tmp_path):
    validator = QualityValidator(
        bronze_dir=str(tmp_path / "bronze"),
        quarantine_dir=str(tmp_path / "quarantine"),
        invalid_dir=str(tmp_path / "invalid"),
    )

    valid_job = sample_valid_job
    quarantine_job = dict(sample_valid_job, detail_id="topcv_999", salary_raw="50 - 20 triệu")
    invalid_job = dict(sample_valid_job, detail_id="topcv_888", title_raw="")

    records = [valid_job, quarantine_job, invalid_job]
    v_list, q_list, i_list, summary = validator.route_records(records)

    assert len(v_list) == 1
    assert len(q_list) == 1
    assert len(i_list) == 1

    assert summary["total_scanned"] == 3
    assert summary["valid_count"] == 1
    assert summary["quarantine_count"] == 1
    assert summary["invalid_count"] == 1
    assert ERR_SALARY_INVERTED in summary["errors_breakdown"]
    assert ERR_MISSING_TITLE in summary["errors_breakdown"]


def test_validator_save_all_layers(sample_valid_job, tmp_path):
    b_dir = str(tmp_path / "bronze")
    q_dir = str(tmp_path / "quarantine")
    i_dir = str(tmp_path / "invalid")

    validator = QualityValidator(bronze_dir=b_dir, quarantine_dir=q_dir, invalid_dir=i_dir)

    # 1. Lưu Bronze
    b_path = validator.save_valid_to_bronze([sample_valid_job], "topcv", "2026-10-11")
    assert os.path.exists(b_path)

    # 2. Lưu Quarantine
    q_path = validator.save_to_quarantine([sample_valid_job], "topcv", "2026-10-11")
    assert os.path.exists(q_path)

    # 3. Lưu Invalid
    i_path = validator.save_to_invalid([sample_valid_job], "topcv", "2026-10-11")
    assert os.path.exists(i_path)
