"""
CapiHeater – PySide6 theme: "Obsidian Pulse"
Importa identidade visual do theme.py raiz e expõe constantes de compatibilidade.
"""

import os
import sys

# Import the master theme from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import CapiHeaterTheme, Colors

_C = Colors()

# ======================================================================
# QSS — gerado pelo CapiHeaterTheme
# ======================================================================
QSS = CapiHeaterTheme.get_stylesheet()

# ======================================================================
# Backward-compatible color constants (used across GUI modules)
# ======================================================================
BG_DARK = _C.BG_DARKEST
BG_SECONDARY = _C.BG_DARK
BG_ACCENT = _C.BG_ELEVATED
BG_INPUT = _C.BG_SURFACE

FG_TEXT = _C.TEXT_PRIMARY
FG_MUTED = _C.TEXT_SECONDARY
FG_TITLE = _C.TEXT_PRIMARY

ACCENT = _C.ACCENT
ACCENT_HIGHLIGHT = _C.ACCENT_HOVER

COLOR_SUCCESS = _C.SUCCESS
COLOR_WARNING = _C.WARNING
COLOR_ERROR = _C.DANGER
COLOR_INFO = _C.INFO
COLOR_ORANGE = _C.WARNING

# Status colors (used by StatusIndicator and row coloring)
STATUS_COLORS = {
    "running": _C.STATUS_RUNNING,
    "paused": _C.STATUS_PAUSED,
    "error": _C.STATUS_ERROR,
    "idle": _C.STATUS_STOPPED,
    "completed": _C.STATUS_COMPLETED,
    "stopping": _C.WARNING,
}

# ======================================================================
# Icon path helper
# ======================================================================
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ICON_PATH = os.path.join(_ASSETS_DIR, "icon.png")
ICON_ICO_PATH = os.path.join(_ASSETS_DIR, "icon.ico")
