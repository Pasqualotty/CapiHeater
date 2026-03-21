"""
AccountCard - Compact card widget showing account summary.
"""

import tkinter as tk
from tkinter import ttk

from gui.widgets.status_indicator import StatusIndicator


class AccountCard(ttk.Frame):
    """Displays a single account's username, status, day progress, and a mini
    progress bar.

    Parameters
    ----------
    parent : tk.Widget
        Parent widget.
    account : dict
        Account dictionary from the database (must contain ``username``,
        ``status``, ``current_day``, ``schedule_id``).
    total_days : int
        Total number of days in the schedule (used for progress bar).
    """

    def __init__(self, parent, account: dict, total_days: int = 14, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self._account = account
        self._total_days = total_days

        # --- Row 0: indicator + username ---
        top_frame = ttk.Frame(self, style="Card.TFrame")
        top_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

        self._indicator = StatusIndicator(
            top_frame,
            status=account.get("status", "idle"),
            size=10,
        )
        self._indicator.pack(side=tk.LEFT, padx=(0, 6))

        self._lbl_username = ttk.Label(
            top_frame,
            text=f"@{account.get('username', '???')}",
            style="CardTitle.TLabel",
        )
        self._lbl_username.pack(side=tk.LEFT)

        self._lbl_status = ttk.Label(
            top_frame,
            text=self._status_text(account.get("status", "idle")),
            style="CardStatus.TLabel",
        )
        self._lbl_status.pack(side=tk.RIGHT)

        # --- Row 1: day progress ---
        day = account.get("current_day", 1)
        progress_frame = ttk.Frame(self, style="Card.TFrame")
        progress_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

        self._lbl_day = ttk.Label(
            progress_frame,
            text=f"Dia {day}/{total_days}",
            style="CardDetail.TLabel",
        )
        self._lbl_day.pack(side=tk.LEFT)

        # --- Row 2: progress bar ---
        bar_frame = ttk.Frame(self, style="Card.TFrame")
        bar_frame.pack(fill=tk.X, padx=6, pady=(0, 6))

        self._progress = ttk.Progressbar(
            bar_frame,
            orient=tk.HORIZONTAL,
            length=160,
            mode="determinate",
            maximum=total_days,
            value=day,
            style="Card.Horizontal.TProgressbar",
        )
        self._progress.pack(fill=tk.X)

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
        self._lbl_username.config(text=f"@{account.get('username', '???')}")
        self._lbl_status.config(text=self._status_text(status))
        self._lbl_day.config(text=f"Dia {day}/{self._total_days}")
        self._progress.config(value=day, maximum=self._total_days)

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
