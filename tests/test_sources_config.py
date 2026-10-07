from src.utils.config import get_settings


def test_both_sources_configured():
    sources = get_settings().config["sources"]
    assert {"source_01_vietjobs", "source_02_arbeitnow"} <= set(sources)


def test_source_flags():
    sources = get_settings().config["sources"]
    assert sources["source_01_vietjobs"]["is_snapshot"] is True
    assert sources["source_02_arbeitnow"]["is_snapshot"] is False
    assert sources["source_02_arbeitnow"]["base_url"].startswith("https://")