"""
SfsManager - CRUD operations for SFS (Shoutout For Shoutout) sessions.
"""

from database.db import Database
from utils.config import DB_PATH


class SfsManager:
    """Manage SFS sessions and their associated targets."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(DB_PATH)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_session(
        self,
        name: str,
        account_id: int,
        actions_dict: dict | None = None,
        pace: str = "normal",
    ) -> int:
        """Insert a new SFS session and return its id.

        Parameters
        ----------
        name : str
            Display name for the session.
        account_id : int
            FK to the accounts table.
        actions_dict : dict, optional
            Keys map to action columns: ``action_like``, ``action_follow``,
            ``action_retweet``, ``action_comment_like``, ``like_latest_post``,
            ``rt_latest_post``.  Missing keys use the table defaults.
        pace : str
            Execution pace: ``'slow'``, ``'normal'``, or ``'fast'``.

        Returns
        -------
        int
            The newly created session row id.
        """
        actions = actions_dict or {}
        query = """
            INSERT INTO sfs_sessions (
                name, account_id,
                action_like, action_follow, action_retweet, action_comment_like,
                like_latest_post, rt_latest_post,
                pace, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'idle')
        """
        return self.db.execute(
            query,
            (
                name,
                account_id,
                actions.get("action_like", 1),
                actions.get("action_follow", 1),
                actions.get("action_retweet", 1),
                actions.get("action_comment_like", 0),
                actions.get("like_latest_post", 0),
                actions.get("rt_latest_post", 0),
                pace,
            ),
        )

    def add_targets_to_session(self, session_id: int, target_ids: list[int]) -> None:
        """Insert session-target relationships, ignoring duplicates.

        Parameters
        ----------
        session_id : int
            FK to sfs_sessions.
        target_ids : list[int]
            List of target row ids to associate with the session.
        """
        if not target_ids:
            return
        conn = self.db.get_connection()
        try:
            conn.executemany(
                "INSERT OR IGNORE INTO sfs_session_targets (session_id, target_id) VALUES (?, ?)",
                [(session_id, tid) for tid in target_ids],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_session(self, session_id: int) -> dict | None:
        """Fetch a single session by id."""
        return self.db.fetch_one(
            "SELECT * FROM sfs_sessions WHERE id = ?",
            (session_id,),
        )

    def get_all_sessions(self) -> list[dict]:
        """Return all sessions with account username, target count and progress.

        Each row includes:
        - all sfs_sessions columns
        - ``account_username`` — username from the accounts table
        - ``total_targets`` — number of targets linked to the session
        - ``completed_targets`` — number of targets marked as completed
        """
        query = """
            SELECT
                s.*,
                a.username AS account_username,
                COUNT(st.target_id) AS total_targets,
                COALESCE(SUM(st.completed), 0) AS completed_targets
            FROM sfs_sessions s
            JOIN accounts a ON a.id = s.account_id
            LEFT JOIN sfs_session_targets st ON st.session_id = s.id
            GROUP BY s.id
            ORDER BY s.id
        """
        return self.db.fetch_all(query)

    def get_session_targets(self, session_id: int) -> list[dict]:
        """Return targets linked to a session with completion info.

        Each row includes all columns from ``targets`` plus:
        - ``completed`` — 0 or 1
        - ``completed_at`` — ISO datetime string or NULL
        """
        query = """
            SELECT
                t.*,
                st.completed,
                st.completed_at
            FROM sfs_session_targets st
            JOIN targets t ON t.id = st.target_id
            WHERE st.session_id = ?
            ORDER BY t.username
        """
        return self.db.fetch_all(query, (session_id,))

    def get_session_progress(self, session_id: int) -> tuple[int, int]:
        """Return (completed, total) target counts for a session."""
        row = self.db.fetch_one(
            """
            SELECT
                SUM(completed) AS completed,
                COUNT(*) AS total
            FROM sfs_session_targets
            WHERE session_id = ?
            """,
            (session_id,),
        )
        if row is None:
            return (0, 0)
        return (int(row["completed"] or 0), int(row["total"] or 0))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    ALLOWED_COLUMNS: frozenset[str] = frozenset({
        "name", "account_id", "action_like", "action_follow",
        "action_retweet", "action_comment_like", "like_latest_post", "rt_latest_post",
        "pace", "status", "updated_at",
    })

    def update_session(self, session_id: int, **kwargs) -> None:
        """Update arbitrary columns on a session.

        ``updated_at`` is always refreshed automatically.
        Only columns present in ``ALLOWED_COLUMNS`` are accepted.

        Example::

            manager.update_session(1, pace='fast', action_follow=0)
        """
        # Drop any column not in the whitelist to prevent SQL injection
        kwargs = {k: v for k, v in kwargs.items() if k in self.ALLOWED_COLUMNS}
        if not kwargs:
            return
        kwargs["updated_at"] = "datetime('now', 'localtime')"
        # Separate the updated_at raw expression from regular values
        set_parts = []
        values: list = []
        for col, val in kwargs.items():
            if col == "updated_at":
                set_parts.append(f"{col} = {val}")
            else:
                set_parts.append(f"{col} = ?")
                values.append(val)
        values.append(session_id)
        query = f"UPDATE sfs_sessions SET {', '.join(set_parts)} WHERE id = ?"
        self.db.execute(query, tuple(values))

    def update_status(self, session_id: int, status: str) -> None:
        """Update the session status and refresh updated_at.

        Common values: ``'idle'``, ``'running'``, ``'paused'``,
        ``'completed'``, ``'error'``.
        """
        self.db.execute(
            "UPDATE sfs_sessions SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (status, session_id),
        )

    def mark_target_completed(self, session_id: int, target_id: int) -> None:
        """Mark a session-target pair as completed with the current timestamp."""
        self.db.execute(
            """
            UPDATE sfs_session_targets
            SET completed = 1, completed_at = datetime('now', 'localtime')
            WHERE session_id = ? AND target_id = ?
            """,
            (session_id, target_id),
        )

    def remove_targets_from_session(self, session_id: int, target_ids: list[int]) -> None:
        """Remove target associations from a session.

        Parameters
        ----------
        session_id : int
            The session to modify.
        target_ids : list[int]
            Target ids to disassociate.
        """
        if not target_ids:
            return
        conn = self.db.get_connection()
        try:
            conn.executemany(
                "DELETE FROM sfs_session_targets WHERE session_id = ? AND target_id = ?",
                [(session_id, tid) for tid in target_ids],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_session(self, session_id: int) -> None:
        """Remove a session; CASCADE deletes its sfs_session_targets rows."""
        self.db.execute(
            "DELETE FROM sfs_sessions WHERE id = ?",
            (session_id,),
        )
