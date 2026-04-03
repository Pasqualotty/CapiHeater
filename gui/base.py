"""
Base classes for PySide6 tabs in CapiHeater.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem, QWidget


class SortableItem(QTableWidgetItem):
    """QTableWidgetItem that compares via a stored sort key (UserRole + 1).

    Usage
    -----
    Pass a *sort_key* of the correct Python type so ordering is meaningful:

    * ``int`` or ``float`` — numeric columns (Dia, Prioridade, Likes, …)
    * ``datetime``         — date/time columns (Data Inicio, Data/Hora, …)
    * ``str``              — text columns (sort is case-insensitive)

    The *display* string (what the user sees) is kept separate from the
    sort key, so you can show "Dia 3" while sorting by the integer ``3``.

    Parameters
    ----------
    text : str
        Text shown in the cell.
    sort_key : object
        Value used for comparisons.  Stored in ``Qt.UserRole + 1`` so it does
        not overwrite ``Qt.UserRole``, which tabs use for entity IDs.
    """

    _SORT_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, text: str, sort_key=None):
        super().__init__(text)
        # Fall back to lower-cased text for plain text columns.
        key = text.lower() if sort_key is None else sort_key
        self.setData(self._SORT_ROLE, key)

    def __lt__(self, other: "QTableWidgetItem") -> bool:  # type: ignore[override]
        my_key = self.data(self._SORT_ROLE)
        other_key = other.data(self._SORT_ROLE) if isinstance(other, SortableItem) else None

        if my_key is None and other_key is None:
            return self.text().lower() < other.text().lower()
        if my_key is None:
            return True
        if other_key is None:
            return False

        # Mixed types: fall back to string comparison to avoid TypeError.
        try:
            return my_key < other_key  # type: ignore[operator]
        except TypeError:
            return str(my_key) < str(other_key)


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
