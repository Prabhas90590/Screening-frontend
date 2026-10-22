"""Application logging configuration and structured diagnostic loggers.

Provides dual-output logging:
1. Real-time console output in the terminal.
2. Rotating log file at 'backend/logs/screening.log' for persistent developer inspection.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional


LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "screening.log"


def configure_logging(debug: bool = False) -> None:
    """Initialize root application logging to both console and a rotating file."""
    log_level = logging.DEBUG if debug else logging.INFO

    # Ensure log directory exists
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    handlers = [logging.StreamHandler(sys.stdout)]

    # Add rotating file handler (5MB per file, keeps last 3 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(file_handler)
    except Exception as e:
        # If file permission issue, continue with stream handler
        sys.stderr.write(f"Warning: could not initialize file logger: {e}\n")

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )


class DiagnosticLogger:
    """Standardized diagnostic logger helper to ensure consistent troubleshooting tags."""

    def __init__(self, component: str):
        self._logger = logging.getLogger(f"app.{component}")
        self.component = component

    def provider_info(self, provider: str, message: str, *args):
        self._logger.info(f"[PROVIDER:{provider.upper()}] {message}", *args)

    def provider_warn(self, provider: str, message: str, *args):
        self._logger.warning(f"[PROVIDER:{provider.upper()}] {message}", *args)

    def provider_error(self, provider: str, message: str, *args):
        self._logger.error(f"[PROVIDER:{provider.upper()}] {message}", *args)

    def normalize_warn(self, ticker: str, message: str, *args):
        self._logger.warning(f"[NORMALIZE:{ticker}] {message}", *args)

    def normalize_debug(self, ticker: str, message: str, *args):
        self._logger.debug(f"[NORMALIZE:{ticker}] {message}", *args)

    def calc_info(self, metric: str, ticker: str, message: str, *args):
        self._logger.info(f"[CALC:{metric.upper()}:{ticker}] {message}", *args)

    def calc_warn(self, metric: str, ticker: str, message: str, *args):
        self._logger.warning(f"[CALC:{metric.upper()}:{ticker}] {message}", *args)

    def rule_info(self, stage: str, ticker: str, message: str, *args):
        self._logger.info(f"[RULE:{stage.upper()}:{ticker}] {message}", *args)
