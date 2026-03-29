"""
AdminTab - Painel administrativo para moderadores/admins (dark themed, PT-BR).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AdminTab(QWidget):
    """Admin panel for managing user access.

    Parameters
    ----------
    auth : SupabaseAuth
        Authenticated instance.
    session :
        Current Supabase session.
    """

    def __init__(self, auth, session, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.session = session
        self._all_users: list[dict] = []

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        title_lbl = QLabel("Gerenciamento de Usuarios")
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold;")
        toolbar.addWidget(title_lbl)
        toolbar.addStretch()

        self._grant_btn = QPushButton("Liberar Acesso")
        self._grant_btn.setObjectName("accent")
        self._grant_btn.clicked.connect(self._on_grant)
        toolbar.addWidget(self._grant_btn)

        self._revoke_btn = QPushButton("Revogar Acesso")
        self._revoke_btn.setObjectName("danger")
        self._revoke_btn.clicked.connect(self._on_revoke)
        toolbar.addWidget(self._revoke_btn)

        self._refresh_btn = QPushButton("Atualizar")
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["E-mail", "Papel", "Status", "Ativado em", "Liberado por", "Motivo"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        # Filters row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)
        filter_layout.addWidget(QLabel("Filtro:"))

        self._filter_group = QButtonGroup(self)
        self._filter_group.buttonClicked.connect(self._apply_filter)

        for label in ("Todos", "Ativos", "Inativos", "Liberados Manualmente"):
            rb = QRadioButton(label)
            if label == "Todos":
                rb.setChecked(True)
            self._filter_group.addButton(rb)
            filter_layout.addWidget(rb)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        """Fetch users from Supabase and populate the table."""
        self._all_users = []
        try:
            self._all_users = self.auth.list_users()
        except Exception:
            pass
        self._apply_filter()

    def _apply_filter(self):
        checked = self._filter_group.checkedButton()
        filt = checked.text() if checked else "Todos"

        self._table.setRowCount(0)

        for u in self._all_users:
            is_active = u.get("is_active", False)
            status = "Ativo" if is_active else "Inativo"

            if filt == "Ativos" and not is_active:
                continue
            if filt == "Inativos" and is_active:
                continue
            if filt == "Liberados Manualmente" and not u.get("granted_by"):
                continue

            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                u.get("email", ""),
                u.get("role", "user"),
                status,
                u.get("activated_at", ""),
                u.get("granted_by", ""),
                u.get("grant_reason", ""),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_grant(self):
        email, ok = QInputDialog.getText(
            self, "Liberar Acesso", "Digite o e-mail do usuario:"
        )
        if not ok or not email:
            return

        reason, _ = QInputDialog.getText(
            self, "Motivo", "Motivo da liberacao (opcional):"
        )

        try:
            grantor_id = (
                self.session.user.id if hasattr(self.session, "user") else "unknown"
            )
            self.auth.grant_access(email, grantor_id, reason or "")
            QMessageBox.information(self, "Sucesso", f"Acesso liberado para {email}.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def _on_revoke(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selecione", "Selecione um usuario na tabela.")
            return

        email_item = self._table.item(row, 0)
        email = email_item.text() if email_item else ""

        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja revogar o acesso de {email}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.auth.revoke_access(email)
            QMessageBox.information(self, "Sucesso", f"Acesso revogado de {email}.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
