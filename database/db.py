"""
SQLite connection manager and database initialization.
"""

import json
import os
import sqlite3
from pathlib import Path


class Database:
    """Manages SQLite database connections and schema initialization."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self):
        """Create the parent directory for the database file if needed."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Return a new SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self):
        """Create all tables and insert default data if not present."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    schedule_json TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    cookies_json TEXT NOT NULL,
                    proxy TEXT DEFAULT NULL,
                    status TEXT DEFAULT 'idle',
                    schedule_id INTEGER DEFAULT 1,
                    start_date TEXT NOT NULL,
                    current_day INTEGER DEFAULT 1,
                    scroll_config TEXT DEFAULT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    target_username TEXT,
                    target_url TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT DEFAULT NULL,
                    executed_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_categories (
                    account_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    PRIMARY KEY (account_id, category_id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS target_categories (
                    target_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    PRIMARY KEY (target_id, category_id),
                    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    target_username TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    schedule_day INTEGER NOT NULL,
                    executed_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                )
            """)

            # --- Migrations for existing databases ---
            # Add scroll_config column if missing (v0.7.1+)
            cols = {r[1] for r in cursor.execute("PRAGMA table_info(accounts)").fetchall()}
            if "scroll_config" not in cols:
                cursor.execute("ALTER TABLE accounts ADD COLUMN scroll_config TEXT DEFAULT NULL")

            # Insert default schedules if none exist
            cursor.execute("SELECT COUNT(*) FROM schedules")
            if cursor.fetchone()[0] == 0:
                self._insert_all_schedules(cursor)

            conn.commit()
        finally:
            conn.close()

    def _insert_all_schedules(self, cursor: sqlite3.Cursor):
        """Insert all three default schedule templates."""
        from utils.config import DEFAULT_SCHEDULE_PATH

        # --- Padrao (14 dias) ---
        if os.path.exists(DEFAULT_SCHEDULE_PATH):
            with open(DEFAULT_SCHEDULE_PATH, "r", encoding="utf-8") as f:
                padrao = json.load(f)
        else:
            padrao = self._fallback_default_schedule()

        cursor.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            ("Padrao", "Cronograma progressivo de 14 dias - equilibrado", json.dumps(padrao)),
        )

        # --- Conservador (21 dias, crescimento lento, mais browse) ---
        conservador = [
            {"day": 1,  "likes": 2,  "follows": 0, "retweets": 0, "unfollows": 0, "browse_before_min": 900, "browse_before_max": 1200, "browse_between_min": 180, "browse_between_max": 420, "posts_to_open": 3, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 2,  "likes": 3,  "follows": 0, "retweets": 0, "unfollows": 0, "browse_before_min": 900, "browse_before_max": 1200, "browse_between_min": 180, "browse_between_max": 420, "posts_to_open": 3, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 3,  "likes": 4,  "follows": 1, "retweets": 0, "unfollows": 0, "browse_before_min": 720, "browse_before_max": 1080, "browse_between_min": 180, "browse_between_max": 360, "posts_to_open": 4, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 4,  "likes": 5,  "follows": 1, "retweets": 0, "unfollows": 0, "browse_before_min": 720, "browse_before_max": 1080, "browse_between_min": 180, "browse_between_max": 360, "posts_to_open": 4, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 5,  "likes": 6,  "follows": 2, "retweets": 1, "unfollows": 0, "browse_before_min": 600, "browse_before_max": 900, "browse_between_min": 120, "browse_between_max": 300, "posts_to_open": 4, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 6,  "likes": 7,  "follows": 2, "retweets": 1, "unfollows": 0, "browse_before_min": 600, "browse_before_max": 900, "browse_between_min": 120, "browse_between_max": 300, "posts_to_open": 4, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 7,  "likes": 8,  "follows": 3, "retweets": 1, "unfollows": 1, "browse_before_min": 600, "browse_before_max": 900, "browse_between_min": 120, "browse_between_max": 300, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 8,  "likes": 9,  "follows": 3, "retweets": 1, "unfollows": 1, "browse_before_min": 600, "browse_before_max": 900, "browse_between_min": 120, "browse_between_max": 300, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 9,  "likes": 10, "follows": 3, "retweets": 2, "unfollows": 1, "browse_before_min": 480, "browse_before_max": 720, "browse_between_min": 120, "browse_between_max": 240, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 10, "likes": 11, "follows": 4, "retweets": 2, "unfollows": 1, "browse_before_min": 480, "browse_before_max": 720, "browse_between_min": 120, "browse_between_max": 240, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 11, "likes": 12, "follows": 4, "retweets": 2, "unfollows": 2, "browse_before_min": 480, "browse_before_max": 720, "browse_between_min": 120, "browse_between_max": 240, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 12, "likes": 13, "follows": 5, "retweets": 2, "unfollows": 2, "browse_before_min": 480, "browse_before_max": 720, "browse_between_min": 120, "browse_between_max": 240, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 13, "likes": 14, "follows": 5, "retweets": 3, "unfollows": 2, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 14, "likes": 15, "follows": 5, "retweets": 3, "unfollows": 2, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 15, "likes": 16, "follows": 6, "retweets": 3, "unfollows": 2, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 16, "likes": 17, "follows": 6, "retweets": 3, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 17, "likes": 18, "follows": 7, "retweets": 3, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 18, "likes": 19, "follows": 7, "retweets": 4, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 19, "likes": 20, "follows": 8, "retweets": 4, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 20, "likes": 20, "follows": 8, "retweets": 4, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
            {"day": 21, "likes": 20, "follows": 8, "retweets": 4, "unfollows": 3, "browse_before_min": 300, "browse_before_max": 600, "browse_between_min": 60, "browse_between_max": 180, "posts_to_open": 5, "view_comments_chance": 0.4, "likes_on_feed": True, "follow_initial_count": 2},
        ]
        cursor.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            ("Conservador", "Crescimento lento em 21 dias - menor risco de ban", json.dumps(conservador)),
        )

        # --- Agressivo (7 dias, crescimento rapido, menos browse) ---
        agressivo = [
            {"day": 1, "likes": 5,  "follows": 2,  "retweets": 1,  "unfollows": 0, "browse_before_min": 300, "browse_before_max": 480, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 1, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 2, "likes": 10, "follows": 5,  "retweets": 2,  "unfollows": 1, "browse_before_min": 300, "browse_before_max": 480, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 1, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 3, "likes": 15, "follows": 8,  "retweets": 4,  "unfollows": 2, "browse_before_min": 180, "browse_before_max": 360, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 2, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 4, "likes": 20, "follows": 10, "retweets": 5,  "unfollows": 3, "browse_before_min": 180, "browse_before_max": 360, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 2, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 5, "likes": 25, "follows": 12, "retweets": 6,  "unfollows": 4, "browse_before_min": 120, "browse_before_max": 300, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 2, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 6, "likes": 30, "follows": 15, "retweets": 8,  "unfollows": 5, "browse_before_min": 120, "browse_before_max": 300, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 2, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
            {"day": 7, "likes": 35, "follows": 18, "retweets": 10, "unfollows": 7, "browse_before_min": 120, "browse_before_max": 300, "browse_between_min": 60, "browse_between_max": 120, "posts_to_open": 2, "view_comments_chance": 0.2, "likes_on_feed": False, "follow_initial_count": 3},
        ]
        cursor.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            ("Agressivo", "Crescimento rapido em 7 dias - maior risco de ban", json.dumps(agressivo)),
        )

    # ------------------------------------------------------------------
    # Convenience query methods
    # ------------------------------------------------------------------

    def execute(self, query: str, params: tuple = ()) -> int:
        """Execute a write query and return ``lastrowid``."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        """Execute a read query and return the first row as a dict (or None)."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a read query and return all rows as a list of dicts."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _fallback_default_schedule() -> list:
        """Return a minimal default schedule as a Python list."""
        return [
            {"day": 1, "likes": 3, "follows": 0, "retweets": 0, "unfollows": 0},
            {"day": 2, "likes": 5, "follows": 1, "retweets": 0, "unfollows": 0},
            {"day": 3, "likes": 7, "follows": 2, "retweets": 1, "unfollows": 0},
            {"day": 4, "likes": 10, "follows": 3, "retweets": 1, "unfollows": 0},
            {"day": 5, "likes": 12, "follows": 4, "retweets": 2, "unfollows": 1},
            {"day": 6, "likes": 14, "follows": 5, "retweets": 2, "unfollows": 1},
            {"day": 7, "likes": 16, "follows": 6, "retweets": 3, "unfollows": 2},
            {"day": 8, "likes": 18, "follows": 7, "retweets": 3, "unfollows": 2},
            {"day": 9, "likes": 20, "follows": 8, "retweets": 4, "unfollows": 3},
            {"day": 10, "likes": 22, "follows": 9, "retweets": 4, "unfollows": 3},
            {"day": 11, "likes": 24, "follows": 10, "retweets": 5, "unfollows": 4},
            {"day": 12, "likes": 26, "follows": 10, "retweets": 5, "unfollows": 4},
            {"day": 13, "likes": 28, "follows": 11, "retweets": 6, "unfollows": 5},
            {"day": 14, "likes": 30, "follows": 12, "retweets": 6, "unfollows": 5},
        ]
