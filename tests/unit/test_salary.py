import pytest

from src.data_cleaning.salary import parse_salary_vnd, SALARY_MIN_VND, SALARY_MAX_VND

M = 1_000_000
USD = 25_400


@pytest.mark.parametrize("raw,expected", [
    ("15 - 20 triệu", (15 * M, 20 * M)),
    ("Tới 30 triệu", (None, 30 * M)),
    ("Từ 10 triệu", (10 * M, None)),
    ("15tr-20tr", (15 * M, 20 * M)),
    ("$ 1,000 - 2,000", (1000 * USD, 2000 * USD)),
    ("Thỏa thuận", (None, None)),
    ("", (None, None)),
    (None, (None, None)),
])
def test_common_formats(raw, expected):
    assert parse_salary_vnd(raw) == expected


def test_month_suffix_is_not_million():
    """Lỗi cũ: chữ M trong 'MONTH' bị hiểu là triệu ➔ 1,4×10^13."""
    assert parse_salary_vnd("14000000 - 18000000 MONTH") == (14 * M, 18 * M)


def test_yearly_salary_is_divided_by_12():
    mn, mx = parse_salary_vnd("200tr-500tr ₫/năm")
    assert mn == pytest.approx(200 * M / 12) and mx == pytest.approx(500 * M / 12)
    mn, mx = parse_salary_vnd("$ 24,000-29,000 /năm")
    assert mn == pytest.approx(24000 * USD / 12) and mx == pytest.approx(29000 * USD / 12)


def test_bare_numbers_are_usd_when_in_usd_range():
    assert parse_salary_vnd("500 - 2000") == (500 * USD, 2000 * USD)
    assert parse_salary_vnd("Lên tới 3000") == (None, 3000 * USD)


@pytest.mark.parametrize("raw", ["$ 1-1 /tháng", "S$ 110,000-220,000 /tháng", "23000", "500000", "Tới 0.5 triệu"])
def test_implausible_values_are_dropped(raw):
    assert parse_salary_vnd(raw) == (None, None)


def test_title_is_only_a_fallback():
    # chuỗi lương gốc có số ➔ dùng nó, bỏ qua tiêu đề
    assert parse_salary_vnd("20 - 30 triệu", "Dev 10 - 15M") == (20 * M, 30 * M)
    # chuỗi gốc không có số ➔ lấy từ tiêu đề
    assert parse_salary_vnd("Thỏa thuận", "Backend Dev 15 - 20M") == (15 * M, 20 * M)
    # 'Mobile' không phải đơn vị 'm'
    assert parse_salary_vnd("", "Dev 3 - 5 Mobile") == (None, None)


def test_all_outputs_within_plausible_range():
    for raw in ["15 - 20 triệu", "$ 1,000 - 2,000", "200tr-500tr ₫/năm", "500 - 2000"]:
        for v in parse_salary_vnd(raw):
            assert v is None or SALARY_MIN_VND <= v <= SALARY_MAX_VND
