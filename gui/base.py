"""
Base classes for PySide6 tabs in CapiHeater.
"""

from PySide6.QtWidgets import QWidget


class BaseTab(QWidget):
    """Base class that all tab widgets inherit from.

    Provides a standard interface that ``CapiHeaterApp`` relies on when
    dispatching engine messages and tab-switch events.
    """

    def __init__(self, app, parent: QWidget | None = None):
        super().__init__(parent)
        self.app = app

    # -- Interface methods (override in subclasses as needed) ----------

    def refresh(self):
        """Reload data from the database and update the display."""

    def on_status_update(self, msg: dict):
        """Handle a status message from the engine."""

    def on_new_log(self, msg: dict):
        """Handle a new log entry from the engine."""
