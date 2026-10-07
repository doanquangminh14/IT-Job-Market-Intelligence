"""Kiểm tra setup: thư mục, config, logging, biến môi trường."""
from __future__ import annotations

import sys

from src.utils.config import get_settings
from src.utils.logging_utils import get_logger, setup_logging

REQUIRED_PATH_KEYS = ["raw", "bronze", "silver", "gold", "logs"]


def main() -> int:
    settings = get_settings()
    setup_logging(settings.log_level, settings.path("logs") / "pipeline.log")
    logger = get_logger(__name__)

    logger.info("Project root: %s", settings.project_root)
    logger.info("APP_ENV=%s | LOG_LEVEL=%s", settings.app_env, settings.log_level)

    ok = True
    for key in REQUIRED_PATH_KEYS:
        p = settings.path(key)
        if p.exists():
            logger.info("OK      %-7s -> %s", key, p)
        else:
            logger.error("MISSING %-7s -> %s", key, p)
            ok = False

    if not settings.db_password or settings.db_password == "change_me":
        logger.warning("DB_PASSWORD chưa được đặt trong .env (cần ở Task 05)")

    logger.info("Setup check %s", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())