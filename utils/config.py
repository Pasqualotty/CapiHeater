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

# User data directory — stored in AppData so updates never affect it
_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
DATA_DIR = os.path.join(_APPDATA, "CapiHeater", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Database
DB_PATH = os.path.join(DATA_DIR, "capiheater.db")


def get_user_db_path(user_id: str) -> str:
    """Return a per-user database path based on the user's ID."""
    safe_id = user_id.replace("-", "")[:16]
    return os.path.join(DATA_DIR, f"capiheater_{safe_id}.db")

# Concurrency
MAX_WORKERS = 3

# Logging — also in AppData
LOG_DIR = os.path.join(_APPDATA, "CapiHeater", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
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

# Scroll behavior defaults
DEFAULT_SCROLL_CONFIG = {
    "scroll_small_min": 200,
    "scroll_small_max": 400,
    "scroll_medium_min": 450,
    "scroll_medium_max": 750,
    "scroll_large_min": 800,
    "scroll_large_max": 1400,
    "weight_scroll_small": 32,
    "weight_scroll_medium": 28,
    "weight_scroll_large": 10,
    "weight_pause_read": 22,
    "weight_distracted_pause": 8,
    "pause_after_small_min": 1.5,
    "pause_after_small_max": 3.0,
    "pause_after_medium_min": 1.5,
    "pause_after_medium_max": 3.0,
    "pause_after_large_min": 0.8,
    "pause_after_large_max": 1.5,
    "distracted_pause_min": 5.0,
    "distracted_pause_max": 12.0,
    "post_read_time_min": 5.0,
    "post_read_time_max": 15.0,
    "comment_read_time_min": 2.0,
    "comment_read_time_max": 6.0,
    "hover_chance": 0.12,
}

SCROLL_PRESETS = {
    "Lento": {
        "scroll_small_min": 100, "scroll_small_max": 250,
        "scroll_medium_min": 300, "scroll_medium_max": 500,
        "scroll_large_min": 550, "scroll_large_max": 900,
        "weight_scroll_small": 38, "weight_scroll_medium": 25,
        "weight_scroll_large": 5, "weight_pause_read": 25,
        "weight_distracted_pause": 7,
        "pause_after_small_min": 2.5, "pause_after_small_max": 5.0,
        "pause_after_medium_min": 2.0, "pause_after_medium_max": 4.0,
        "pause_after_large_min": 1.5, "pause_after_large_max": 3.0,
        "distracted_pause_min": 8.0, "distracted_pause_max": 18.0,
        "post_read_time_min": 8.0, "post_read_time_max": 25.0,
        "comment_read_time_min": 3.0, "comment_read_time_max": 10.0,
        "hover_chance": 0.15,
    },
    "Normal": None,  # Uses DEFAULT_SCROLL_CONFIG
    "Rapido": {
        "scroll_small_min": 300, "scroll_small_max": 550,
        "scroll_medium_min": 600, "scroll_medium_max": 1000,
        "scroll_large_min": 1100, "scroll_large_max": 1800,
        "weight_scroll_small": 25, "weight_scroll_medium": 32,
        "weight_scroll_large": 18, "weight_pause_read": 18,
        "weight_distracted_pause": 7,
        "pause_after_small_min": 0.8, "pause_after_small_max": 1.8,
        "pause_after_medium_min": 0.8, "pause_after_medium_max": 1.5,
        "pause_after_large_min": 0.5, "pause_after_large_max": 1.0,
        "distracted_pause_min": 3.0, "distracted_pause_max": 7.0,
        "post_read_time_min": 3.0, "post_read_time_max": 10.0,
        "comment_read_time_min": 1.5, "comment_read_time_max": 4.0,
        "hover_chance": 0.08,
    },
}

# Browser
HEADLESS = False
USER_DATA_DIR = os.path.join(APP_DIR, "browser_profiles")
