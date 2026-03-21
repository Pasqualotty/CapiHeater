"""
Global configuration constants for CapiHeater.

When running as a PyInstaller --onefile bundle the ``CAPIHEATER_BASE_DIR``
environment variable (set by ``main.py``) points to the directory that
contains the ``.exe``.  All mutable data (database, logs, profiles) is
stored relative to that directory so the app works portably.
"""

import os
import sys

# Application
APP_NAME = "CapiHeater"

# Base directory: frozen .exe location or source tree root
if os.environ.get("CAPIHEATER_BASE_DIR"):
    APP_DIR = os.environ["CAPIHEATER_BASE_DIR"]
elif getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Internal data bundled by PyInstaller (read-only)
if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = APP_DIR

# Database
DB_PATH = os.path.join(APP_DIR, "data", "capiheater.db")
DATA_DIR = os.path.join(APP_DIR, "data")


def get_user_db_path(user_id: str) -> str:
    """Return a per-user database path based on the user's ID."""
    safe_id = user_id.replace("-", "")[:16]
    return os.path.join(DATA_DIR, f"capiheater_{safe_id}.db")

# Concurrency
MAX_WORKERS = 3

# Logging
LOG_DIR = os.path.join(APP_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "capiheater.log")
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# Schedules — look inside the bundle first, then fall back to APP_DIR
DEFAULT_SCHEDULE_PATH = os.path.join(BUNDLE_DIR, "schedules", "default_schedule.json")

# Humanizer timing (seconds)
MIN_ACTION_DELAY = 2.0
MAX_ACTION_DELAY = 8.0
MEAN_ACTION_DELAY = 4.0
STD_ACTION_DELAY = 1.5

MIN_PAGE_LOAD_WAIT = 3.0
MAX_PAGE_LOAD_WAIT = 7.0

MIN_SCROLL_PAUSE = 0.5
MAX_SCROLL_PAUSE = 2.5

# Browser
HEADLESS = False
USER_DATA_DIR = os.path.join(APP_DIR, "browser_profiles")
