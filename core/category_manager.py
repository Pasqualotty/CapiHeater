"""
CategoryManager - CRUD operations for categories and their associations.
"""

from database.db import Database
from utils.config import DB_PATH


class CategoryManager:
    """Manage categories and their many-to-many relationships with accounts and targets."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(DB_PATH)

    # ------------------------------------------------------------------
    # Category CRUD
    # ------------------------------------------------------------------

    def add_category(self, name: str) -> int:
        """Insert a new category and return its id."""
        query = "INSERT INTO categories (name) VALUES (?)"
        return self.db.execute(query, (name,))

    def get_all_categories(self) -> list[dict]:
        """Return all categories ordered by id."""
        return self.db.fetch_all("SELECT * FROM categories ORDER BY id")

    def get_category_names(self) -> dict[int, str]:
        """Return {id: name} mapping for all categories."""
        rows = self.get_all_categories()
        return {r["id"]: r["name"] for r in rows}

    def delete_category(self, category_id: int) -> None:
        """Delete a category. ON DELETE CASCADE cleans up associations."""
        self.db.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    # ------------------------------------------------------------------
    # Account <-> Category associations
    # ------------------------------------------------------------------

    def set_account_categories(self, account_id: int, category_ids: list[int]) -> None:
        """Replace all category associations for an account."""
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM account_categories WHERE account_id = ?", (account_id,))
            for cat_id in category_ids:
                conn.execute(
                    "INSERT INTO account_categories (account_id, category_id) VALUES (?, ?)",
                    (account_id, cat_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_account_categories(self, account_id: int) -> list[int]:
        """Return list of category IDs for an account."""
        rows = self.db.fetch_all(
            "SELECT category_id FROM account_categories WHERE account_id = ?",
            (account_id,),
        )
        return [r["category_id"] for r in rows]

    def get_account_category_names(self, account_id: int) -> list[str]:
        """Return list of category names for an account."""
        rows = self.db.fetch_all(
            """SELECT c.name FROM categories c
               JOIN account_categories ac ON c.id = ac.category_id
               WHERE ac.account_id = ?
               ORDER BY c.name""",
            (account_id,),
        )
        return [r["name"] for r in rows]

    # ------------------------------------------------------------------
    # Target <-> Category associations
    # ------------------------------------------------------------------

    def set_target_categories(self, target_id: int, category_ids: list[int]) -> None:
        """Replace all category associations for a target."""
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM target_categories WHERE target_id = ?", (target_id,))
            for cat_id in category_ids:
                conn.execute(
                    "INSERT INTO target_categories (target_id, category_id) VALUES (?, ?)",
                    (target_id, cat_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_target_categories(self, target_id: int) -> list[int]:
        """Return list of category IDs for a target."""
        rows = self.db.fetch_all(
            "SELECT category_id FROM target_categories WHERE target_id = ?",
            (target_id,),
        )
        return [r["category_id"] for r in rows]

    def get_target_category_names(self, target_id: int) -> list[str]:
        """Return list of category names for a target."""
        rows = self.db.fetch_all(
            """SELECT c.name FROM categories c
               JOIN target_categories tc ON c.id = tc.category_id
               WHERE tc.target_id = ?
               ORDER BY c.name""",
            (target_id,),
        )
        return [r["name"] for r in rows]
