"""Cấu hình logging dùng chung cho toàn project."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
_CONFIGURED = False


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Cấu hình root logger một lần duy nhất (console + file xoay vòng)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())
    formatter = logging.Formatter(_LOG_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Lấy logger theo tên module, ví dụ get_logger(__name__)."""
    return logging.getLogger(name)