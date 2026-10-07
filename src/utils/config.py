"""Đọc cấu hình từ .env và configs/config.yaml."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


@dataclass(frozen=True)
class Settings:
    project_root: Path
    app_env: str
    log_level: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    config: dict[str, Any]

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL (dùng từ Task 05)."""
        pwd = quote_plus(self.db_password)
        return (
            f"postgresql+psycopg2://{self.db_user}:{pwd}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def path(self, key: str) -> Path:
        """Trả về đường dẫn tuyệt đối theo khóa trong config.paths (raw/bronze/silver/gold/logs)."""
        try:
            relative = self.config["paths"][key]
        except KeyError as exc:
            raise KeyError(f"Không có paths.{key} trong config.yaml") from exc
        return self.project_root / relative


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Nạp settings một lần và cache lại."""
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        project_root=PROJECT_ROOT,
        app_env=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "it_jobs"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", ""),
        config=_load_yaml(CONFIG_PATH),
    )