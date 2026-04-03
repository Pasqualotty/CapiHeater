"""
AccountsTab - CRUD interface for managing Twitter/X accounts.
"""

import json
import webbrowser
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QAbstractItemView,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.base import BaseTab, SortableItem
from gui.theme import (
    ACCENT,
    BG_DARK,
    BG_INPUT,
    BG_SECONDARY,
    FG_MUTED,
    FG_TEXT,
    ACCENT_HIGHLIGHT,
)
from utils.config import DEFAULT_SCROLL_CONFIG, SCROLL_PRESETS


class AccountsTab(BaseTab):
    """Accounts management tab with table and CRUD dialogs.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._all_accounts: list[dict] = []
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(6)

        # ---------- Toolbar ----------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        lbl_heading = QLabel("Gerenciamento de Contas")
        lbl_heading.setStyleSheet("font-size: 13pt; font-weight: bold;")
        toolbar.addWidget(lbl_heading)
        toolbar.addStretch()

        buttons = [
            ("Adicionar", "accent", self._add_account_dialog),
            ("Editar", "accent", self._edit_account_dialog),
            ("Excluir", "danger", self._delete_account),
            ("Cookies", "accent", self._import_cookies),
            ("Importar Massa", "accent", self._bulk_import),
            ("Reiniciar", "danger", self._reset_schedule),
            ("Categorias", "accent", self._manage_categories),
        ]
        for text, obj_name, slot in buttons:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)

        root_layout.addLayout(toolbar)

        # ---------- Search / filter bar ----------
        search_layout = QHBoxLayout()
        search_layout.setSpacing(6)

        search_layout.addWidget(QLabel("Pesquisar:"))
        self._search_edit = QLineEdit()
        self._search_edit.setFixedWidth(180)
        self._search_edit.setPlaceholderText("Filtrar por usuario...")
        self._search_edit.textChanged.connect(self._filter_table)
        search_layout.addWidget(self._search_edit)

        search_layout.addWidget(QLabel("Categoria:"))
        self._cat_filter_combo = QComboBox()
        self._cat_filter_combo.setFixedWidth(160)
        self._cat_filter_combo.currentTextChanged.connect(lambda _: self._filter_table())
        search_layout.addWidget(self._cat_filter_combo)

        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(self._clear_filters)
        search_layout.addWidget(btn_clear)

        search_layout.addStretch()
        root_layout.addLayout(search_layout)

        # ---------- Table ----------
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Usuario", "Status", "Cronograma", "Categoria", "Dia", "Proxy", "Data Inicio"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(lambda _idx: self._open_profile())
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setSortingEnabled(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        root_layout.addWidget(self._table, stretch=1)

        # ---------- Selection info ----------
        self._sel_info = QLabel("")
        root_layout.addWidget(self._sel_info)

        # ---------- Shortcuts (stored to prevent GC) ----------
        self._shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), self._table)
        self._shortcut_select_all.activated.connect(self._select_all)

    # ==================================================================
    # Selection helpers
    # ==================================================================

    def _select_all(self):
        self._table.selectAll()

    def _on_selection_changed(self):
        count = len(self._table.selectionModel().selectedRows())
        if count == 0:
            self._sel_info.setText("")
        elif count == 1:
            self._sel_info.setText("1 conta selecionada")
        else:
            self._sel_info.setText(f"{count} contas selecionadas")

    def _show_context_menu(self, pos):
        index = self._table.indexAt(pos)
        if index.isValid():
            row = index.row()
            if row not in [idx.row() for idx in self._table.selectionModel().selectedRows()]:
                self._table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("Abrir Perfil", self._open_profile)
        menu.addSeparator()
        menu.addAction("Editar", self._edit_account_dialog)
        menu.addAction("Importar Cookies", self._import_cookies)
        menu.addAction("Alternar Ativo", self._toggle_active)
        menu.addSeparator()
        menu.addAction("Reiniciar Cronograma", self._reset_schedule)
        menu.addAction("Excluir Selecionados", self._delete_account)
        menu.addSeparator()
        menu.addAction("Selecionar Todos", self._select_all)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload accounts from the database into the table."""
        accounts = self.app.account_manager.get_all_accounts()
        schedules = self._get_schedule_names()
        cat_mgr = self.app.category_manager

        self._all_accounts = []
        for acc in accounts:
            sched_name = schedules.get(acc.get("schedule_id", 1), "Padrao")
            status_label = self._status_label(acc.get("status", "idle"))
            proxy = acc.get("proxy") or "\u2014"
            cat_names = cat_mgr.get_account_category_names(acc["id"])
            cat_label = ", ".join(cat_names) if cat_names else "\u2014"
            self._all_accounts.append({
                "id": acc["id"],
                "username": acc.get("username", "???"),
                "cat_names": cat_names,
                "values": (
                    f"@{acc.get('username', '???')}",
                    status_label,
                    sched_name,
                    cat_label,
                    str(acc.get("current_day", 1)),
                    proxy,
                    acc.get("start_date", ""),
                ),
            })

        # Update category filter combo
        all_cats = sorted({n for item in self._all_accounts for n in item["cat_names"]})
        current_filter = self._cat_filter_combo.currentText()
        self._cat_filter_combo.blockSignals(True)
        self._cat_filter_combo.clear()
        self._cat_filter_combo.addItems(["Todas", "Sem categoria"] + all_cats)
        idx = self._cat_filter_combo.findText(current_filter)
        self._cat_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._cat_filter_combo.blockSignals(False)

        self._filter_table()

    def _clear_filters(self):
        self._search_edit.clear()
        self._cat_filter_combo.setCurrentIndex(0)

    def _filter_table(self) -> None:
        """Apply search and category filters and repopulate the table."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        query = self._search_edit.text().strip().lower()
        cat_filter = self._cat_filter_combo.currentText()

        row = 0
        for item in self._all_accounts:
            display_name = item["values"][0].lower()
            if query and query not in display_name:
                continue
            if cat_filter == "Sem categoria" and item["cat_names"]:
                continue
            if cat_filter not in ("Todas", "Sem categoria") and cat_filter not in item["cat_names"]:
                continue

            # col indices: 0=Usuario, 1=Status, 2=Cronograma, 3=Categoria, 4=Dia, 5=Proxy, 6=Data Inicio
            vals = item["values"]
            day_val = int(vals[4]) if str(vals[4]).isdigit() else 0
            date_str = str(vals[6]) if vals[6] else ""

            self._table.insertRow(row)
            for col, val in enumerate(vals):
                if col == 4:
                    cell = SortableItem(str(val), sort_key=day_val)
                elif col == 6:
                    cell = SortableItem(str(val), sort_key=date_str)
                else:
                    cell = SortableItem(str(val))
                cell.setData(Qt.ItemDataRole.UserRole, item["id"])
                if col in (1, 2, 3, 4, 6):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, cell)

            row += 1

        self._table.setSortingEnabled(True)

    def _get_schedule_names(self) -> dict[int, str]:
        rows = self.app.db.fetch_all("SELECT id, name FROM schedules ORDER BY id")
        return {r["id"]: r["name"] for r in rows}

    def _get_selected_ids(self) -> list[int]:
        """Return list of selected account IDs."""
        ids = []
        for idx in self._table.selectionModel().selectedRows():
            item = self._table.item(idx.row(), 0)
            if item is not None:
                aid = item.data(Qt.ItemDataRole.UserRole)
                if aid is not None:
                    ids.append(aid)
        return ids

    def _get_selected_id(self) -> int | None:
        """Return a single selected ID (for single-item actions like edit)."""
        ids = self._get_selected_ids()
        return ids[0] if ids else None

    # ==================================================================
    # Dialogs
    # ==================================================================

    def _add_account_dialog(self) -> None:
        self._open_account_form(title="Adicionar Conta", account=None)

    def _edit_account_dialog(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas para editar.")
            return
        if len(ids) == 1:
            account = self.app.account_manager.get_account(ids[0])
            if account is None:
                return
            self._open_account_form(title="Editar Conta", account=account)
        else:
            self._open_bulk_edit_form(ids)

    def _open_account_form(self, title: str, account: dict | None) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedWidth(700)
        dlg.setModal(True)

        main_layout = QVBoxLayout(dlg)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(20, 14, 20, 14)

        # --- Tab button bar ---
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)
        stack = QStackedWidget()

        tab_btn_style = (
            "QPushButton {{ background: {bg}; color: {fg}; border: none; "
            "padding: 8px 20px; font-size: 10pt; font-weight: bold; "
            "border-bottom: 2px solid {border}; }}"
        )
        tab_buttons: list[QPushButton] = []
        tab_names = ["Conta", "Conexao", "Cronograma", "Categorias", "Extras"]

        def _switch_tab(index: int) -> None:
            stack.setCurrentIndex(index)
            for i, btn in enumerate(tab_buttons):
                if i == index:
                    btn.setStyleSheet(tab_btn_style.format(
                        bg=BG_SECONDARY, fg="#ffffff", border=ACCENT))
                else:
                    btn.setStyleSheet(tab_btn_style.format(
                        bg=BG_DARK, fg=FG_MUTED, border="transparent"))

        for i, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, idx=i: _switch_tab(idx))
            tab_buttons.append(btn)
            tab_bar.addWidget(btn)

        main_layout.addLayout(tab_bar)
        main_layout.addWidget(stack)

        # ====================== PAGE 0: Conta ======================
        page_account = QWidget()
        pa_layout = QVBoxLayout(page_account)
        pa_layout.setContentsMargins(16, 16, 16, 16)
        pa_layout.setSpacing(10)

        pa_layout.addWidget(QLabel("Usuario (sem @):"))
        ent_user = QLineEdit()
        if account:
            ent_user.setText(account.get("username", ""))
        pa_layout.addWidget(ent_user)

        pa_layout.addWidget(QLabel("Notas:"))
        txt_notes = QPlainTextEdit()
        txt_notes.setMaximumHeight(90)
        if account and account.get("notes"):
            txt_notes.setPlainText(account["notes"])
        pa_layout.addWidget(txt_notes)

        pa_layout.addStretch()
        stack.addWidget(page_account)

        # ====================== PAGE 1: Conexao ======================
        page_conn = QWidget()
        pc_layout = QVBoxLayout(page_conn)
        pc_layout.setContentsMargins(16, 16, 16, 16)
        pc_layout.setSpacing(10)

        pc_layout.addWidget(QLabel("Arquivo de Cookies (.json / .txt):"))
        cookie_row = QHBoxLayout()
        ent_cookie = QLineEdit()
        cookie_row.addWidget(ent_cookie)

        def browse_cookies():
            path, _ = QFileDialog.getOpenFileName(
                dlg,
                "Selecionar arquivo de cookies",
                "",
                "JSON (*.json);;Netscape TXT (*.txt);;Todos (*.*)",
            )
            if path:
                ent_cookie.setText(path)

        btn_browse = QPushButton("Procurar...")
        btn_browse.clicked.connect(browse_cookies)
        cookie_row.addWidget(btn_browse)
        pc_layout.addLayout(cookie_row)

        pc_layout.addSpacing(8)
        pc_layout.addWidget(QLabel("Proxy (opcional):"))
        ent_proxy = QLineEdit()
        if account and account.get("proxy"):
            ent_proxy.setText(account["proxy"])
        pc_layout.addWidget(ent_proxy)

        from gui.proxy_tester import create_proxy_test_row
        pc_layout.addWidget(create_proxy_test_row(ent_proxy))

        pc_layout.addStretch()
        stack.addWidget(page_conn)

        # ====================== PAGE 2: Cronograma ======================
        page_sched = QWidget()
        ps_layout = QVBoxLayout(page_sched)
        ps_layout.setContentsMargins(16, 16, 16, 16)
        ps_layout.setSpacing(10)

        ps_layout.addWidget(QLabel("Cronograma:"))
        schedule_names = self._get_schedule_names()
        schedule_list = list(schedule_names.values()) or ["Padrao"]
        schedule_ids = list(schedule_names.keys()) or [1]
        combo_sched = QComboBox()
        combo_sched.addItems(schedule_list)
        if account:
            sid = account.get("schedule_id", 1)
            idx = schedule_ids.index(sid) if sid in schedule_ids else 0
            combo_sched.setCurrentIndex(idx)
        elif schedule_list:
            combo_sched.setCurrentIndex(0)
        ps_layout.addWidget(combo_sched)

        ps_layout.addSpacing(12)
        ps_layout.addWidget(QLabel("Perfil de rolagem:"))
        scroll_preset_names = ["Padrao Global", "Lento", "Normal", "Rapido", "Super Rapido", "Ultra Rapido"]
        combo_scroll = QComboBox()
        combo_scroll.addItems(scroll_preset_names)

        if account and account.get("scroll_config"):
            try:
                acct_cfg = (
                    json.loads(account["scroll_config"])
                    if isinstance(account["scroll_config"], str)
                    else account["scroll_config"]
                )
            except (json.JSONDecodeError, TypeError):
                acct_cfg = None
            matched = False
            if acct_cfg:
                for pname, pdata in SCROLL_PRESETS.items():
                    ref = pdata if pdata else DEFAULT_SCROLL_CONFIG
                    if acct_cfg == ref:
                        combo_scroll.setCurrentText(pname)
                        matched = True
                        break
                if not matched:
                    if acct_cfg == DEFAULT_SCROLL_CONFIG:
                        combo_scroll.setCurrentText("Normal")
                    else:
                        combo_scroll.addItem("Personalizado")
                        combo_scroll.setCurrentText("Personalizado")
            else:
                combo_scroll.setCurrentText("Padrao Global")
        else:
            combo_scroll.setCurrentText("Padrao Global")

        ps_layout.addWidget(combo_scroll)
        ps_layout.addStretch()
        stack.addWidget(page_sched)

        # ====================== PAGE 3: Categorias ======================
        page_cats = QWidget()
        pcat_layout = QVBoxLayout(page_cats)
        pcat_layout.setContentsMargins(16, 16, 16, 16)
        pcat_layout.setSpacing(10)

        pcat_layout.addWidget(QLabel("Categorias (Ctrl+clique para multiplas):"))
        cat_names = self.app.category_manager.get_category_names()
        cat_list = list(cat_names.values())
        cat_ids = list(cat_names.keys())

        cat_listwidget = QListWidget()
        cat_listwidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        cat_listwidget.addItems(cat_list)

        if account:
            existing_cats = set(self.app.category_manager.get_account_categories(account["id"]))
            for i, cid in enumerate(cat_ids):
                if cid in existing_cats:
                    cat_listwidget.item(i).setSelected(True)

        pcat_layout.addWidget(cat_listwidget)
        stack.addWidget(page_cats)

        # ====================== PAGE 4: Extras ======================
        page_extras = QWidget()
        pe_layout = QVBoxLayout(page_extras)
        pe_layout.setContentsMargins(16, 16, 16, 16)
        pe_layout.setSpacing(10)
        pe_layout.addWidget(QLabel("Nenhuma configuracao extra disponivel no momento."))
        pe_layout.addStretch()
        stack.addWidget(page_extras)

        # Select first tab
        _switch_tab(0)

        # --- Save button ---
        def save():
            username = ent_user.text().strip().lstrip("@")
            if not username:
                QMessageBox.critical(dlg, "Erro", "O nome de usuario e obrigatorio.")
                return

            proxy = ent_proxy.text().strip() or None
            sched_idx = combo_sched.currentIndex()
            sched_id = schedule_ids[sched_idx] if sched_idx >= 0 else 1
            notes = txt_notes.toPlainText().strip()

            scroll_choice = combo_scroll.currentText()
            if scroll_choice == "Padrao Global":
                scroll_config_json = None
            elif scroll_choice == "Personalizado":
                scroll_config_json = account.get("scroll_config") if account else None
            else:
                preset_data = SCROLL_PRESETS.get(scroll_choice)
                scroll_config_json = json.dumps(preset_data if preset_data else DEFAULT_SCROLL_CONFIG)

            selected_cat_ids = [cat_ids[i] for i in range(cat_listwidget.count()) if cat_listwidget.item(i).isSelected()]

            if account:
                updates = {
                    "username": username,
                    "proxy": proxy,
                    "schedule_id": sched_id,
                    "scroll_config": scroll_config_json,
                    "notes": notes,
                }
                cookie_path = ent_cookie.text().strip()
                if cookie_path:
                    cookies = self._load_cookies(cookie_path)
                    if cookies is not None:
                        updates["cookies_json"] = cookies
                self.app.account_manager.update_account(account["id"], **updates)
                self.app.category_manager.set_account_categories(account["id"], selected_cat_ids)
                self.app.set_status(f"Conta @{username} atualizada")
            else:
                cookie_path = ent_cookie.text().strip()
                if not cookie_path:
                    QMessageBox.critical(dlg, "Erro", "Selecione o arquivo de cookies.")
                    return
                cookies = self._load_cookies(cookie_path)
                if cookies is None:
                    QMessageBox.critical(dlg, "Erro", "Falha ao carregar cookies.")
                    return
                new_id = self.app.account_manager.add_account(
                    username=username,
                    cookies_json=cookies,
                    proxy=proxy,
                    schedule_id=sched_id,
                    start_date=date.today().isoformat(),
                )
                if scroll_config_json is not None:
                    self.app.account_manager.update_account(new_id, scroll_config=scroll_config_json)
                if selected_cat_ids:
                    self.app.category_manager.set_account_categories(new_id, selected_cat_ids)
                self.app.set_status(f"Conta @{username} adicionada")

            dlg.accept()
            self.refresh()

        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("accent")
        btn_save.clicked.connect(save)
        main_layout.addWidget(btn_save)

        dlg.exec()

    # ==================================================================
    # Bulk edit
    # ==================================================================

    def _open_bulk_edit_form(self, account_ids: list[int]) -> None:
        """Edit shared fields across multiple accounts at once."""
        count = len(account_ids)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Editar {count} Contas")
        dlg.setFixedSize(460, 480)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        lbl_heading = QLabel(f"Editando {count} contas simultaneamente")
        lbl_heading.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(lbl_heading)

        layout.addWidget(QLabel(
            "Apenas os campos alterados serao aplicados.\n"
            "Deixe em branco ou no padrao para nao alterar."
        ))

        # Proxy
        layout.addWidget(QLabel("Proxy (deixe vazio para nao alterar):"))
        ent_proxy = QLineEdit()
        layout.addWidget(ent_proxy)

        from gui.proxy_tester import create_proxy_test_row
        layout.addWidget(create_proxy_test_row(ent_proxy))

        # Schedule
        layout.addWidget(QLabel("Cronograma:"))
        schedule_names = self._get_schedule_names()
        schedule_list = ["\u2014 Nao alterar \u2014"] + list(schedule_names.values())
        schedule_ids: list[int | None] = [None] + list(schedule_names.keys())
        combo_sched = QComboBox()
        combo_sched.addItems(schedule_list)
        combo_sched.setCurrentIndex(0)
        layout.addWidget(combo_sched)

        # Categories
        layout.addWidget(QLabel("Categorias (selecione para SUBSTITUIR, vazio = nao alterar):"))
        cat_names = self.app.category_manager.get_category_names()
        cat_list = list(cat_names.values())
        cat_ids = list(cat_names.keys())

        cat_listwidget = QListWidget()
        cat_listwidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        cat_listwidget.setMaximumHeight(90)
        cat_listwidget.addItems(cat_list)
        layout.addWidget(cat_listwidget)

        # Scroll config
        layout.addWidget(QLabel("Perfil de rolagem:"))
        scroll_options = ["\u2014 Nao alterar \u2014", "Padrao Global", "Lento", "Normal", "Rapido", "Super Rapido", "Ultra Rapido"]
        combo_scroll = QComboBox()
        combo_scroll.addItems(scroll_options)
        combo_scroll.setCurrentIndex(0)
        layout.addWidget(combo_scroll)

        # Notes
        layout.addWidget(QLabel("Notas (deixe vazio para nao alterar):"))
        txt_notes = QPlainTextEdit()
        txt_notes.setMaximumHeight(72)
        layout.addWidget(txt_notes)

        def save():
            updates: dict = {}
            changed = 0

            # Proxy
            proxy_val = ent_proxy.text().strip()
            if proxy_val:
                updates["proxy"] = proxy_val
                changed += 1

            # Schedule
            sched_idx = combo_sched.currentIndex()
            sched_id = schedule_ids[sched_idx]
            if sched_id is not None:
                updates["schedule_id"] = sched_id
                changed += 1

            # Scroll config
            scroll_choice = combo_scroll.currentText()
            if scroll_choice != "\u2014 Nao alterar \u2014":
                if scroll_choice == "Padrao Global":
                    updates["scroll_config"] = None
                else:
                    preset_data = SCROLL_PRESETS.get(scroll_choice)
                    updates["scroll_config"] = json.dumps(preset_data if preset_data else DEFAULT_SCROLL_CONFIG)
                changed += 1

            # Notes
            notes_val = txt_notes.toPlainText().strip()
            if notes_val:
                updates["notes"] = notes_val
                changed += 1

            # Categories
            selected_cat_ids = [cat_ids[i] for i in range(cat_listwidget.count()) if cat_listwidget.item(i).isSelected()]
            cat_changed = len(selected_cat_ids) > 0

            if changed == 0 and not cat_changed:
                QMessageBox.information(dlg, "Info", "Nenhum campo foi alterado.")
                return

            for aid in account_ids:
                if updates:
                    self.app.account_manager.update_account(aid, **updates)
                if cat_changed:
                    self.app.category_manager.set_account_categories(aid, selected_cat_ids)

            fields = []
            if "proxy" in updates:
                fields.append("proxy")
            if "schedule_id" in updates:
                fields.append("cronograma")
            if "scroll_config" in updates:
                fields.append("rolagem")
            if "notes" in updates:
                fields.append("notas")
            if cat_changed:
                fields.append("categorias")

            dlg.accept()
            self.refresh()
            self.app.set_status(f"{count} conta(s) atualizadas ({', '.join(fields)})")

        layout.addStretch()
        btn_apply = QPushButton("Aplicar a Todas")
        btn_apply.setObjectName("accent")
        btn_apply.clicked.connect(save)
        layout.addWidget(btn_apply)

        dlg.exec()

    # ==================================================================
    # Actions
    # ==================================================================

    def _open_profile(self) -> None:
        """Open selected accounts' Twitter/X profiles in the browser."""
        selected_rows = {idx.row() for idx in self._table.selectionModel().selectedRows()}
        if not selected_rows:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas.")
            return
        for row in selected_rows:
            # Column 0 shows "@username" — strip the leading "@"
            item = self._table.item(row, 0)
            if item is not None:
                username = item.text().lstrip("@")
                if username:
                    webbrowser.open(f"https://x.com/{username}")

    def _toggle_active(self) -> None:
        """Toggle status between idle and paused for selected accounts."""
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas.")
            return
        toggled = 0
        for aid in ids:
            acc = self.app.account_manager.get_account(aid)
            if acc is None:
                continue
            current = acc.get("status", "idle")
            if current in ("idle", "error", "completed"):
                self.app.account_manager.update_status(aid, "paused")
                toggled += 1
            elif current == "paused":
                self.app.account_manager.update_status(aid, "idle")
                toggled += 1
        self.app.set_status(f"{toggled} conta(s) alternada(s)")
        self.refresh()

    def _reset_schedule(self) -> None:
        """Reset selected accounts' schedules to day 1 (today)."""
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas.")
            return
        count = len(ids)
        msg = (
            f"Reiniciar cronograma de {count} conta(s)?\n\n"
            "Isso vai:\n"
            "- Definir a data de inicio como hoje\n"
            "- Resetar o dia atual para 1\n"
            "- Limpar o historico de acoes\n\n"
            "Tem certeza?"
        )
        reply = QMessageBox.question(self, "Reiniciar Cronograma", msg)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for aid in ids:
            self.app.account_manager.reset_schedule(aid)
        self.app.set_status(f"Cronograma reiniciado para {count} conta(s)")
        self.refresh()

    def _delete_account(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas para excluir.")
            return
        count = len(ids)
        msg = f"Excluir {count} conta(s) selecionada(s)?" if count > 1 else "Excluir esta conta?"
        reply = QMessageBox.question(self, "Confirmar", msg)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for aid in ids:
            self.app.account_manager.delete_account(aid)
        self.app.set_status(f"{count} conta(s) excluida(s)")
        self.refresh()

    def _import_cookies(self) -> None:
        """Import cookies from a file and assign to selected accounts."""
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione uma ou mais contas para importar cookies.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de cookies",
            "",
            "JSON (*.json);;Netscape TXT (*.txt);;Todos (*.*)",
        )
        if not path:
            return

        cookies = self._load_cookies(path)
        if cookies is None:
            QMessageBox.critical(self, "Erro", "Falha ao carregar cookies do arquivo.")
            return

        for aid in ids:
            self.app.account_manager.update_account(aid, cookies_json=cookies)
        self.app.set_status(f"Cookies importados para {len(ids)} conta(s)")
        self.refresh()

    # ==================================================================
    # Bulk import
    # ==================================================================

    def _bulk_import(self) -> None:
        """Import multiple accounts at once from multiple JSON cookie files.

        Each file becomes one account. The username is derived from the filename.
        """
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos de cookies (multiplos)",
            "",
            "JSON files (*.json);;Todos (*.*)",
        )
        if not file_paths:
            return

        from pathlib import Path

        successes = []
        failures = []

        # Get existing usernames to check duplicates
        existing = {
            acc["username"]
            for acc in self.app.account_manager.get_all_accounts()
        }

        for fp in file_paths:
            path = Path(fp)
            filename = path.name
            username = path.stem

            if not username:
                failures.append((filename, "Nome de arquivo vazio"))
                continue

            if username in existing:
                failures.append((filename, "Conta ja existente"))
                continue

            cookies = self._load_cookies(fp)
            if cookies is None:
                failures.append((filename, "Falha ao carregar cookies"))
                continue

            try:
                self.app.account_manager.add_account(
                    username=username,
                    cookies_json=cookies,
                    start_date=date.today().isoformat(),
                )
                existing.add(username)
                successes.append(username)
            except Exception as e:
                failures.append((filename, f"Erro no banco: {e}"))

        # Build summary
        lines = [f"Sucesso: {len(successes)} conta(s)"]
        if failures:
            lines.append(f"Falha: {len(failures)} arquivo(s)\n")
            lines.append("Erros:")
            for fname, err in failures:
                lines.append(f"  - {fname}: {err}")

        QMessageBox.information(self, "Importacao em Massa", "\n".join(lines))
        self.app.set_status(f"{len(successes)} conta(s) importada(s)")
        self.refresh()

    # ==================================================================
    # Category management dialog
    # ==================================================================

    def _manage_categories(self) -> None:
        """Open a dialog to create and delete categories."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Gerenciar Categorias")
        dlg.setFixedSize(380, 400)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        lbl_heading = QLabel("Categorias")
        lbl_heading.setStyleSheet("font-size: 13pt; font-weight: bold;")
        lbl_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_heading)

        # Listbox
        cat_listwidget = QListWidget()
        layout.addWidget(cat_listwidget, stretch=1)

        def refresh_list():
            cat_listwidget.clear()
            for cat in self.app.category_manager.get_all_categories():
                cat_listwidget.addItem(cat["name"])

        refresh_list()

        # Add section
        add_row = QHBoxLayout()
        ent_name = QLineEdit()
        ent_name.setPlaceholderText("Nome da categoria...")
        add_row.addWidget(ent_name)

        def on_add():
            name = ent_name.text().strip()
            if not name:
                return
            try:
                self.app.category_manager.add_category(name)
                ent_name.clear()
                refresh_list()
            except Exception:
                QMessageBox.critical(dlg, "Erro", "Categoria ja existe ou nome invalido.")

        btn_add = QPushButton("Adicionar")
        btn_add.setObjectName("accent")
        btn_add.clicked.connect(on_add)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # Delete button
        def on_delete():
            items = cat_listwidget.selectedItems()
            if not items:
                return
            selected_name = items[0].text()
            cats = self.app.category_manager.get_all_categories()
            cat = next((c for c in cats if c["name"] == selected_name), None)
            if cat is None:
                refresh_list()
                return
            reply = QMessageBox.question(dlg, "Confirmar", f"Excluir categoria '{cat['name']}'?")
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.app.category_manager.delete_category(cat["id"])
            refresh_list()

        btn_del = QPushButton("Excluir Selecionada")
        btn_del.setObjectName("danger")
        btn_del.clicked.connect(on_delete)
        layout.addWidget(btn_del)

        dlg.finished.connect(lambda _: self.refresh())
        dlg.exec()

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _load_cookies(filepath: str) -> str | None:
        """Load cookies from a JSON or Netscape TXT file.

        Returns the cookies as a JSON string, or None on failure.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # Try JSON first
            if content.startswith("[") or content.startswith("{"):
                data = json.loads(content)
                return json.dumps(data)

            # Netscape/Mozilla cookie TXT format
            cookies = []
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies.append({
                        "domain": parts[0],
                        "httpOnly": parts[1].upper() == "TRUE",
                        "path": parts[2],
                        "secure": parts[3].upper() == "TRUE",
                        "expiry": int(parts[4]) if parts[4].isdigit() else 0,
                        "name": parts[5],
                        "value": parts[6],
                    })
            if cookies:
                return json.dumps(cookies)

            return None
        except Exception:
            return None

    @staticmethod
    def _status_label(status: str) -> str:
        mapping = {
            "running": "Rodando",
            "paused": "Pausado",
            "error": "Erro",
            "idle": "Parado",
            "completed": "Concluido",
        }
        return mapping.get(status, status.capitalize())
