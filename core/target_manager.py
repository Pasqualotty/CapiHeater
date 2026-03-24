"""
TargetManager - CRUD operations for target accounts/URLs to interact with.
"""

from database.db import Database
from utils.config import DB_PATH


class TargetManager:
    """Manage target Twitter/X accounts stored in the database."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(DB_PATH)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def add_target(self, username: str, url: str, priority: int = 1) -> int:
        """Insert a new target and return its id.

        Parameters
        ----------
        username : str
            Target Twitter/X handle.
        url : str
            Profile or tweet URL.
        priority : int
            Higher means interacted with first (default 1).

        Returns
        -------
        int
            The newly created target row id.
        """
        query = """
            INSERT INTO targets (username, url, priority, active)
            VALUES (?, ?, ?, 1)
        """
        return self.db.execute(query, (username, url, priority))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_targets(self, active_only: bool = True) -> list[dict]:
        """Return targets ordered by priority descending.

        Parameters
        ----------
        active_only : bool
            If True, only return targets where ``is_active = 1``.
        """
        if active_only:
            query = "SELECT * FROM targets WHERE active = 1 ORDER BY priority DESC, id"
        else:
            query = "SELECT * FROM targets ORDER BY priority DESC, id"
        return self.db.fetch_all(query)

    def get_targets_for_account(self, account_id: int, category_manager) -> list[dict]:
        """Return active targets filtered by the account's categories.

        - Account with no categories: returns ALL active targets.
        - Account with categories: returns targets sharing at least one
          category in common + targets with no categories.
        """
        account_cats = category_manager.get_account_categories(account_id)
        if not account_cats:
            return self.get_targets(active_only=True)

        placeholders = ",".join("?" for _ in account_cats)
        query = f"""
            SELECT t.* FROM targets t
            WHERE t.active = 1
              AND EXISTS (
                  SELECT 1 FROM target_categories tc
                  WHERE tc.target_id = t.id AND tc.category_id IN ({placeholders})
              )
            ORDER BY t.priority DESC, t.id
        """
        return self.db.fetch_all(query, tuple(account_cats))

    def get_target(self, target_id: int) -> dict | None:
        """Fetch a single target by id."""
        query = "SELECT * FROM targets WHERE id = ?"
        return self.db.fetch_one(query, (target_id,))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_target(self, target_id: int, **kwargs) -> None:
        """Update arbitrary columns on a target.

        Example::

            manager.update_target(1, priority=5, url="https://x.com/user")
        """
        if not kwargs:
            return

        columns = ", ".join(f"{col} = ?" for col in kwargs)
        values = list(kwargs.values()) + [target_id]
        query = f"UPDATE targets SET {columns} WHERE id = ?"
        self.db.execute(query, tuple(values))

    def toggle_active(self, target_id: int) -> None:
        """Flip the ``is_active`` flag on a target."""
        query = "UPDATE targets SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END WHERE id = ?"
        self.db.execute(query, (target_id,))

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_target(self, target_id: int) -> None:
        """Remove a target from the database."""
        query = "DELETE FROM targets WHERE id = ?"
        self.db.execute(query, (target_id,))
