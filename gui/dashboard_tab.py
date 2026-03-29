"""
DashboardTab - Overview of all accounts and quick controls.
"""

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.base import BaseTab
from gui.theme import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    FG_MUTED,
    FG_TITLE,
)

_STATUS_COLORS = {
    "running": COLOR_SUCCESS,
    "paused": COLOR_WARNING,
    "error": COLOR_ERROR,
    "idle": "#9e9e9e",
    "completed": "#2979ff",
    "stopping": "#ff9100",
}


class DashboardTab(BaseTab):
    """Dashboard showing overview cards and per-account status list.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._account_rows: dict[int, int] = {}  # account_id -> table row
        self._accounts_cache: list[dict] = []
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # ---------- Overview cards row ----------
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._card_labels: dict[str, QLabel] = {}
        card_defs = [
            ("total", "Total de Contas"),
            ("running", "Rodando"),
            ("paused", "Pausadas"),
            ("errors", "Erros"),
        ]
        for key, caption in card_defs:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            val_lbl = QLabel("0")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setStyleSheet(f"font-size: 20pt; font-weight: bold; color: {FG_TITLE};")
            card_layout.addWidget(val_lbl)

            cap_lbl = QLabel(caption)
            cap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap_lbl.setStyleSheet(f"font-size: 9pt; color: {FG_MUTED};")
            card_layout.addWidget(cap_lbl)

            self._card_labels[key] = val_lbl
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # ---------- Buttons row ----------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        btn_start_all = QPushButton("Iniciar Todos")
        btn_start_all.setObjectName("accent")
        btn_start_all.clicked.connect(self._start_all)
        btn_layout.addWidget(btn_start_all)

        btn_stop_all = QPushButton("Parar Todos")
        btn_stop_all.setObjectName("danger")
        btn_stop_all.clicked.connect(self._stop_all)
        btn_layout.addWidget(btn_stop_all)

        btn_refresh = QPushButton("Atualizar")
        btn_refresh.setObjectName("accent")
        btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(btn_refresh)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---------- Account table ----------
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["", "Conta", "Status", "Dia"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 30)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Selection info
        self._sel_info = QLabel("")
        layout.addWidget(self._sel_info)

        # Action buttons below table
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)

        btn_start_sel = QPushButton("Iniciar Selecionadas")
        btn_start_sel.setObjectName("accent")
        btn_start_sel.clicked.connect(self._start_selected)
        action_layout.addWidget(btn_start_sel)

        btn_pause_sel = QPushButton("Pausar Selecionadas")
        btn_pause_sel.clicked.connect(self._pause_selected)
        action_layout.addWidget(btn_pause_sel)

        btn_stop_sel = QPushButton("Parar Selecionadas")
        btn_stop_sel.setObjectName("danger")
        btn_stop_sel.clicked.connect(self._stop_selected)
        action_layout.addWidget(btn_stop_sel)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    # ==================================================================
    # Data refresh
    # ==================================================================

    def refresh(self) -> None:
        """Reload account data from the database and update the view."""
        accounts = self.app.account_manager.get_all_accounts()
        self._accounts_cache = accounts

        # Update overview cards
        total = len(accounts)
        running = sum(1 for a in accounts if a.get("status") == "running")
        paused = sum(1 for a in accounts if a.get("status") == "paused")
        errors = sum(1 for a in accounts if a.get("status") == "error")

        self._card_labels["total"].setText(str(total))
        self._card_labels["running"].setText(str(running))
        self._card_labels["paused"].setText(str(paused))
        self._card_labels["errors"].setText(str(errors))

        # Update table
        self._table.setRowCount(0)
        self._account_rows.clear()

        self._table.setRowCount(len(accounts))
        for i, acc in enumerate(accounts):
            aid = acc.get("id", 0)
            status = acc.get("status", "idle")
            day = acc.get("current_day", 1)
            color = QColor(_STATUS_COLORS.get(status, "#9e9e9e"))

            dot = "\u25cf" if status in ("running", "paused", "error", "completed") else "\u25cb"
            values = [dot, f"@{acc.get('username', '???')}", self._status_label(status), f"Dia {day}"]
            alignments = [
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter,
            ]

            for col, (val, align) in enumerate(zip(values, alignments)):
                item = QTableWidgetItem(val)
                item.setForeground(color)
                item.setTextAlignment(align)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, aid)
                self._table.setItem(i, col, item)

            self._account_rows[aid] = i

    def on_status_update(self, msg: dict) -> None:
        """Handle a status_update message from the engine queue."""
        self.refresh()

    # ==================================================================
    # Actions
    # ==================================================================

    def _start_all(self) -> None:
        started = self.app.engine.start_all()
        self.app.set_status(f"Iniciadas {len(started)} conta(s)")
        self.refresh()

    def _stop_all(self) -> None:
        self.app.engine.stop_all()
        self.app.set_status("Todas as contas paradas")
        self.refresh()

    def _get_selected_account_ids(self) -> list[int]:
        """Return list of selected account IDs."""
        ids = []
        for idx in self._table.selectionModel().selectedRows():
            item = self._table.item(idx.row(), 0)
            if item:
                aid = item.data(Qt.ItemDataRole.UserRole)
                if aid is not None:
                    ids.append(aid)
        return ids

    def _on_selection_changed(self) -> None:
        count = len(self._table.selectionModel().selectedRows())
        if count == 0:
            self._sel_info.setText("")
        elif count == 1:
            self._sel_info.setText("1 conta selecionada")
        else:
            self._sel_info.setText(f"{count} contas selecionadas")

    def _start_selected(self) -> None:
        ids = self._get_selected_account_ids()
        if not ids:
            self.app.set_status("Selecione uma conta primeiro")
            return
        started = 0
        for aid in ids:
            if self.app.engine.start_account(aid):
                started += 1
        self.app.set_status(f"{started} conta(s) iniciada(s)")
        self.refresh()

    def _pause_selected(self) -> None:
        ids = self._get_selected_account_ids()
        if not ids:
            self.app.set_status("Selecione uma conta primeiro")
            return
        for aid in ids:
            self.app.engine.pause_account(aid)
        self.app.set_status(f"{len(ids)} conta(s) pausada(s)")
        self.refresh()

    def _stop_selected(self) -> None:
        ids = self._get_selected_account_ids()
        if not ids:
            self.app.set_status("Selecione uma conta primeiro")
            return
        for aid in ids:
            self.app.engine.stop_account(aid)
        self.app.set_status(f"{len(ids)} conta(s) parada(s)")
        self.refresh()

    def _show_context_menu(self, pos) -> None:
        """Right-click context menu for per-account actions."""
        item = self._table.itemAt(pos)
        if not item:
            return

        row = item.row()
        if row not in [idx.row() for idx in self._table.selectionModel().selectedRows()]:
            self._table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("Iniciar", self._start_selected)
        menu.addAction("Pausar", self._pause_selected)
        menu.addAction("Parar", self._stop_selected)
        menu.addSeparator()
        menu.addAction("Editar Dia", self._edit_day)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _edit_day(self) -> None:
        """Let the user change which warming day an account will run next."""
        ids = self._get_selected_account_ids()
        if len(ids) != 1:
            self.app.set_status("Selecione exatamente uma conta para editar o dia")
            return

        aid = ids[0]
        row_idx = self._account_rows.get(aid)
        if row_idx is None:
            return
        account = self._accounts_cache[row_idx]
        status = account.get("status", "idle")

        if status in ("running", "paused"):
            QMessageBox.warning(self, "Aviso", "Pare a conta antes de editar o dia.")
            return

        current = account.get("current_day", 1)
        new_day, ok = QInputDialog.getInt(
            self,
            "Editar Dia",
            f"Dia atual: {current}\nNovo dia:",
            value=current,
            minValue=1,
            maxValue=365,
        )
        if not ok or new_day == current:
            return

        # Back-calculate start_date so Scheduler.get_day_number() returns new_day
        new_start = (date.today() - timedelta(days=new_day - 1)).isoformat()
        self.app.account_manager.update_account(
            aid, current_day=new_day, start_date=new_start,
        )
        self.app.set_status(f"Dia alterado para {new_day}")
        self.refresh()

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _status_label(status: str) -> str:
        mapping = {
            "running": "Rodando",
            "paused": "Pausado",
            "error": "Erro",
            "idle": "Parado",
            "completed": "Concluido",
            "stopping": "Parando",
        }
        return mapping.get(status, status.capitalize())
