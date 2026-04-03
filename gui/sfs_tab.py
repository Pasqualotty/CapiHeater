"""
SfsTab - CRUD interface for managing SFS (Shoutout For Shoutout) sessions.
"""

import logging
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.base import BaseTab, SortableItem
from gui.theme import STATUS_COLORS

logger = logging.getLogger(__name__)


def _setup_searchable_combo(combo: QComboBox, items: list[str]) -> None:
    """Torna um QComboBox pesquisavel por substring, case-insensitive.

    O usuario pode digitar para filtrar as opcoes, mas nao pode confirmar
    um valor que nao exista na lista — ao perder foco o combo restaura a
    selecao valida mais proxima.
    """
    combo.setEditable(True)
    completer = QCompleter(items)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    combo.setCompleter(completer)

    def _on_editing_finished() -> None:
        text = combo.lineEdit().text()
        # busca exata primeiro, depois case-insensitive
        idx = combo.findText(text, Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            for i in range(combo.count()):
                if combo.itemText(i).lower() == text.lower():
                    idx = i
                    break
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            # texto nao corresponde a nenhum item — restaura selecao atual
            combo.lineEdit().setText(combo.itemText(combo.currentIndex()))

    combo.lineEdit().editingFinished.connect(_on_editing_finished)


# Pace option labels  <-> DB values
PACE_LABELS = ["Conservador", "Normal", "Agressivo"]
PACE_VALUES = {"Conservador": "slow", "Normal": "normal", "Agressivo": "fast"}
PACE_LABELS_BY_VALUE = {v: k for k, v in PACE_VALUES.items()}


def _build_actions_label(session: dict) -> str:
    """Return a compact action string, e.g. 'L* F RT C'."""
    parts = []
    if session.get("action_like", 1):
        parts.append("L*" if session.get("like_latest_post", 0) else "L")
    if session.get("action_follow", 1):
        parts.append("F")
    if session.get("action_retweet", 1):
        parts.append("RT*" if session.get("rt_latest_post", 0) else "RT")
    if session.get("action_comment_like", 0):
        parts.append("C")
    return " ".join(parts) if parts else "\u2014"


class SfsTab(BaseTab):
    """SFS sessions management tab.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

        # Refresh table every 5 s while any SFS session is running
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(5000)

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # ---------- Toolbar ----------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        heading = QLabel("Sessoes SFS")
        heading.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        toolbar.addWidget(heading)
        toolbar.addStretch()

        self._btn_new = QPushButton("+ Nova Sessao")
        self._btn_new.setObjectName("accent")
        self._btn_new.clicked.connect(self._create_dialog)
        toolbar.addWidget(self._btn_new)

        self._btn_edit = QPushButton("Editar")
        self._btn_edit.clicked.connect(self._edit_dialog)
        toolbar.addWidget(self._btn_edit)

        self._btn_delete = QPushButton("Excluir")
        self._btn_delete.setObjectName("danger")
        self._btn_delete.clicked.connect(self._delete_sessions)
        toolbar.addWidget(self._btn_delete)

        toolbar.addWidget(_separator())

        self._btn_start = QPushButton("Iniciar")
        self._btn_start.clicked.connect(self._start_sessions)
        toolbar.addWidget(self._btn_start)

        self._btn_stop = QPushButton("Parar")
        self._btn_stop.clicked.connect(self._stop_sessions)
        toolbar.addWidget(self._btn_stop)

        self._btn_pause = QPushButton("Pausar")
        self._btn_pause.clicked.connect(self._pause_or_resume_sessions)
        toolbar.addWidget(self._btn_pause)

        layout.addLayout(toolbar)

        # ---------- Table ----------
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Nome", "Alvos", "Acoes", "Ritmo", "Conta", "Status"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 120)
        self._table.setColumnWidth(5, 90)

        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._edit_dialog)
        self._table.setSortingEnabled(True)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self._table)

        # Ctrl+A
        self._shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), self._table)
        self._shortcut_select_all.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._shortcut_select_all.activated.connect(self._table.selectAll)

        # ---------- Info bar ----------
        self._sel_info = QLabel(
            "0 sessoes | Ctrl+A = selecionar todas | Duplo clique = editar"
        )
        layout.addWidget(self._sel_info)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload sessions from database and repopulate the table."""
        sessions = self.app.sfs_manager.get_all_sessions()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        for session in sessions:
            row = self._table.rowCount()
            self._table.insertRow(row)

            total = int(session.get("total_targets") or 0)
            actions_label = _build_actions_label(session)
            pace_label = PACE_LABELS_BY_VALUE.get(session.get("pace", "normal"), "Normal")
            account_username = session.get("account_username", "?")
            status = session.get("status", "idle")

            # col: 0=Nome, 1=Alvos, 2=Acoes, 3=Ritmo, 4=Conta, 5=Status
            values = (
                session.get("name", ""),
                str(total),
                actions_label,
                pace_label,
                f"@{account_username}",
                status,
            )

            for col, text in enumerate(values):
                if col == 1:
                    cell = SortableItem(text, sort_key=total)
                else:
                    cell = SortableItem(text)
                cell.setData(Qt.ItemDataRole.UserRole, session["id"])
                if col in (1, 2, 3, 4, 5):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 5:
                    color = STATUS_COLORS.get(status)
                    if color:
                        cell.setForeground(QColor(color))
                self._table.setItem(row, col, cell)

        self._table.setSortingEnabled(True)

        total_count = len(sessions)
        self._sel_info.setText(
            f"{total_count} sessao(oes) | Ctrl+A = selecionar todas | Duplo clique = editar"
        )
        self._update_button_states()

    def _get_selected_ids(self) -> list[int]:
        ids = []
        for idx in self._table.selectionModel().selectedRows():
            item = self._table.item(idx.row(), 0)
            if item is not None:
                sid = item.data(Qt.ItemDataRole.UserRole)
                if sid is not None:
                    ids.append(sid)
        return ids

    def _get_selected_id(self) -> int | None:
        ids = self._get_selected_ids()
        return ids[0] if ids else None

    def _on_selection_changed(self) -> None:
        count = len(self._table.selectionModel().selectedRows())
        if count == 0:
            self._sel_info.setText("Nenhuma selecionada")
        elif count == 1:
            self._sel_info.setText("1 sessao selecionada")
        else:
            self._sel_info.setText(f"{count} sessoes selecionadas")
        self._update_button_states()

    def _update_button_states(self) -> None:
        """Enable/disable action buttons based on selection."""
        ids = self._get_selected_ids()
        has_selection = len(ids) > 0

        self._btn_edit.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)
        self._btn_start.setEnabled(has_selection)
        self._btn_stop.setEnabled(has_selection)
        self._btn_pause.setEnabled(has_selection)

        # Update pause/resume label based on selected statuses
        if len(ids) == 1:
            session = self.app.sfs_manager.get_session(ids[0])
            if session and session.get("status") == "paused":
                self._btn_pause.setText("Retomar")
                return
        self._btn_pause.setText("Pausar")

    # ==================================================================
    # Context menu
    # ==================================================================

    def _show_context_menu(self, pos) -> None:
        idx = self._table.indexAt(pos)
        if idx.isValid():
            row = idx.row()
            if row not in {i.row() for i in self._table.selectionModel().selectedRows()}:
                self._table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("Editar", self._edit_dialog)
        menu.addSeparator()
        menu.addAction("Iniciar", self._start_sessions)
        menu.addAction("Parar", self._stop_sessions)
        menu.addAction("Pausar / Retomar", self._pause_or_resume_sessions)
        menu.addSeparator()
        menu.addAction("Excluir", self._delete_sessions)
        menu.addSeparator()
        menu.addAction("Selecionar Todas", self._table.selectAll)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    # ==================================================================
    # Dialog helpers
    # ==================================================================

    def _create_dialog(self) -> None:
        self._open_session_form(session=None)

    def _edit_dialog(self) -> None:
        sid = self._get_selected_id()
        if sid is None:
            QMessageBox.warning(self, "Aviso", "Selecione uma sessao para editar.")
            return
        session = self.app.sfs_manager.get_session(sid)
        if session is None:
            return
        self._open_session_form(session=session)

    def _open_session_form(self, session: dict | None) -> None:
        """Open the create/edit dialog for an SFS session."""
        is_edit = session is not None

        dlg = QDialog(self)
        dlg.setWindowTitle("Editar Sessao SFS" if is_edit else "Nova Sessao SFS")
        dlg.resize(500, 560)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        title_lbl = QLabel("Editar Sessao SFS" if is_edit else "Nova Sessao SFS")
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_lbl)

        # ---------- Nome ----------
        layout.addWidget(QLabel("Nome da sessao:"))
        ent_name = QLineEdit()
        ent_name.setPlaceholderText("Ex: SFS Janeiro 2026")
        layout.addWidget(ent_name)

        # ---------- Conta ----------
        layout.addWidget(QLabel("Conta:"))
        combo_account = QComboBox()
        accounts = sorted(
            self.app.account_manager.get_all_accounts(),
            key=lambda a: a["username"].lower(),
        )
        account_ids: list[int] = []
        for acc in accounts:
            combo_account.addItem(f"@{acc['username']}")
            account_ids.append(acc["id"])
        _setup_searchable_combo(combo_account, [f"@{a['username']}" for a in accounts])
        layout.addWidget(combo_account)

        # ---------- Alvos ----------
        layout.addWidget(QLabel("Alvos (um por linha — @usuario ou link):"))
        txt_targets = QPlainTextEdit()
        txt_targets.setPlaceholderText(
            "https://x.com/usuario\n@usuario\nusuario"
        )
        txt_targets.setFixedHeight(100)
        layout.addWidget(txt_targets)

        # ---------- Acoes ----------
        layout.addWidget(QLabel("Acoes:"))
        actions_row = QHBoxLayout()
        chk_follow = QCheckBox("Seguir")
        chk_like = QCheckBox("Curtir")
        chk_rt = QCheckBox("RT")
        chk_cl = QCheckBox("Like coment.")
        chk_like_latest = QCheckBox("Like ultima post.")
        chk_rt_latest = QCheckBox("RT ultima post.")
        for chk, default in (
            (chk_follow, False),
            (chk_like, True),
            (chk_rt, True),
            (chk_cl, False),
        ):
            chk.setChecked(default)
            actions_row.addWidget(chk)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        latest_row = QHBoxLayout()
        for chk in (chk_like_latest, chk_rt_latest):
            chk.setChecked(True)
            latest_row.addWidget(chk)
        latest_row.addStretch()
        layout.addLayout(latest_row)

        # ---------- Ritmo ----------
        layout.addWidget(QLabel("Ritmo:"))
        pace_row = QHBoxLayout()
        pace_group = QButtonGroup(dlg)
        radio_slow = QRadioButton("Conservador")
        radio_normal = QRadioButton("Normal")
        radio_fast = QRadioButton("Agressivo")
        radio_normal.setChecked(True)
        for rb in (radio_slow, radio_normal, radio_fast):
            pace_group.addButton(rb)
            pace_row.addWidget(rb)
        pace_row.addStretch()
        layout.addLayout(pace_row)

        # ---------- Pre-fill for edit ----------
        if is_edit:
            ent_name.setText(session.get("name", ""))

            # Select account
            account_id = session.get("account_id")
            if account_id in account_ids:
                combo_account.setCurrentIndex(account_ids.index(account_id))

            # Pre-fill targets textarea
            existing_targets = self.app.sfs_manager.get_session_targets(session["id"])
            lines = [f"@{t['username']}" for t in existing_targets]
            txt_targets.setPlainText("\n".join(lines))

            # Action flags — chk_follow=Seguir->action_follow, chk_like=Curtir->action_like
            chk_follow.setChecked(bool(session.get("action_follow", 1)))
            chk_like.setChecked(bool(session.get("action_like", 1)))
            chk_rt.setChecked(bool(session.get("action_retweet", 1)))
            chk_cl.setChecked(bool(session.get("action_comment_like", 0)))
            chk_like_latest.setChecked(bool(session.get("like_latest_post", 0)))
            chk_rt_latest.setChecked(bool(session.get("rt_latest_post", 0)))

            pace = session.get("pace", "normal")
            if pace == "slow":
                radio_slow.setChecked(True)
            elif pace == "fast":
                radio_fast.setChecked(True)
            else:
                radio_normal.setChecked(True)

        # ---------- Buttons ----------
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("accent")
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---------- Save handler ----------
        def on_save() -> None:
            name = ent_name.text().strip()
            if not name:
                QMessageBox.critical(dlg, "Erro", "O nome da sessao e obrigatorio.")
                return

            if not account_ids:
                QMessageBox.critical(
                    dlg, "Erro", "Nenhuma conta cadastrada. Adicione uma conta primeiro."
                )
                return

            selected_account_id = account_ids[combo_account.currentIndex()]

            # Parse target usernames from textarea
            raw_lines = txt_targets.toPlainText().strip().splitlines()
            usernames: list[str] = []
            for line in raw_lines:
                uname = _extract_username(line.strip())
                if uname:
                    usernames.append(uname)

            # Resolve/create target IDs
            target_ids = _resolve_target_ids(self.app, usernames)

            # Build actions dict — chk_follow=Seguir->action_follow, chk_like=Curtir->action_like
            actions = {
                "action_like": int(chk_like.isChecked()),
                "action_follow": int(chk_follow.isChecked()),
                "action_retweet": int(chk_rt.isChecked()),
                "action_comment_like": int(chk_cl.isChecked()),
                "like_latest_post": int(chk_like_latest.isChecked()),
                "rt_latest_post": int(chk_rt_latest.isChecked()),
            }

            if radio_slow.isChecked():
                pace = "slow"
            elif radio_fast.isChecked():
                pace = "fast"
            else:
                pace = "normal"

            if is_edit:
                self.app.sfs_manager.update_session(
                    session["id"],
                    name=name,
                    account_id=selected_account_id,
                    pace=pace,
                    **actions,
                )
                # Diff targets: only add new ones and remove deleted ones,
                # preserving completed/completed_at for targets that remain.
                existing = self.app.sfs_manager.get_session_targets(session["id"])
                existing_id_set = {t["id"] for t in existing}
                new_id_set = set(target_ids)
                ids_to_remove = list(existing_id_set - new_id_set)
                ids_to_add = list(new_id_set - existing_id_set)
                if ids_to_remove:
                    self.app.sfs_manager.remove_targets_from_session(
                        session["id"], ids_to_remove
                    )
                if ids_to_add:
                    self.app.sfs_manager.add_targets_to_session(
                        session["id"], ids_to_add
                    )
                self.app.set_status(f"Sessao '{name}' atualizada")
            else:
                sid = self.app.sfs_manager.create_session(
                    name=name,
                    account_id=selected_account_id,
                    actions_dict=actions,
                    pace=pace,
                )
                if target_ids:
                    self.app.sfs_manager.add_targets_to_session(sid, target_ids)
                self.app.set_status(
                    f"Sessao '{name}' criada com {len(target_ids)} alvo(s)"
                )

            dlg.accept()
            self.refresh()

        btn_save.clicked.connect(on_save)
        dlg.exec()

    # ==================================================================
    # Session actions
    # ==================================================================

    def _start_sessions(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais sessoes.")
            return
        started = 0
        failed_names: list[str] = []
        for sid in ids:
            ok = self.app.engine.start_sfs_session(sid, self.app.sfs_manager)
            if ok:
                started += 1
            else:
                session = self.app.sfs_manager.get_session(sid)
                name = session.get("name", str(sid)) if session else str(sid)
                failed_names.append(name)
        if started:
            self.app.set_status(f"{started} sessao(oes) iniciada(s)")
        if failed_names:
            names_list = "\n".join(f"  • {n}" for n in failed_names)
            QMessageBox.warning(
                self,
                "Aviso",
                f"Nao foi possivel iniciar {len(failed_names)} sessao(oes):\n"
                f"{names_list}\n\n"
                "Verifique se a conta ja possui um worker ativo ou se a "
                "sessao esta em execucao.",
            )
        self.refresh()

    def _stop_sessions(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais sessoes.")
            return
        for sid in ids:
            self.app.engine.stop_sfs_session(sid, self.app.sfs_manager)
        self.app.set_status(f"{len(ids)} sessao(oes) parada(s)")
        self.refresh()

    def _pause_or_resume_sessions(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais sessoes.")
            return
        for sid in ids:
            session = self.app.sfs_manager.get_session(sid)
            if session:
                if session.get("status") == "paused":
                    self.app.engine.resume_sfs_session(sid, self.app.sfs_manager)
                else:
                    self.app.engine.pause_sfs_session(sid, self.app.sfs_manager)
        self.app.set_status(f"{len(ids)} sessao(oes) pausada(s)/retomada(s)")
        self.refresh()

    def _auto_refresh(self) -> None:
        """Refresh the table periodically when any session is active."""
        try:
            sessions = self.app.sfs_manager.get_all_sessions()
            active_statuses = {"running", "paused"}
            if any(s.get("status") in active_statuses for s in sessions):
                self.refresh()
        except Exception as exc:
            logger.debug(f"SFS auto_refresh error: {exc}")

    def _delete_sessions(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais sessoes.")
            return
        count = len(ids)
        msg = (
            f"Excluir {count} sessao(oes) SFS?"
            if count > 1
            else "Excluir esta sessao SFS?"
        )
        reply = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for sid in ids:
            self.app.sfs_manager.delete_session(sid)
        self.app.set_status(f"{count} sessao(oes) excluida(s)")
        self.refresh()


# ==================================================================
# Module-level helpers
# ==================================================================

def _separator() -> QLabel:
    """Return a thin vertical separator label for toolbars."""
    sep = QLabel("|")
    sep.setStyleSheet("color: #444466; padding: 0 4px;")
    return sep


def _extract_username(text: str) -> str | None:
    """Extract a Twitter/X username from a URL or raw text.

    Replicates the logic from TargetsTab._extract_username.
    """
    text = text.strip().rstrip("/")
    if not text:
        return None

    # URL com ou sem protocolo (case-insensitive)
    match = re.match(
        r'(?:https?://)?(?:www\.)?(?:x|twitter)\.com/(@?[\w]+)', text, re.IGNORECASE
    )
    if match:
        return match.group(1).lstrip("@")

    # @usuario em qualquer posicao do texto
    match = re.search(r'@([\w]+)', text)
    if match:
        return match.group(1)

    match = re.match(r'^([\w]+)$', text)
    if match and len(text) <= 30:
        return match.group(1)

    return None


def _resolve_target_ids(app, usernames: list[str]) -> list[int]:
    """Return target IDs, creating new targets for unknown usernames.

    Parameters
    ----------
    app : CapiHeaterApp
        Main application instance (provides target_manager).
    usernames : list[str]
        List of cleaned usernames (no leading @).

    Returns
    -------
    list[int]
        Ordered list of target IDs corresponding to *usernames*.
    """
    existing_targets = app.target_manager.get_targets(active_only=False)
    username_to_id: dict[str, int] = {
        t["username"].lower(): t["id"] for t in existing_targets
    }

    ids: list[int] = []
    for username in usernames:
        key = username.lower()
        if key in username_to_id:
            ids.append(username_to_id[key])
        else:
            url = f"https://x.com/{username}"
            new_id = app.target_manager.add_target(username=username, url=url)
            username_to_id[key] = new_id
            ids.append(new_id)

    ids = list(dict.fromkeys(ids))
    return ids
