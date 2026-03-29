"""
AccountCard - Compact card widget showing account summary.
"""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from gui.theme import FG_MUTED, FG_TITLE
from gui.widgets.status_indicator import StatusIndicator


class AccountCard(QFrame):
    """Displays a single account's username, status, day progress, and a mini
    progress bar.

    Parameters
    ----------
    account : dict
        Account dictionary from the database (must contain ``username``,
        ``status``, ``current_day``, ``schedule_id``).
    total_days : int
        Total number of days in the schedule (used for progress bar).
    """

    def __init__(self, parent=None, account: dict | None = None, total_days: int = 14):
        super().__init__(parent)
        if account is None:
            account = {}

        self.setObjectName("card")
        self._account = account
        self._total_days = total_days

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        # --- Row 0: indicator + username + status ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        self._indicator = StatusIndicator(
            self,
            status=account.get("status", "idle"),
            size=10,
        )
        top_layout.addWidget(self._indicator)

        self._lbl_username = QLabel(f"@{account.get('username', '???')}")
        self._lbl_username.setStyleSheet(f"color: {FG_TITLE}; font-weight: bold;")
        top_layout.addWidget(self._lbl_username)

        top_layout.addStretch()

        self._lbl_status = QLabel(self._status_text(account.get("status", "idle")))
        self._lbl_status.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
        top_layout.addWidget(self._lbl_status)

        layout.addLayout(top_layout)

        # --- Row 1: day progress ---
        day = account.get("current_day", 1)
        self._lbl_day = QLabel(f"Dia {day}/{total_days}")
        self._lbl_day.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
        layout.addWidget(self._lbl_day)

        # --- Row 2: progress bar ---
        self._progress = QProgressBar()
        self._progress.setRange(0, total_days)
        self._progress.setValue(day)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        layout.addWidget(self._progress)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def update_account(self, account: dict, total_days: int | None = None) -> None:
        """Refresh the card with updated account data."""
        self._account = account
        if total_days is not None:
            self._total_days = total_days

        status = account.get("status", "idle")
        day = account.get("current_day", 1)

        self._indicator.set_status(status)
        self._lbl_username.setText(f"@{account.get('username', '???')}")
        self._lbl_status.setText(self._status_text(status))
        self._lbl_day.setText(f"Dia {day}/{self._total_days}")
        self._progress.setMaximum(self._total_days)
        self._progress.setValue(day)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _status_text(status: str) -> str:
        mapping = {
            "running": "Rodando",
            "paused": "Pausado",
            "error": "Erro",
            "idle": "Parado",
            "completed": "Concluido",
            "stopping": "Parando",
        }
        return mapping.get(status, status.capitalize())
