"""
StatusIndicator - Small colored circle widget indicating account status.
"""

import tkinter as tk


# Status -> color mapping
STATUS_COLORS = {
    "running": "#00e676",
    "paused": "#ffea00",
    "error": "#ff1744",
    "idle": "#757575",
    "completed": "#2979ff",
    "stopping": "#ff9100",
    "not_started": "#757575",
    "finished": "#2979ff",
}


class StatusIndicator(tk.Canvas):
    """A small colored circle that represents an account status.

    Parameters
    ----------
    parent : tk.Widget
        Parent widget.
    status : str
        Initial status (``running``, ``paused``, ``error``, ``idle``, etc.).
    size : int
        Diameter of the circle in pixels (default 12).
    """

    def __init__(self, parent, status: str = "idle", size: int = 12, **kwargs):
        kwargs.setdefault("width", size)
        kwargs.setdefault("height", size)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bg", "#16213e")
        super().__init__(parent, **kwargs)

        self._size = size
        self._oval = self.create_oval(
            1, 1, size - 1, size - 1,
            fill=STATUS_COLORS.get(status, "#757575"),
            outline="",
        )
        self._status = status

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        """Update the indicator color based on the new status."""
        self._status = status
        color = STATUS_COLORS.get(status, "#757575")
        self.itemconfig(self._oval, fill=color)
