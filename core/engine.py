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
from workers.sfs_worker import SfsWorker
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
        # session_id -> SfsWorker
        self._sfs_workers: dict[int, "SfsWorker"] = {}
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
            # Purge dead workers to free slots and avoid stale refs
            dead = [aid for aid, w in self._workers.items() if not w.is_alive()]
            for aid in dead:
                del self._workers[aid]

            # If a worker is still alive (stuck), force-stop it
            existing = self._workers.get(account_id)
            if existing and existing.is_alive():
                logger.warning(
                    f"Account {account_id} has a stuck worker — force-stopping."
                )
                existing._superseded = True  # prevent safety-net from resetting status
                existing.stop()
                if hasattr(existing, "force_stop"):
                    existing.force_stop()
                # Release lock while waiting so the worker's finally block
                # can run without deadlocking.
                self._lock.release()
                try:
                    existing.join(timeout=5)
                finally:
                    self._lock.acquire()
                if existing.is_alive():
                    logger.error(
                        f"Account {account_id} worker did not die after "
                        f"force-stop — abandoning daemon thread."
                    )
                del self._workers[account_id]

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

            try:
                worker = self._build_worker(account)
            except Exception as exc:
                logger.error(f"Failed to build worker for account {account_id}: {exc}")
                self.account_manager.update_status(account_id, "error")
                return False

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
    # SFS session controls
    # ------------------------------------------------------------------

    def start_sfs_session(self, session_id: int, sfs_manager) -> bool:
        """Start a worker for the given SFS session.

        Parameters
        ----------
        session_id : int
            ID of the SFS session to start.
        sfs_manager : SfsManager
            The shared SFS manager instance.

        Returns
        -------
        bool
            False if the session is not found, already running, or the account
            already has an active heating/SFS worker.
        """
        with self._lock:
            # Purge dead SFS workers
            dead = [sid for sid, w in self._sfs_workers.items() if not w.is_alive()]
            for sid in dead:
                del self._sfs_workers[sid]

            # Refuse if session already has a live worker
            existing = self._sfs_workers.get(session_id)
            if existing and existing.is_alive():
                logger.warning(
                    f"SFS session {session_id} already has a live worker."
                )
                return False

            session = sfs_manager.get_session(session_id)
            if session is None:
                logger.error(f"SFS session {session_id} not found.")
                return False

            account_id = session["account_id"]

            # Refuse if account already runs a heating worker
            heating_worker = self._workers.get(account_id)
            if heating_worker and heating_worker.is_alive():
                logger.warning(
                    f"Account {account_id} already has an active heating worker. "
                    f"Cannot start SFS session {session_id}."
                )
                return False

            # Refuse if account already runs another SFS session
            for sid, w in self._sfs_workers.items():
                if w.is_alive() and w.account["id"] == account_id:
                    logger.warning(
                        f"Account {account_id} already has an active SFS worker "
                        f"(session {sid}). Cannot start session {session_id}."
                    )
                    return False

            account = self.account_manager.get_account(account_id)
            if account is None:
                logger.error(
                    f"Account {account_id} not found for SFS session {session_id}."
                )
                return False

            worker = SfsWorker(
                account=account,
                session_data=session,
                sfs_manager=sfs_manager,
                db=self.db,
                message_queue=self.queue,
            )
            self._sfs_workers[session_id] = worker
            worker.start()

            sfs_manager.update_status(session_id, "running")
            logger.info(
                f"Started SFS worker for session {session_id} "
                f"(account {account['username']})"
            )
            return True

    def stop_sfs_session(self, session_id: int, sfs_manager) -> bool:
        """Signal an SFS worker to stop.

        Returns False if no live worker exists for this session.
        """
        with self._lock:
            worker = self._sfs_workers.get(session_id)

        if worker and worker.is_alive():
            worker.stop()
            sfs_manager.update_status(session_id, "idle")
            logger.info(f"Stop signal sent to SFS session {session_id}")
            return True

        # Worker already dead — reset status anyway
        sfs_manager.update_status(session_id, "idle")
        logger.info(
            f"SFS session {session_id} worker already dead, status reset to idle"
        )
        return False

    def pause_sfs_session(self, session_id: int, sfs_manager) -> bool:
        """Pause a running SFS worker.

        Returns False if no live worker exists.
        """
        with self._lock:
            worker = self._sfs_workers.get(session_id)

        if worker and worker.is_alive():
            worker.pause()
            sfs_manager.update_status(session_id, "paused")
            logger.info(f"Paused SFS session {session_id}")
            return True

        logger.warning(f"No active SFS worker for session {session_id}")
        return False

    def resume_sfs_session(self, session_id: int, sfs_manager) -> bool:
        """Resume a paused SFS worker.

        Returns False if no live worker exists.
        """
        with self._lock:
            worker = self._sfs_workers.get(session_id)

        if worker and worker.is_alive():
            worker.resume()
            sfs_manager.update_status(session_id, "running")
            logger.info(f"Resumed SFS session {session_id}")
            return True

        logger.warning(f"No active SFS worker for session {session_id}")
        return False

    def get_sfs_worker_status(self, session_id: int) -> str:
        """Return a human-readable status for an SFS worker."""
        with self._lock:
            worker = self._sfs_workers.get(session_id)

        if worker is None:
            return "not_started"
        if not worker.is_alive():
            return "finished"
        if worker.is_paused():
            return "paused"
        if worker.is_stopped():
            return "stopping"
        return "running"

    # ------------------------------------------------------------------
    # Internal (no-lock variants for use inside the lock)
    # ------------------------------------------------------------------

    def _active_count_unlocked(self) -> int:
        """Count alive workers — caller must hold ``self._lock``."""
        return sum(1 for w in self._workers.values() if w.is_alive())
