import pandas as pd
import pytest

from src.data_cleaning.dedup import company_key, companies_compatible, company_tokens, deduplicate_jobs, title_key
from src.data_cleaning.location import extract_city


@pytest.mark.parametrize("loc,expected", [
    ("hanoi", "Hà Nội"),
    ("Ha Noi, Vietnam", "Hà Nội"),
    ("Cầu Giấy, Hà Nội", "Hà Nội"),
    ("district 1, ho chi minh city, vietnam", "Hồ Chí Minh"),
    ("Sài Gòn", "Hồ Chí Minh"),
    ("Quận Hải Châu, Đà Nẵng", "Đà Nẵng"),
    ("Hà Nội; Hồ Chí Minh", "Hà Nội"),            # lấy thành phố xuất hiện đầu tiên
    ("Hồ Chí Minh; Hà Nội", "Hồ Chí Minh"),
    ("kcn Quế Võ, Bắc Ninh", "Khác"),
    ("Thanh Hóa", "Khác"),                         # 'hn' không được khớp nhầm trong từ khác
    ("remote vietnam", "Toàn quốc"),
    ("", "Toàn quốc"),
    (None, "Toàn quốc"),
])
def test_extract_city(loc, expected):
    assert extract_city(loc) == expected


def test_company_matching_handles_variants():
    assert company_key("Thương Mại và Truyền Thông HTC") == company_key("Truyền thông & Thương mại HTC")
    assert companies_compatible(company_tokens("MBBANK"), company_tokens("NGÂN HÀNG TMCP QUÂN ĐỘI – MBBANK"))
    assert not companies_compatible(company_tokens("FPT Software"), company_tokens("Viettel"))


def test_title_key_drops_posting_code():
    assert title_key("FullStack Developer (2025TD943)") == title_key("fullstack developer")


def _row(jid, company, title, desc, deadline="2026-12-01", city="Hà Nội", exp=1.0):
    return dict(job_id=jid, company_name=company, title=title, description_clean=desc,
                deadline=deadline, city=city, experience_min=exp)


def test_dedup_keeps_latest_deadline_and_merges_company_variants():
    desc = "xay dung api backend python django postgresql " * 20
    other = "thiet ke do hoa photoshop illustrator branding " * 20
    df = pd.DataFrame([
        _row("a", "MBBANK", "Backend Developer", desc, "2026-01-01"),
        _row("b", "NGÂN HÀNG TMCP QUÂN ĐỘI – MBBANK", "Backend Developer", desc, "2026-06-01"),
        _row("c", "Công ty ABC", "Backend Developer", other),          # công ty khác -> giữ
        _row("d", "Công ty ABC", "Graphic Designer", other),           # tiêu đề khác -> giữ
    ])
    out, rep = deduplicate_jobs(df)
    assert set(out.job_id) == {"b", "c", "d"}
    assert rep.loc[0, "job_id"] == "a" and rep.loc[0, "kept_job_id"] == "b"


def test_dedup_does_not_merge_different_roles_sharing_boilerplate():
    boiler = "gioi thieu cong ty phuc loi bao hiem thuong nghi mat " * 30
    df = pd.DataFrame([
        _row("x", "Acme", "Business Analyst", boiler + " phan tich nghiep vu"),
        _row("y", "Acme", "Cloud Engineer", boiler + " ha tang cloud"),
    ])
    out, _ = deduplicate_jobs(df)
    assert len(out) == 2
