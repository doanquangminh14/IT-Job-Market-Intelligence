from datetime import datetime, timedelta
from src.crawlers.base import clean_html, fix_encoding, parse_relative_deadline


def test_clean_html():
    raw_html = "<div><p>Hello <b>World</b></p><br/><ul><li>Item 1</li><li>Item 2</li></ul></div>"
    cleaned = clean_html(raw_html)
    assert "Hello World" in cleaned
    assert "Item 1" in cleaned
    assert "Item 2" in cleaned
    assert "<p>" not in cleaned


def test_fix_encoding():
    text = "  Software    Engineer   \t\n  "
    fixed = fix_encoding(text)
    assert fixed == "Software Engineer"


def test_parse_relative_deadline():
    base = datetime(2026, 10, 11)
    # 1. 'Còn 15 ngày'
    res = parse_relative_deadline("Hạn nộp hồ sơ: Còn 15 ngày", base_date=base)
    expected = (base + timedelta(days=15)).strftime("%Y-%m-%d")
    assert res == expected

    # 2. '5 days left'
    res2 = parse_relative_deadline("Urgent: 5 days left", base_date=base)
    expected2 = (base + timedelta(days=5)).strftime("%Y-%m-%d")
    assert res2 == expected2

    # 3. 'Hôm nay hết hạn'
    res3 = parse_relative_deadline("Hôm nay hết hạn", base_date=base)
    assert res3 == "2026-10-11"

    # 4. DD/MM/YYYY
    res4 = parse_relative_deadline("Hạn chót: 30/11/2026")
    assert res4 == "2026-11-30"
