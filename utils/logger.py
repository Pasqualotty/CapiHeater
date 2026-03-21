"""
Logging setup: file handler + optional SQLite activity_logs insertion.
"""

import logging
import os
import sqlite3
from logging.handlers import RotatingFileHandler

from utils.config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger that writes to console and rotating file."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log_activity(
    db_path: str,
    account_id: int,
    action_type: str,
    status: str,
    target_username: str | None = None,
    target_url: str | None = None,
    error_message: str | None = None,
):
    """Insert a row into the activity_logs table."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO activity_logs
                (account_id, action_type, target_username, target_url, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (account_id, action_type, target_username, target_url, status, error_message),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as exc:
        logging.getLogger(__name__).error(f"Failed to write activity log: {exc}")
