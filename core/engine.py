"""
Engine - Orchestrates worker threads for all accounts.
"""

import threading
from queue import Queue

from core.account_manager import AccountManager
from core.target_manager import TargetManager
from core.category_manager import CategoryManager
from core.scheduler import Scheduler
from workers.twitter_worker import TwitterWorker
from database.db import Database
from utils.config import DB_PATH
from utils.logger import get_logger

logger = get_logger(__name__)


class Engine:
    """Central orchestrator that manages TwitterWorker threads.

    Parameters
    ----------
    db : Database, optional
        Shared database instance.  Created automatically if omitted.
    message_queue : Queue, optional
        Thread-safe queue for communicating with the GUI.
    max_concurrent : int
        Maximum number of workers running at the same time (default 3).
    """

    def __init__(
        self,
        db: Database | None = None,
        message_queue: Queue | None = None,
        max_concurrent: int = 3,
    ):
        self.db = db or Database(DB_PATH)
        self.queue: Queue = message_queue or Queue()
        self.max_concurrent = max_concurrent

        self.account_manager = AccountManager(self.db)
        self.target_manager = TargetManager(self.db)
        self.category_manager = CategoryManager(self.db)

        # account_id -> TwitterWorker
        self._workers: dict[int, TwitterWorker] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_schedule_json(self, schedule_id: int):
        """Fetch the schedule JSON for a given schedule id."""
        row = self.db.fetch_one(
            "SELECT schedule_json FROM schedules WHERE id = ?", (schedule_id,)
        )
        if row:
            return row.get("schedule_json", "[]")
        return "[]"

    def _build_worker(self, account: dict) -> TwitterWorker:
        """Construct a TwitterWorker for the given account dict."""
        schedule_json = self._get_schedule_json(account.get("schedule_id", 1))
        targets = self.target_manager.get_targets_for_account(
            account["id"], self.category_manager
        )

        worker = TwitterWorker(
            account=account,
            schedule_json=schedule_json,
            targets=targets,
            message_queue=self.queue,
            db=self.db,
        )
        return worker

    def _active_count(self) -> int:
        """Return the number of currently alive workers."""
        with self._lock:
            return sum(1 for w in self._workers.values() if w.is_alive())

    # ------------------------------------------------------------------
    # Single-account controls
    # ------------------------------------------------------------------

    def start_account(self, account_id: int) -> bool:
        """Start a worker for the given account.

        Returns False if the concurrency limit is reached or the account
        is already running.
        """
        with self._lock:
            # Already running?
            existing = self._workers.get(account_id)
            if existing and existing.is_alive():
                logger.warning(f"Account {account_id} is already running.")
                return False

            if self._active_count_unlocked() >= self.max_concurrent:
                logger.warning(
                    f"Concurrency limit ({self.max_concurrent}) reached. "
                    f"Cannot start account {account_id}."
                )
                return False

            account = self.account_manager.get_account(account_id)
            if account is None:
                logger.error(f"Account {account_id} not found.")
                return False

            worker = self._build_worker(account)
            self._workers[account_id] = worker
            worker.start()

            self.account_manager.update_status(account_id, "running")
            logger.info(f"Started worker for account {account_id}")
            return True

    def stop_account(self, account_id: int) -> None:
        """Signal a running worker to stop."""
        with self._lock:
            worker = self._workers.get(account_id)

        if worker and worker.is_alive():
            worker.stop()
            logger.info(f"Stop signal sent to account {account_id}")
            self.account_manager.update_status(account_id, "idle")
        else:
            # Worker already dead but status may be stuck — reset to idle
            self.account_manager.update_status(account_id, "idle")
            logger.info(f"Worker already dead for account {account_id}, status reset to idle")

    def pause_account(self, account_id: int) -> None:
        """Pause a running worker."""
        with self._lock:
            worker = self._workers.get(account_id)

        if worker and worker.is_alive():
            worker.pause()
            logger.info(f"Paused account {account_id}")
            self.account_manager.update_status(account_id, "paused")
        else:
            logger.warning(f"No active worker for account {account_id}")

    def resume_account(self, account_id: int) -> None:
        """Resume a paused worker."""
        with self._lock:
            worker = self._workers.get(account_id)

        if worker and worker.is_alive():
            worker.resume()
            logger.info(f"Resumed account {account_id}")
            self.account_manager.update_status(account_id, "running")
        else:
            logger.warning(f"No active worker for account {account_id}")

    # ------------------------------------------------------------------
    # Bulk controls
    # ------------------------------------------------------------------

    def start_all(self) -> list[int]:
        """Start workers for every idle account (up to concurrency limit).

        Returns a list of account ids that were successfully started.
        """
        accounts = self.account_manager.get_all_accounts()
        started = []
        for account in accounts:
            if account.get("status") in ("idle", "completed", "error"):
                if self.start_account(account["id"]):
                    started.append(account["id"])
        return started

    def stop_all(self) -> None:
        """Signal every running worker to stop."""
        with self._lock:
            worker_items = list(self._workers.items())

        for account_id, worker in worker_items:
            if worker.is_alive():
                worker.stop()
            # Always reset status — covers both alive and dead workers
            self.account_manager.update_status(account_id, "idle")

        logger.info("Stop signal sent to all workers.")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_worker_status(self, account_id: int) -> str:
        """Return a human-readable status for the worker."""
        with self._lock:
            worker = self._workers.get(account_id)

        if worker is None:
            return "not_started"
        if not worker.is_alive():
            return "finished"
        if worker.is_paused():
            return "paused"
        if worker.is_stopped():
            return "stopping"
        return "running"

    def get_all_statuses(self) -> dict[int, str]:
        """Return ``{account_id: status}`` for every tracked worker."""
        with self._lock:
            ids = list(self._workers.keys())
        return {aid: self.get_worker_status(aid) for aid in ids}

    # ------------------------------------------------------------------
    # Internal (no-lock variants for use inside the lock)
    # ------------------------------------------------------------------

    def _active_count_unlocked(self) -> int:
        """Count alive workers — caller must hold ``self._lock``."""
        return sum(1 for w in self._workers.values() if w.is_alive())
