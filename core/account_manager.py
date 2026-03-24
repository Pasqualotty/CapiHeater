"""
AccountManager - CRUD operations for Twitter/X accounts.
"""

import json
from datetime import date

from database.db import Database
from utils.config import DB_PATH


class AccountManager:
    """Manage accounts stored in the database."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(DB_PATH)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def add_account(
        self,
        username: str,
        cookies_json: str | dict | list,
        proxy: str | None = None,
        schedule_id: int = 1,
        start_date: str | None = None,
    ) -> int:
        """Insert a new account and return its id.

        Parameters
        ----------
        username : str
            Twitter/X handle (without @).
        cookies_json : str | dict | list
            Browser cookies as JSON string or Python object.
        proxy : str, optional
            Proxy URL (e.g. ``socks5://host:port``).
        schedule_id : int
            Foreign key to the schedules table (default 1).
        start_date : str, optional
            Schedule start date in ``YYYY-MM-DD`` format.  Defaults to today.

        Returns
        -------
        int
            The newly created account row id.
        """
        if not isinstance(cookies_json, str):
            cookies_json = json.dumps(cookies_json)

        if start_date is None:
            start_date = date.today().isoformat()

        query = """
            INSERT INTO accounts (username, cookies_json, proxy, schedule_id, start_date, status)
            VALUES (?, ?, ?, ?, ?, 'idle')
        """
        return self.db.execute(query, (username, cookies_json, proxy, schedule_id, start_date))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_account(self, account_id: int) -> dict | None:
        """Fetch a single account by id."""
        query = "SELECT * FROM accounts WHERE id = ?"
        row = self.db.fetch_one(query, (account_id,))
        return row

    def get_all_accounts(self) -> list[dict]:
        """Return every account in the database."""
        query = "SELECT * FROM accounts ORDER BY id"
        return self.db.fetch_all(query)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_account(self, account_id: int, **kwargs) -> None:
        """Update arbitrary columns on an account.

        Example::

            manager.update_account(1, proxy="socks5://new:1080", schedule_id=2)
        """
        if not kwargs:
            return

        # Serialise cookies if passed as non-string
        if "cookies_json" in kwargs and not isinstance(kwargs["cookies_json"], str):
            kwargs["cookies_json"] = json.dumps(kwargs["cookies_json"])

        columns = ", ".join(f"{col} = ?" for col in kwargs)
        values = list(kwargs.values()) + [account_id]
        query = f"UPDATE accounts SET {columns} WHERE id = ?"
        self.db.execute(query, tuple(values))

    def update_status(self, account_id: int, status: str) -> None:
        """Convenience method to change an account's status.

        Common statuses: ``idle``, ``running``, ``paused``, ``error``, ``completed``.
        """
        self.update_account(account_id, status=status)

    def reset_schedule(self, account_id: int) -> None:
        """Reset an account's schedule: set start_date to today, current_day to 1,
        and clear its action history."""
        today = date.today().isoformat()
        self.db.execute(
            "UPDATE accounts SET start_date = ?, current_day = 1, status = 'idle' WHERE id = ?",
            (today, account_id),
        )
        self.db.execute(
            "DELETE FROM action_history WHERE account_id = ?",
            (account_id,),
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_account(self, account_id: int) -> None:
        """Remove an account from the database."""
        query = "DELETE FROM accounts WHERE id = ?"
        self.db.execute(query, (account_id,))
