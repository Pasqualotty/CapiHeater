"""
╔══════════════════════════════════════════════════════════════╗
║  CapiHeater Theme — "Obsidian Pulse"                        ║
║  Identidade visual para PySide6 (Qt for Python)             ║
║                                                              ║
║  Paleta: Dark charcoal + Teal accent + Violet secondary     ║
║  Uso: from theme import CapiHeaterTheme                     ║
║       app.setStyleSheet(CapiHeaterTheme.get_stylesheet())   ║
╚══════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:
    """Paleta de cores — Obsidian Pulse"""

    # ── Backgrounds ──────────────────────────────────────────
    BG_DARKEST   = "#080b10"   # Window background / fundo principal
    BG_DARK      = "#0e1219"   # Painéis laterais / sidebar
    BG_BASE      = "#141a24"   # Cards e containers
    BG_ELEVATED  = "#1b2332"   # Elementos elevados (cards hover, dropdowns)
    BG_SURFACE   = "#222d3f"   # Inputs, linhas alternadas de tabela

    # ── Borders ──────────────────────────────────────────────
    BORDER_SUBTLE  = "#1e2a3a"  # Bordas quase invisíveis
    BORDER_DEFAULT = "#2a3a50"  # Bordas padrão
    BORDER_STRONG  = "#3a4f6a"  # Bordas com destaque

    # ── Text ─────────────────────────────────────────────────
    TEXT_PRIMARY   = "#e8edf5"  # Texto principal
    TEXT_SECONDARY = "#8899b0"  # Texto secundário / labels
    TEXT_MUTED     = "#556680"  # Texto desabilitado / placeholders
    TEXT_INVERSE   = "#080b10"  # Texto em botões coloridos

    # ── Accent — Teal Pulse (identidade principal) ───────────
    ACCENT         = "#00e5a0"  # Cor principal da marca
    ACCENT_HOVER   = "#00ffb3"  # Hover
    ACCENT_PRESSED = "#00c98c"  # Pressed / active
    ACCENT_SUBTLE  = "#0a2e25"  # Background sutil com accent
    ACCENT_GLOW    = "#00e5a033" # Glow / sombra (com alpha)

    # ── Secondary — Violet ───────────────────────────────────
    SECONDARY         = "#8b7cf6"
    SECONDARY_HOVER   = "#a094f8"
    SECONDARY_PRESSED = "#7568e0"
    SECONDARY_SUBTLE  = "#1a1530"

    # ── Semantic ─────────────────────────────────────────────
    SUCCESS        = "#00e5a0"  # Usa o accent
    SUCCESS_SUBTLE = "#0a2e25"

    WARNING        = "#ffb84d"
    WARNING_SUBTLE = "#2e2210"

    DANGER         = "#ff4d6a"
    DANGER_HOVER   = "#ff6680"
    DANGER_PRESSED = "#e63c57"
    DANGER_SUBTLE  = "#2e1018"

    INFO           = "#4da6ff"
    INFO_SUBTLE    = "#102030"

    # ── Status (para tabelas) ────────────────────────────────
    STATUS_RUNNING   = "#00e5a0"
    STATUS_PAUSED    = "#ffb84d"
    STATUS_STOPPED   = "#8899b0"
    STATUS_ERROR     = "#ff4d6a"
    STATUS_COMPLETED = "#8b7cf6"

    # ── Scrollbar ────────────────────────────────────────────
    SCROLLBAR_BG     = "#0e1219"
    SCROLLBAR_HANDLE = "#2a3a50"
    SCROLLBAR_HOVER  = "#3a4f6a"


class CapiHeaterTheme:
    """Gerador de tema completo para o CapiHeater."""

    C = Colors()

    @classmethod
    def get_stylesheet(cls) -> str:
        """Retorna o QSS completo pronto para app.setStyleSheet()"""
        c = cls.C
        return f"""
        /* ═══════════════════════════════════════════════════════
           CAPIHEATER THEME — "OBSIDIAN PULSE"
           Gerado por CapiHeaterTheme
           ═══════════════════════════════════════════════════════ */

        /* ── RESET & BASE ──────────────────────────────────── */
        * {{
            font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
            font-size: 13px;
            outline: none;
        }}

        QMainWindow {{
            background-color: {c.BG_DARKEST};
        }}

        QWidget {{
            background-color: {c.BG_DARKEST};
            color: {c.TEXT_PRIMARY};
        }}

        QWidget#centralWidget {{
            background-color: {c.BG_DARKEST};
        }}


        /* ── MENU BAR / TAB BAR (Navegação principal) ──────── */
        QTabWidget::pane {{
            border: none;
            background-color: {c.BG_DARKEST};
        }}

        QTabBar {{
            background-color: {c.BG_DARK};
            border: none;
            qproperty-drawBase: 0;
        }}

        QTabBar::tab {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            padding: 10px 20px;
            margin: 0px;
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: 500;
            min-width: 80px;
        }}

        QTabBar::tab:hover {{
            color: {c.TEXT_PRIMARY};
            background-color: {c.BG_ELEVATED};
            border-bottom: 2px solid {c.BORDER_STRONG};
        }}

        QTabBar::tab:selected {{
            color: {c.ACCENT};
            background-color: {c.BG_BASE};
            border-bottom: 2px solid {c.ACCENT};
            font-weight: 600;
        }}

        /* ── MENU BAR (se usar QMenuBar) ───────────────────── */
        QMenuBar {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_SECONDARY};
            border-bottom: 1px solid {c.BORDER_SUBTLE};
            padding: 2px 0px;
            spacing: 0px;
        }}

        QMenuBar::item {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            padding: 8px 18px;
            border-radius: 0px;
        }}

        QMenuBar::item:hover,
        QMenuBar::item:selected {{
            color: {c.TEXT_PRIMARY};
            background-color: {c.BG_ELEVATED};
        }}

        QMenu {{
            background-color: {c.BG_ELEVATED};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 8px;
            padding: 6px 0px;
        }}

        QMenu::item {{
            padding: 8px 32px 8px 16px;
        }}

        QMenu::item:selected {{
            background-color: {c.ACCENT_SUBTLE};
            color: {c.ACCENT};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {c.BORDER_SUBTLE};
            margin: 4px 12px;
        }}


        /* ── BOTÕES ────────────────────────────────────────── */

        /* Botão padrão (neutro) */
        QPushButton {{
            background-color: {c.BG_SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: 500;
            min-height: 18px;
        }}

        QPushButton:hover {{
            background-color: {c.BG_ELEVATED};
            border-color: {c.BORDER_STRONG};
        }}

        QPushButton:pressed {{
            background-color: {c.BG_BASE};
        }}

        QPushButton:disabled {{
            background-color: {c.BG_BASE};
            color: {c.TEXT_MUTED};
            border-color: {c.BORDER_SUBTLE};
        }}

        /* Botão primário (accent — teal) */
        QPushButton#btnPrimary,
        QPushButton[cssClass="primary"] {{
            background-color: {c.ACCENT};
            color: {c.TEXT_INVERSE};
            border: 1px solid {c.ACCENT};
            font-weight: 600;
        }}

        QPushButton#btnPrimary:hover,
        QPushButton[cssClass="primary"]:hover {{
            background-color: {c.ACCENT_HOVER};
            border-color: {c.ACCENT_HOVER};
        }}

        QPushButton#btnPrimary:pressed,
        QPushButton[cssClass="primary"]:pressed {{
            background-color: {c.ACCENT_PRESSED};
            border-color: {c.ACCENT_PRESSED};
        }}

        /* Botão de perigo (vermelho) */
        QPushButton#btnDanger,
        QPushButton[cssClass="danger"] {{
            background-color: {c.DANGER};
            color: #ffffff;
            border: 1px solid {c.DANGER};
            font-weight: 600;
        }}

        QPushButton#btnDanger:hover,
        QPushButton[cssClass="danger"]:hover {{
            background-color: {c.DANGER_HOVER};
            border-color: {c.DANGER_HOVER};
        }}

        QPushButton#btnDanger:pressed,
        QPushButton[cssClass="danger"]:pressed {{
            background-color: {c.DANGER_PRESSED};
            border-color: {c.DANGER_PRESSED};
        }}

        /* Botão secundário (violet) */
        QPushButton#btnSecondary,
        QPushButton[cssClass="secondary"] {{
            background-color: {c.SECONDARY};
            color: #ffffff;
            border: 1px solid {c.SECONDARY};
            font-weight: 600;
        }}

        QPushButton#btnSecondary:hover,
        QPushButton[cssClass="secondary"]:hover {{
            background-color: {c.SECONDARY_HOVER};
            border-color: {c.SECONDARY_HOVER};
        }}

        /* Botão ghost / outline */
        QPushButton#btnGhost,
        QPushButton[cssClass="ghost"] {{
            background-color: transparent;
            color: {c.ACCENT};
            border: 1px solid {c.ACCENT};
        }}

        QPushButton#btnGhost:hover,
        QPushButton[cssClass="ghost"]:hover {{
            background-color: {c.ACCENT_SUBTLE};
        }}


        /* ── CARDS (QFrame / QGroupBox) ────────────────────── */
        QFrame#card,
        QFrame[cssClass="card"] {{
            background-color: {c.BG_BASE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 10px;
            padding: 16px;
        }}

        QFrame#cardAccent,
        QFrame[cssClass="cardAccent"] {{
            background-color: {c.BG_BASE};
            border: 1px solid {c.ACCENT};
            border-radius: 10px;
            padding: 16px;
        }}

        QGroupBox {{
            background-color: {c.BG_BASE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 10px;
            margin-top: 24px;
            padding: 24px 16px 16px 16px;
            font-weight: 600;
            color: {c.TEXT_PRIMARY};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 14px;
            left: 12px;
            color: {c.TEXT_PRIMARY};
            font-size: 14px;
            font-weight: 700;
        }}


        /* ── STAT CARDS (números do dashboard) ─────────────── */
        QFrame#statCard {{
            background-color: {c.BG_BASE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 10px;
            padding: 20px;
        }}

        QLabel#statNumber {{
            font-size: 32px;
            font-weight: 700;
            color: {c.TEXT_PRIMARY};
        }}

        QLabel#statLabel {{
            font-size: 12px;
            font-weight: 400;
            color: {c.TEXT_SECONDARY};
            text-transform: uppercase;
        }}

        QLabel#statNumberAccent {{
            font-size: 32px;
            font-weight: 700;
            color: {c.ACCENT};
        }}

        QLabel#statNumberDanger {{
            font-size: 32px;
            font-weight: 700;
            color: {c.DANGER};
        }}

        QLabel#statNumberWarning {{
            font-size: 32px;
            font-weight: 700;
            color: {c.WARNING};
        }}


        /* ── TABELAS ───────────────────────────────────────── */
        QTableWidget, QTableView, QTreeView, QListView {{
            background-color: {c.BG_DARK};
            alternate-background-color: {c.BG_BASE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 8px;
            gridline-color: {c.BORDER_SUBTLE};
            selection-background-color: {c.ACCENT_SUBTLE};
            selection-color: {c.ACCENT};
            font-size: 13px;
        }}

        QTableWidget::item, QTableView::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {c.BORDER_SUBTLE};
        }}

        QTableWidget::item:hover, QTableView::item:hover {{
            background-color: {c.BG_ELEVATED};
        }}

        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {c.ACCENT_SUBTLE};
            color: {c.ACCENT};
        }}

        QHeaderView {{
            background-color: {c.BG_DARK};
            border: none;
        }}

        QHeaderView::section {{
            background-color: {c.BG_BASE};
            color: {c.TEXT_SECONDARY};
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid {c.BORDER_DEFAULT};
            border-right: 1px solid {c.BORDER_SUBTLE};
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }}

        QHeaderView::section:hover {{
            color: {c.TEXT_PRIMARY};
            background-color: {c.BG_ELEVATED};
        }}

        QHeaderView::section:first {{
            border-top-left-radius: 8px;
        }}

        QHeaderView::section:last {{
            border-top-right-radius: 8px;
            border-right: none;
        }}


        /* ── INPUTS ────────────────────────────────────────── */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c.BG_SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 8px 12px;
            selection-background-color: {c.ACCENT_SUBTLE};
            selection-color: {c.ACCENT};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c.ACCENT};
        }}

        QLineEdit:disabled {{
            background-color: {c.BG_BASE};
            color: {c.TEXT_MUTED};
        }}

        QLineEdit::placeholder {{
            color: {c.TEXT_MUTED};
        }}


        /* ── COMBOBOX ──────────────────────────────────────── */
        QComboBox {{
            background-color: {c.BG_SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 8px 12px;
            padding-right: 30px;
            min-height: 18px;
        }}

        QComboBox:hover {{
            border-color: {c.BORDER_STRONG};
        }}

        QComboBox:focus {{
            border-color: {c.ACCENT};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 28px;
            subcontrol-position: right center;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c.TEXT_SECONDARY};
            margin-right: 10px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.BG_ELEVATED};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            selection-background-color: {c.ACCENT_SUBTLE};
            selection-color: {c.ACCENT};
            padding: 4px;
        }}


        /* ── CHECKBOX & RADIO ──────────────────────────────── */
        QCheckBox {{
            color: {c.TEXT_PRIMARY};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c.BORDER_DEFAULT};
            border-radius: 4px;
            background-color: {c.BG_SURFACE};
        }}

        QCheckBox::indicator:hover {{
            border-color: {c.ACCENT};
        }}

        QCheckBox::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
            image: none;
        }}

        QRadioButton {{
            color: {c.TEXT_PRIMARY};
            spacing: 8px;
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {c.BORDER_DEFAULT};
            border-radius: 10px;
            background-color: {c.BG_SURFACE};
        }}

        QRadioButton::indicator:hover {{
            border-color: {c.ACCENT};
        }}

        QRadioButton::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
        }}


        /* ── SPINBOX ───────────────────────────────────────── */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.BG_SURFACE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 6px 10px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.ACCENT};
        }}

        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {c.BG_ELEVATED};
            border: none;
            width: 20px;
        }}

        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {c.BG_SURFACE};
        }}


        /* ── SCROLLBAR ─────────────────────────────────────── */
        QScrollBar:vertical {{
            background-color: {c.SCROLLBAR_BG};
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {c.SCROLLBAR_HANDLE};
            min-height: 30px;
            border-radius: 5px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {c.SCROLLBAR_HOVER};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            background-color: {c.SCROLLBAR_BG};
            height: 10px;
            margin: 0px;
            border-radius: 5px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {c.SCROLLBAR_HANDLE};
            min-width: 30px;
            border-radius: 5px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {c.SCROLLBAR_HOVER};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}


        /* ── PROGRESS BAR ──────────────────────────────────── */
        QProgressBar {{
            background-color: {c.BG_SURFACE};
            border: none;
            border-radius: 4px;
            text-align: center;
            color: {c.TEXT_PRIMARY};
            font-size: 11px;
            font-weight: 600;
            min-height: 8px;
            max-height: 8px;
        }}

        QProgressBar::chunk {{
            background-color: {c.ACCENT};
            border-radius: 4px;
        }}


        /* ── TOOLBAR ───────────────────────────────────────── */
        QToolBar {{
            background-color: {c.BG_DARK};
            border-bottom: 1px solid {c.BORDER_SUBTLE};
            padding: 4px 8px;
            spacing: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
        }}

        QToolButton:hover {{
            background-color: {c.BG_ELEVATED};
            color: {c.TEXT_PRIMARY};
        }}

        QToolButton:checked {{
            background-color: {c.ACCENT_SUBTLE};
            color: {c.ACCENT};
        }}


        /* ── STATUS BAR ────────────────────────────────────── */
        QStatusBar {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_SECONDARY};
            border-top: 1px solid {c.BORDER_SUBTLE};
            font-size: 12px;
            padding: 4px 12px;
        }}

        QStatusBar::item {{
            border: none;
        }}

        QStatusBar QLabel {{
            color: {c.TEXT_SECONDARY};
            background-color: transparent;
            padding: 0 8px;
        }}


        /* ── TOOLTIP ───────────────────────────────────────── */
        QToolTip {{
            background-color: {c.BG_ELEVATED};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}


        /* ── SPLITTER ──────────────────────────────────────── */
        QSplitter::handle {{
            background-color: {c.BORDER_SUBTLE};
        }}

        QSplitter::handle:horizontal {{
            width: 2px;
        }}

        QSplitter::handle:vertical {{
            height: 2px;
        }}

        QSplitter::handle:hover {{
            background-color: {c.ACCENT};
        }}


        /* ── SLIDER ────────────────────────────────────────── */
        QSlider::groove:horizontal {{
            background-color: {c.BG_SURFACE};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background-color: {c.ACCENT};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {c.ACCENT_HOVER};
        }}

        QSlider::sub-page:horizontal {{
            background-color: {c.ACCENT};
            border-radius: 3px;
        }}


        /* ── DIALOG ────────────────────────────────────────── */
        QDialog {{
            background-color: {c.BG_DARKEST};
        }}

        QMessageBox {{
            background-color: {c.BG_DARKEST};
        }}


        /* ── LABELS UTILITÁRIOS ────────────────────────────── */
        QLabel {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}

        QLabel#labelMuted {{
            color: {c.TEXT_MUTED};
        }}

        QLabel#labelSecondary {{
            color: {c.TEXT_SECONDARY};
        }}

        QLabel#labelAccent {{
            color: {c.ACCENT};
            font-weight: 600;
        }}

        QLabel#labelDanger {{
            color: {c.DANGER};
            font-weight: 600;
        }}

        QLabel#labelSuccess {{
            color: {c.SUCCESS};
            font-weight: 600;
        }}

        QLabel#labelWarning {{
            color: {c.WARNING};
            font-weight: 600;
        }}

        QLabel#title {{
            font-size: 20px;
            font-weight: 700;
            color: {c.TEXT_PRIMARY};
        }}

        QLabel#subtitle {{
            font-size: 14px;
            font-weight: 400;
            color: {c.TEXT_SECONDARY};
        }}

        QLabel#brand {{
            font-size: 16px;
            font-weight: 700;
            color: {c.ACCENT};
        }}


        /* ── STACKED WIDGET ────────────────────────────────── */
        QStackedWidget {{
            background-color: {c.BG_DARKEST};
        }}
        """

    @classmethod
    def apply(cls, app):
        """Aplica o tema diretamente no QApplication."""
        app.setStyleSheet(cls.get_stylesheet())


# ── Funções auxiliares para uso nos widgets ────────────────────

def style_status_label(label, status: str):
    """
    Aplica cor ao QLabel conforme o status.
    Uso: style_status_label(my_label, "Concluido")
    """
    c = Colors()
    status_map = {
        "rodando":   c.STATUS_RUNNING,
        "running":   c.STATUS_RUNNING,
        "pausado":   c.STATUS_PAUSED,
        "paused":    c.STATUS_PAUSED,
        "parado":    c.STATUS_STOPPED,
        "stopped":   c.STATUS_STOPPED,
        "erro":      c.STATUS_ERROR,
        "error":     c.STATUS_ERROR,
        "concluido": c.STATUS_COMPLETED,
        "completed": c.STATUS_COMPLETED,
    }
    color = status_map.get(status.lower(), c.TEXT_PRIMARY)
    label.setStyleSheet(f"color: {color}; font-weight: 600; background: transparent;")


def set_button_class(button, css_class: str):
    """
    Define a classe visual de um QPushButton.
    Classes: "primary", "danger", "secondary", "ghost"
    Uso: set_button_class(my_button, "primary")
    """
    button.setProperty("cssClass", css_class)
    button.style().unpolish(button)
    button.style().polish(button)
