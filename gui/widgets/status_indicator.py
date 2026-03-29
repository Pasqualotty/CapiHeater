"""
StatusIndicator - Small colored circle widget indicating account status.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gui.theme import STATUS_COLORS

# Extra statuses not in theme
_EXTRA = {
    "not_started": "#757575",
    "finished": "#2979ff",
}
_ALL_COLORS = {**STATUS_COLORS, **_EXTRA}


class StatusIndicator(QWidget):
    """A small colored circle that represents an account status.

    Parameters
    ----------
    status : str
        Initial status (``running``, ``paused``, ``error``, ``idle``, etc.).
    size : int
        Diameter of the circle in pixels (default 12).
    """

    def __init__(self, parent=None, status: str = "idle", size: int = 12):
        super().__init__(parent)
        self._size = size
        self._status = status
        self._color = QColor(_ALL_COLORS.get(status, "#757575"))
        self.setFixedSize(size, size)

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        """Update the indicator color based on the new status."""
        self._status = status
        self._color = QColor(_ALL_COLORS.get(status, "#757575"))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(self._color)
        painter.drawEllipse(1, 1, self._size - 2, self._size - 2)
        painter.end()
