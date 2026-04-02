"""
LogsTab - Activity log viewer with filters and auto-refresh.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.base import BaseTab
from gui.theme import COLOR_ERROR, COLOR_SUCCESS, COLOR_WARNING

_STATUS_COLORS = {
    "success": COLOR_SUCCESS,
    "failed": COLOR_ERROR,
    "error": COLOR_ERROR,
    "skipped": COLOR_WARNING,
}


class LogsTab(BaseTab):
    """Activity logs tab with filtering, auto-refresh, and clear functionality.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    AUTO_REFRESH_MS = 5000

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh_tick)
        self._build_ui()
        self.refresh()
        # Auto-refresh on by default
        self._auto_refresh_cb.setChecked(True)

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Header
        header_lbl = QLabel("Logs de Atividade")
        header_lbl.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(header_lbl)

        # Filters row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        # Account filter
        filter_layout.addWidget(QLabel("Conta:"))
        self._filter_account = QComboBox()
        self._filter_account.setMinimumWidth(130)
        self._filter_account.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self._filter_account)

        # Action type filter
        filter_layout.addWidget(QLabel("Acao:"))
        self._filter_action = QComboBox()
        self._filter_action.addItems(
            ["Todas", "like", "follow", "retweet", "unfollow", "like_comment", "login", "browse", "sistema"]
        )
        self._filter_action.setMinimumWidth(100)
        self._filter_action.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self._filter_action)

        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self._filter_status = QComboBox()
        self._filter_status.addItems(["Todos", "success", "failed", "skipped"])
        self._filter_status.setMinimumWidth(90)
        self._filter_status.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self._filter_status)

        # Auto-refresh checkbox
        self._auto_refresh_cb = QCheckBox("Atualizar automaticamente")
        self._auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        filter_layout.addWidget(self._auto_refresh_cb)

        filter_layout.addStretch()

        # Buttons
        btn_refresh = QPushButton("Atualizar")
        btn_refresh.setObjectName("accent")
        btn_refresh.clicked.connect(self.refresh)
        filter_layout.addWidget(btn_refresh)

        btn_clear = QPushButton("Limpar Logs")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_logs)
        filter_layout.addWidget(btn_clear)

        layout.addLayout(filter_layout)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Data/Hora", "Conta", "Acao", "Alvo", "Status", "Erro"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload logs from the database, applying current filters."""
        self._table.setRowCount(0)
        self._update_account_filter()

        query = """
            SELECT al.executed_at, a.username, al.action_type,
                   al.target_username, al.status, al.error_message
            FROM activity_logs al
            LEFT JOIN accounts a ON al.account_id = a.id
            WHERE 1=1
        """
        params: list = []

        # Account filter
        acct = self._filter_account.currentText()
        if acct and acct != "Todas":
            query += " AND a.username = ?"
            params.append(acct.lstrip("@"))

        # Action filter
        action = self._filter_action.currentText()
        if action and action != "Todas":
            query += " AND al.action_type = ?"
            params.append(action)

        # Status filter
        status = self._filter_status.currentText()
        if status and status != "Todos":
            query += " AND al.status = ?"
            params.append(status)

        query += " ORDER BY al.id DESC LIMIT 1000"

        rows = self.app.db.fetch_all(query, tuple(params))

        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            status_val = row.get("status", "")
            color = QColor(_STATUS_COLORS.get(status_val, "#e0e0e0"))

            # Format date from YYYY-MM-DD HH:MM:SS to DD/MM/YYYY HH:MM:SS
            raw_date = row.get("executed_at", "")
            try:
                dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                formatted_date = dt.strftime("%d/%m/%Y %H:%M:%S")
            except (ValueError, TypeError):
                formatted_date = raw_date

            values = [
                formatted_date,
                f"@{row.get('username', '???')}",
                row.get("action_type", ""),
                f"@{row.get('target_username', '')}" if row.get("target_username") else "\u2014",
                status_val,
                row.get("error_message") or "\u2014",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setForeground(color)
                if col in (2, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(i, col, item)

    def _update_account_filter(self) -> None:
        """Refresh the account filter dropdown."""
        accounts = self.app.account_manager.get_all_accounts()
        names = ["Todas"] + [f"@{a.get('username', '???')}" for a in accounts]

        current = self._filter_account.currentText()
        self._filter_account.blockSignals(True)
        self._filter_account.clear()
        self._filter_account.addItems(names)
        idx = self._filter_account.findText(current)
        self._filter_account.setCurrentIndex(idx if idx >= 0 else 0)
        self._filter_account.blockSignals(False)

    def on_new_log(self, msg: dict) -> None:
        """Handle a log message from the engine queue (trigger refresh)."""
        if self._auto_refresh_cb.isChecked():
            self.refresh()

    # ==================================================================
    # Actions
    # ==================================================================

    def _clear_logs(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Tem certeza que deseja limpar todos os logs?\nEsta acao nao pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.app.db.execute("DELETE FROM activity_logs")
        self.app.set_status("Logs limpos")
        self.refresh()

    def _toggle_auto_refresh(self, checked: bool) -> None:
        if checked:
            self.refresh()
            self._auto_refresh_timer.start(self.AUTO_REFRESH_MS)
        else:
            self._auto_refresh_timer.stop()

    def _auto_refresh_tick(self) -> None:
        self.refresh()
