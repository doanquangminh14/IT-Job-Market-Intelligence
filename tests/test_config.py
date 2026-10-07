from src.utils.config import get_settings


def test_settings_load():
    s = get_settings()
    assert s.project_root.exists()
    assert "paths" in s.config


def test_paths_exist():
    s = get_settings()
    for key in ["raw", "bronze", "silver", "gold"]:
        assert s.path(key).exists()


def test_database_url_format():
    s = get_settings()
    assert s.database_url.startswith("postgresql+psycopg2://")