"""
CapiHeater – PySide6 dark theme constants and QSS stylesheet.
"""

# ======================================================================
# Color palette
# ======================================================================
BG_DARK = "#1a1a2e"
BG_SECONDARY = "#16213e"
BG_ACCENT = "#0f3460"
BG_INPUT = "#0d1b2a"

FG_TEXT = "#e0e0e0"
FG_MUTED = "#9e9e9e"
FG_TITLE = "#ffffff"

ACCENT = "#0f3460"
ACCENT_HIGHLIGHT = "#1a73e8"

COLOR_SUCCESS = "#00e676"
COLOR_WARNING = "#ffea00"
COLOR_ERROR = "#ff1744"
COLOR_INFO = "#2979ff"
COLOR_ORANGE = "#ff9100"

# Status colors (used by StatusIndicator and row coloring)
STATUS_COLORS = {
    "running": COLOR_SUCCESS,
    "paused": COLOR_WARNING,
    "error": COLOR_ERROR,
    "idle": "#757575",
    "completed": COLOR_INFO,
    "stopping": COLOR_ORANGE,
}

# ======================================================================
# Global QSS stylesheet
# ======================================================================
QSS = f"""
/* ------------------------------------------------------------------ */
/* Base                                                                */
/* ------------------------------------------------------------------ */
* {{
    font-family: "Segoe UI";
    font-size: 10pt;
    color: {FG_TEXT};
}}

QMainWindow, QDialog {{
    background-color: {BG_DARK};
}}

QWidget {{
    background-color: transparent;
}}

/* ------------------------------------------------------------------ */
/* Tab widget                                                          */
/* ------------------------------------------------------------------ */
QTabWidget::pane {{
    border: none;
    background-color: {BG_DARK};
}}

QTabBar::tab {{
    background-color: {BG_SECONDARY};
    color: {FG_MUTED};
    padding: 8px 16px;
    border: none;
    min-width: 80px;
}}

QTabBar::tab:selected {{
    background-color: {BG_ACCENT};
    color: {FG_TITLE};
}}

QTabBar::tab:hover:!selected {{
    background-color: {BG_ACCENT};
    color: {FG_TEXT};
}}

/* ------------------------------------------------------------------ */
/* Frames / Cards                                                      */
/* ------------------------------------------------------------------ */
QFrame[objectName="card"] {{
    background-color: {BG_SECONDARY};
    border-radius: 4px;
    padding: 8px;
}}

QGroupBox {{
    color: {FG_TITLE};
    font-weight: bold;
    border: 1px solid {BG_ACCENT};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */
QPushButton {{
    background-color: {BG_ACCENT};
    color: {FG_TEXT};
    padding: 6px 14px;
    border: none;
    border-radius: 3px;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {ACCENT_HIGHLIGHT};
    color: {FG_TITLE};
}}

QPushButton:pressed {{
    background-color: #0d47a1;
}}

QPushButton:disabled {{
    background-color: {BG_SECONDARY};
    color: {FG_MUTED};
}}

QPushButton[objectName="accent"] {{
    background-color: {ACCENT_HIGHLIGHT};
    color: {FG_TITLE};
}}

QPushButton[objectName="accent"]:hover {{
    background-color: #1565c0;
}}

QPushButton[objectName="danger"] {{
    background-color: {COLOR_ERROR};
    color: {FG_TITLE};
}}

QPushButton[objectName="danger"]:hover {{
    background-color: #d50000;
}}

/* ------------------------------------------------------------------ */
/* Input fields                                                        */
/* ------------------------------------------------------------------ */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BG_ACCENT};
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 22px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT_HIGHLIGHT};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {FG_MUTED};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    selection-background-color: {ACCENT_HIGHLIGHT};
    selection-color: {FG_TITLE};
    border: 1px solid {BG_ACCENT};
}}

QPlainTextEdit, QTextBrowser, QTextEdit {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BG_ACCENT};
    border-radius: 3px;
    padding: 4px;
}}

/* ------------------------------------------------------------------ */
/* Tables (QTableWidget / QTreeView)                                   */
/* ------------------------------------------------------------------ */
QTableWidget, QTreeView, QTreeWidget {{
    background-color: {BG_SECONDARY};
    alternate-background-color: {BG_INPUT};
    color: {FG_TEXT};
    gridline-color: {BG_ACCENT};
    selection-background-color: {ACCENT_HIGHLIGHT};
    selection-color: {FG_TITLE};
    border: none;
    outline: none;
}}

QHeaderView::section {{
    background-color: {BG_ACCENT};
    color: {FG_TITLE};
    font-weight: bold;
    padding: 4px 8px;
    border: none;
    border-right: 1px solid {BG_DARK};
}}

QTableWidget::item:selected, QTreeView::item:selected {{
    background-color: {ACCENT_HIGHLIGHT};
    color: {FG_TITLE};
}}

/* ------------------------------------------------------------------ */
/* Scrollbar                                                           */
/* ------------------------------------------------------------------ */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BG_ACCENT};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_HIGHLIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {BG_DARK};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {BG_ACCENT};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ACCENT_HIGHLIGHT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ------------------------------------------------------------------ */
/* Progress bar                                                        */
/* ------------------------------------------------------------------ */
QProgressBar {{
    background-color: {BG_DARK};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT_HIGHLIGHT};
    border-radius: 3px;
}}

/* ------------------------------------------------------------------ */
/* Checkbox / RadioButton                                              */
/* ------------------------------------------------------------------ */
QCheckBox, QRadioButton {{
    color: {FG_TEXT};
    spacing: 6px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BG_ACCENT};
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_HIGHLIGHT};
    border-color: {ACCENT_HIGHLIGHT};
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QRadioButton::indicator:checked {{
    background-color: {ACCENT_HIGHLIGHT};
    border-color: {ACCENT_HIGHLIGHT};
}}

/* ------------------------------------------------------------------ */
/* List widget                                                         */
/* ------------------------------------------------------------------ */
QListWidget {{
    background-color: {BG_INPUT};
    color: {FG_TEXT};
    border: 1px solid {BG_ACCENT};
    border-radius: 3px;
    outline: none;
}}

QListWidget::item:selected {{
    background-color: {ACCENT_HIGHLIGHT};
    color: {FG_TITLE};
}}

/* ------------------------------------------------------------------ */
/* Menu (context menus)                                                */
/* ------------------------------------------------------------------ */
QMenu {{
    background-color: {BG_SECONDARY};
    color: {FG_TEXT};
    border: 1px solid {BG_ACCENT};
    padding: 4px 0;
}}

QMenu::item {{
    padding: 6px 24px;
}}

QMenu::item:selected {{
    background-color: {ACCENT_HIGHLIGHT};
    color: {FG_TITLE};
}}

QMenu::separator {{
    height: 1px;
    background-color: {BG_ACCENT};
    margin: 4px 8px;
}}

/* ------------------------------------------------------------------ */
/* Status bar                                                          */
/* ------------------------------------------------------------------ */
QStatusBar {{
    background-color: {BG_SECONDARY};
    color: {FG_MUTED};
    font-size: 9pt;
    border-top: 1px solid {BG_ACCENT};
}}

/* ------------------------------------------------------------------ */
/* Splitter                                                            */
/* ------------------------------------------------------------------ */
QSplitter::handle {{
    background-color: {BG_ACCENT};
    width: 2px;
}}

/* ------------------------------------------------------------------ */
/* Tooltip                                                             */
/* ------------------------------------------------------------------ */
QToolTip {{
    background-color: {BG_SECONDARY};
    color: {FG_TEXT};
    border: 1px solid {BG_ACCENT};
    padding: 4px;
}}
"""
