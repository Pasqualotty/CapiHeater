"""
TargetsTab - CRUD interface for managing target accounts/URLs.
"""

import json
import re
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui.base import BaseTab, SortableItem


# Priority int <-> label mapping
PRIORITY_LABELS = {1: "Baixa", 2: "Media", 3: "Alta"}
PRIORITY_VALUES = {"Baixa": 1, "Media": 2, "Alta": 3}


class TargetsTab(BaseTab):
    """Targets management tab with table and CRUD dialogs.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._all_targets = []
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        heading = QLabel("Gerenciamento de Alvos")
        heading.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        toolbar.addWidget(heading)
        toolbar.addStretch()

        btn_add = QPushButton("Adicionar Alvo")
        btn_add.clicked.connect(self._add_dialog)
        toolbar.addWidget(btn_add)

        btn_bulk = QPushButton("Adicionar em Massa")
        btn_bulk.clicked.connect(self._add_bulk_dialog)
        toolbar.addWidget(btn_bulk)

        btn_edit = QPushButton("Editar")
        btn_edit.clicked.connect(self._edit_dialog)
        toolbar.addWidget(btn_edit)

        btn_del = QPushButton("Excluir")
        btn_del.setObjectName("danger")
        btn_del.clicked.connect(self._delete_targets)
        toolbar.addWidget(btn_del)

        btn_toggle = QPushButton("Alternar Ativo")
        btn_toggle.clicked.connect(self._toggle_active)
        toolbar.addWidget(btn_toggle)

        btn_profile = QPushButton("Abrir Perfil")
        btn_profile.clicked.connect(self._open_profile)
        toolbar.addWidget(btn_profile)

        btn_cats = QPushButton("Categorias")
        btn_cats.clicked.connect(self._manage_categories)
        toolbar.addWidget(btn_cats)

        btn_export = QPushButton("Exportar")
        btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(btn_export)

        btn_import = QPushButton("Importar")
        btn_import.clicked.connect(self._on_import)
        toolbar.addWidget(btn_import)

        layout.addLayout(toolbar)

        # ---------- Search bar ----------
        search_layout = QHBoxLayout()
        search_layout.setSpacing(6)

        search_layout.addWidget(QLabel("Pesquisar:"))
        self._search_edit = QLineEdit()
        self._search_edit.setFixedWidth(160)
        self._search_edit.textChanged.connect(self._filter_table)
        search_layout.addWidget(self._search_edit)

        search_layout.addWidget(QLabel("Categoria:"))
        self._cat_filter_combo = QComboBox()
        self._cat_filter_combo.setFixedWidth(140)
        self._cat_filter_combo.currentIndexChanged.connect(self._filter_table)
        search_layout.addWidget(self._cat_filter_combo)

        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(self._clear_filters)
        search_layout.addWidget(btn_clear)

        search_layout.addStretch()
        layout.addLayout(search_layout)

        # ---------- Table ----------
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Usuario", "URL", "Prioridade", "Categoria", "Acoes", "Ativo"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 140)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 120)
        self._table.setColumnWidth(4, 100)
        self._table.setColumnWidth(5, 60)

        # Double-click opens profile
        self._table.doubleClicked.connect(self._open_profile)
        # Right-click context menu
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        # Selection changed
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setSortingEnabled(True)
        header.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self._table)

        # Ctrl+A shortcut (stored to prevent GC)
        self._shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), self._table)
        self._shortcut_select_all.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._shortcut_select_all.activated.connect(self._select_all)

        # Selection info bar
        self._sel_info = QLabel("")
        layout.addWidget(self._sel_info)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self):
        targets = self.app.target_manager.get_targets(active_only=False)
        cat_mgr = self.app.category_manager

        self._all_targets = []
        for t in targets:
            priority_label = PRIORITY_LABELS.get(t.get("priority", 1), "Baixa")
            active_label = "Sim" if t.get("active", 1) else "Nao"
            cat_names = cat_mgr.get_target_category_names(t["id"])
            cat_label = ", ".join(cat_names) if cat_names else "\u2014"
            # Build compact actions label
            parts = []
            if t.get("action_like", 1):
                parts.append("L" if not t.get("like_latest_post", 0) else "L*")
            if t.get("action_follow", 1):
                parts.append("F")
            if t.get("action_retweet", 1):
                parts.append("RT" if not t.get("rt_latest_post", 0) else "RT*")
            if t.get("action_comment_like", 1):
                parts.append("C")
            actions_label = " ".join(parts) if parts else "\u2014"
            self._all_targets.append({
                "id": t["id"],
                "url": t.get("url", ""),
                "cat_names": cat_names,
                "values": (
                    f"@{t.get('username', '???')}",
                    t.get("url", ""),
                    priority_label,
                    cat_label,
                    actions_label,
                    active_label,
                ),
            })

        # Update category filter combo
        all_cats = sorted({n for item in self._all_targets for n in item["cat_names"]})
        current = self._cat_filter_combo.currentText()
        self._cat_filter_combo.blockSignals(True)
        self._cat_filter_combo.clear()
        self._cat_filter_combo.addItems(["Todas", "Sem categoria"] + all_cats)
        idx = self._cat_filter_combo.findText(current)
        self._cat_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._cat_filter_combo.blockSignals(False)

        self._filter_table()

    def _clear_filters(self):
        self._search_edit.clear()
        self._cat_filter_combo.setCurrentIndex(0)

    def _filter_table(self):
        """Apply search and category filters and repopulate the table."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        query = self._search_edit.text().strip().lower()
        cat_filter = self._cat_filter_combo.currentText()
        shown = 0

        # col indices: 0=Usuario, 1=URL, 2=Prioridade, 3=Categoria, 4=Acoes, 5=Ativo
        for item in self._all_targets:
            username = item["values"][0].lower()
            if query and query not in username:
                continue
            if cat_filter == "Sem categoria" and item["cat_names"]:
                continue
            if cat_filter not in ("Todas", "Sem categoria") and cat_filter not in item["cat_names"]:
                continue

            row = self._table.rowCount()
            self._table.insertRow(row)

            for col, text in enumerate(item["values"]):
                if col == 2:
                    # Prioridade: sort by numeric value stored in PRIORITY_VALUES
                    prio_int = PRIORITY_VALUES.get(text, 1)
                    cell = SortableItem(text, sort_key=prio_int)
                else:
                    cell = SortableItem(text)
                if col in (2, 3, 4, 5):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setData(Qt.ItemDataRole.UserRole, item["id"])
                self._table.setItem(row, col, cell)

            shown += 1

        self._table.setSortingEnabled(True)

        total = len(self._all_targets)
        if query or cat_filter != "Todas":
            self._sel_info.setText(f"{shown}/{total} alvos encontrados")
        else:
            self._sel_info.setText(
                f"{total} alvos | Ctrl+A = selecionar todos | Duplo clique = abrir perfil"
            )

    def _get_selected_ids(self):
        """Return list of selected target IDs."""
        ids = []
        for idx in self._table.selectionModel().selectedRows():
            item = self._table.item(idx.row(), 0)
            if item is not None:
                tid = item.data(Qt.ItemDataRole.UserRole)
                if tid is not None:
                    ids.append(tid)
        return ids

    def _get_selected_id(self):
        ids = self._get_selected_ids()
        return ids[0] if ids else None

    def _on_selection_changed(self):
        count = len(self._table.selectionModel().selectedRows())
        if count == 0:
            self._sel_info.setText("Nenhum selecionado")
        elif count == 1:
            self._sel_info.setText("1 alvo selecionado")
        else:
            self._sel_info.setText(f"{count} alvos selecionados")

    def _select_all(self):
        self._table.selectAll()

    # ==================================================================
    # Context menu
    # ==================================================================

    def _show_context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if idx.isValid():
            row = idx.row()
            if row not in {i.row() for i in self._table.selectionModel().selectedRows()}:
                self._table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("Abrir Perfil", self._open_profile)
        menu.addSeparator()
        menu.addAction("Editar", self._edit_dialog)
        menu.addAction("Alternar Ativo", self._toggle_active)
        menu.addSeparator()
        menu.addAction("Excluir Selecionados", self._delete_targets)
        menu.addSeparator()
        menu.addAction("Selecionar Todos", self._select_all)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    # ==================================================================
    # Bulk add dialog
    # ==================================================================

    def _add_bulk_dialog(self):
        """Open a dialog to add multiple targets at once via links or usernames."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Adicionar Alvos em Massa")
        dlg.resize(500, 520)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(8)

        title = QLabel("Adicionar Alvos em Massa")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Cole links ou usernames (um por linha):"))

        # Text area
        bulk_text = QPlainTextEdit()
        layout.addWidget(bulk_text, 1)

        # Example hint
        hint = QLabel(
            "Exemplos aceitos:\n"
            "https://x.com/usuario\n"
            "https://twitter.com/usuario\n"
            "@usuario\n"
            "usuario"
        )
        hint.setStyleSheet("color: #666688; font-size: 8pt;")
        layout.addWidget(hint)

        # Priority row
        opts_layout = QHBoxLayout()
        opts_layout.addWidget(QLabel("Prioridade:"))
        prio_combo = QComboBox()
        prio_combo.addItems(["Baixa", "Media", "Alta"])
        prio_combo.setCurrentText("Alta")
        prio_combo.setFixedWidth(100)
        opts_layout.addWidget(prio_combo)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # Categories (multi-select listbox)
        layout.addWidget(QLabel("Categorias (Ctrl+clique para multiplas):"))

        cat_names_map = self.app.category_manager.get_category_names()
        cat_list = list(cat_names_map.values())
        cat_ids = list(cat_names_map.keys())

        bulk_cat_listbox = QListWidget()
        bulk_cat_listbox.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        bulk_cat_listbox.setMaximumHeight(100)
        bulk_cat_listbox.addItems(cat_list)
        layout.addWidget(bulk_cat_listbox)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton("Adicionar Todos")
        btn_ok.setObjectName("accent")
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dlg.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        def on_add():
            raw = bulk_text.toPlainText().strip()
            if not raw:
                QMessageBox.warning(dlg, "Aviso", "Cole pelo menos um link ou username.")
                return

            priority = PRIORITY_VALUES.get(prio_combo.currentText(), 3)
            selected_cat_ids = [
                cat_ids[bulk_cat_listbox.row(item)]
                for item in bulk_cat_listbox.selectedItems()
            ]
            lines = [line.strip() for line in raw.splitlines() if line.strip()]

            added = 0
            skipped = 0
            for line in lines:
                username = self._extract_username(line)
                if not username:
                    skipped += 1
                    continue

                url = f"https://x.com/{username}"
                try:
                    new_id = self.app.target_manager.add_target(
                        username=username, url=url, priority=priority
                    )
                    if selected_cat_ids:
                        self.app.category_manager.set_target_categories(
                            new_id, selected_cat_ids
                        )
                    added += 1
                except Exception:
                    skipped += 1  # Probably duplicate

            dlg.accept()
            self.refresh()
            self.app.set_status(f"{added} alvo(s) adicionado(s), {skipped} ignorado(s)")
            QMessageBox.information(
                self,
                "Resultado",
                f"{added} alvo(s) adicionado(s) com sucesso!\n"
                f"{skipped} ignorado(s) (duplicados ou invalidos).",
            )

        btn_ok.clicked.connect(on_add)
        dlg.exec()

    @staticmethod
    def _extract_username(text):
        """Extract a Twitter username from a URL or raw text."""
        text = text.strip().rstrip("/")

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

        # Match plain username (letters, numbers, underscores only)
        match = re.match(r'^([\w]+)$', text)
        if match and len(text) <= 30:
            return match.group(1)

        return None

    # ==================================================================
    # Dialogs
    # ==================================================================

    def _add_dialog(self):
        self._open_target_form(title="Adicionar Alvo", target=None)

    def _edit_dialog(self):
        tid = self._get_selected_id()
        if tid is None:
            QMessageBox.warning(self, "Aviso", "Selecione um alvo para editar.")
            return
        target = self.app.target_manager.get_target(tid)
        if target is None:
            return
        self._open_target_form(title="Editar Alvo", target=target)

    def _open_target_form(self, title, target):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(480, 520)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # Username
        layout.addWidget(QLabel("Usuario alvo (sem @):"))
        ent_user = QLineEdit()
        layout.addWidget(ent_user)

        # URL
        layout.addWidget(QLabel("URL do perfil:"))
        ent_url = QLineEdit()
        layout.addWidget(ent_url)

        # Auto-fill URL from username on focus out
        def on_username_change():
            user = ent_user.text().strip().lstrip("@")
            if user and not ent_url.text().strip():
                ent_url.setText(f"https://x.com/{user}")

        ent_user.editingFinished.connect(on_username_change)

        # Priority
        layout.addWidget(QLabel("Prioridade:"))
        combo_prio = QComboBox()
        combo_prio.addItems(["Baixa", "Media", "Alta"])
        layout.addWidget(combo_prio)

        # --- Action flags ---
        layout.addSpacing(6)
        layout.addWidget(QLabel("Acoes permitidas:"))
        actions_row = QHBoxLayout()
        chk_like = QCheckBox("Like")
        chk_follow = QCheckBox("Follow")
        chk_retweet = QCheckBox("Retweet")
        chk_comment_like = QCheckBox("Like coment.")
        for chk in (chk_like, chk_follow, chk_retweet, chk_comment_like):
            chk.setChecked(True)
            actions_row.addWidget(chk)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        # Latest post options
        chk_like_latest = QCheckBox("Like na ultima postagem")
        chk_like_latest.setChecked(False)
        layout.addWidget(chk_like_latest)

        chk_rt_latest = QCheckBox("RT na ultima postagem")
        chk_rt_latest.setChecked(False)
        layout.addWidget(chk_rt_latest)

        # Categories (multi-select)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Categorias (Ctrl+clique para multiplas):"))
        cat_names = self.app.category_manager.get_category_names()
        cat_list = list(cat_names.values())
        cat_ids = list(cat_names.keys())

        cat_listbox = QListWidget()
        cat_listbox.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        cat_listbox.setMaximumHeight(100)
        cat_listbox.addItems(cat_list)
        layout.addWidget(cat_listbox)

        if target:
            ent_user.setText(target.get("username", ""))
            ent_url.setText(target.get("url", ""))
            prio_label = PRIORITY_LABELS.get(target.get("priority", 1), "Baixa")
            combo_prio.setCurrentText(prio_label)
            chk_like.setChecked(bool(target.get("action_like", 1)))
            chk_follow.setChecked(bool(target.get("action_follow", 1)))
            chk_retweet.setChecked(bool(target.get("action_retweet", 1)))
            chk_comment_like.setChecked(bool(target.get("action_comment_like", 1)))
            chk_rt_latest.setChecked(bool(target.get("rt_latest_post", 0)))
            chk_like_latest.setChecked(bool(target.get("like_latest_post", 0)))
            # Pre-select existing categories
            existing_cats = set(self.app.category_manager.get_target_categories(target["id"]))
            for i, cid in enumerate(cat_ids):
                if cid in existing_cats:
                    cat_listbox.item(i).setSelected(True)
        else:
            combo_prio.setCurrentIndex(0)

        # Save button
        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("accent")
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)

        def save():
            username = ent_user.text().strip().lstrip("@")
            url = ent_url.text().strip()
            if not username:
                QMessageBox.critical(dlg, "Erro", "O nome de usuario e obrigatorio.")
                return
            if not url:
                url = f"https://x.com/{username}"

            priority = PRIORITY_VALUES.get(combo_prio.currentText(), 1)
            action_flags = {
                "action_like": int(chk_like.isChecked()),
                "action_follow": int(chk_follow.isChecked()),
                "action_retweet": int(chk_retweet.isChecked()),
                "action_comment_like": int(chk_comment_like.isChecked()),
                "rt_latest_post": int(chk_rt_latest.isChecked()),
                "like_latest_post": int(chk_like_latest.isChecked()),
            }
            selected_cat_ids = [
                cat_ids[cat_listbox.row(item)]
                for item in cat_listbox.selectedItems()
            ]

            if target:
                self.app.target_manager.update_target(
                    target["id"], username=username, url=url, priority=priority,
                    **action_flags,
                )
                self.app.category_manager.set_target_categories(
                    target["id"], selected_cat_ids
                )
                self.app.set_status(f"Alvo @{username} atualizado")
            else:
                new_id = self.app.target_manager.add_target(
                    username=username, url=url, priority=priority, **action_flags,
                )
                if selected_cat_ids:
                    self.app.category_manager.set_target_categories(
                        new_id, selected_cat_ids
                    )
                self.app.set_status(f"Alvo @{username} adicionado")

            dlg.accept()
            self.refresh()

        btn_save.clicked.connect(save)
        dlg.exec()

    # ==================================================================
    # Category management dialog
    # ==================================================================

    def _manage_categories(self):
        """Open a dialog to create and delete categories."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Gerenciar Categorias")
        dlg.resize(380, 400)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        heading = QLabel("Categorias")
        heading.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        cat_listbox = QListWidget()
        layout.addWidget(cat_listbox, 1)

        def refresh_list():
            cat_listbox.clear()
            for cat in self.app.category_manager.get_all_categories():
                cat_listbox.addItem(cat["name"])

        refresh_list()

        # Add row
        add_layout = QHBoxLayout()
        ent_name = QLineEdit()
        ent_name.setPlaceholderText("Nova categoria...")
        add_layout.addWidget(ent_name)

        btn_add = QPushButton("Adicionar")
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        def on_add():
            name = ent_name.text().strip()
            if not name:
                return
            try:
                self.app.category_manager.add_category(name)
                ent_name.clear()
                refresh_list()
            except Exception:
                QMessageBox.critical(
                    dlg, "Erro", "Categoria ja existe ou nome invalido."
                )

        btn_add.clicked.connect(on_add)

        # Delete button
        btn_delete = QPushButton("Excluir Selecionada")
        btn_delete.setObjectName("danger")
        layout.addWidget(btn_delete)

        def on_delete():
            sel = cat_listbox.currentItem()
            if sel is None:
                return
            selected_name = sel.text()
            cats = self.app.category_manager.get_all_categories()
            cat = next((c for c in cats if c["name"] == selected_name), None)
            if cat is None:
                refresh_list()
                return
            reply = QMessageBox.question(
                dlg,
                "Confirmar",
                f"Excluir categoria '{cat['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.app.category_manager.delete_category(cat["id"])
            refresh_list()

        btn_delete.clicked.connect(on_delete)

        dlg.finished.connect(lambda: self.refresh())
        dlg.exec()

    # ==================================================================
    # Actions
    # ==================================================================

    def _open_profile(self):
        """Open selected profiles in the default browser."""
        rows = {idx.row() for idx in self._table.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.warning(self, "Aviso", "Selecione um ou mais alvos.")
            return
        for row in rows:
            # Column 1 holds the URL text directly.
            item = self._table.item(row, 1)
            if item is not None:
                url = item.text()
                if url:
                    webbrowser.open(url)

    def _delete_targets(self):
        """Delete all selected targets."""
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(
                self, "Aviso", "Selecione um ou mais alvos para excluir."
            )
            return

        count = len(ids)
        msg = f"Excluir {count} alvo(s) selecionado(s)?" if count > 1 else "Excluir este alvo?"
        reply = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for tid in ids:
            self.app.target_manager.delete_target(tid)

        self.app.set_status(f"{count} alvo(s) excluido(s)")
        self.refresh()

    def _toggle_active(self):
        """Toggle active status for all selected targets."""
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, "Aviso", "Selecione um ou mais alvos.")
            return

        for tid in ids:
            self.app.target_manager.toggle_active(tid)

        self.app.set_status(f"{len(ids)} alvo(s) alternado(s)")
        self.refresh()

    # ==================================================================
    # Export / Import
    # ==================================================================

    def _on_export(self) -> None:
        """Export all targets to a JSON file."""
        targets = self.app.target_manager.get_targets(active_only=False)
        if not targets:
            QMessageBox.warning(self, "Aviso", "Nenhum alvo para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Alvos", "alvos.json", "JSON (*.json)"
        )
        if not path:
            return

        export_list = []
        for t in targets:
            cat_names = self.app.category_manager.get_target_category_names(t["id"])
            export_list.append({
                "username": t.get("username", ""),
                "url": t.get("url", ""),
                "priority": t.get("priority", 1),
                "active": bool(t.get("active", 1)),
                "action_like": bool(t.get("action_like", 1)),
                "action_follow": bool(t.get("action_follow", 1)),
                "action_retweet": bool(t.get("action_retweet", 1)),
                "action_comment_like": bool(t.get("action_comment_like", 1)),
                "rt_latest_post": bool(t.get("rt_latest_post", 0)),
                "like_latest_post": bool(t.get("like_latest_post", 0)),
                "categories": cat_names,
            })

        export_data = {
            "capiheater_targets": True,
            "version": 1,
            "targets": export_list,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self, "Sucesso",
                f"{len(export_list)} alvo(s) exportado(s) com sucesso!"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Falha ao exportar:\n{exc}")

    def _on_import(self) -> None:
        """Import targets from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar Alvos", "", "JSON (*.json);;Todos (*.*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Falha ao ler arquivo:\n{exc}")
            return

        # Accept envelope format or raw array
        if isinstance(data, dict) and "targets" in data:
            targets = data["targets"]
        elif isinstance(data, list):
            targets = data
        else:
            QMessageBox.critical(
                self, "Erro",
                "Formato invalido. O arquivo deve conter alvos CapiHeater\n"
                "ou um array JSON de alvos.",
            )
            return

        if not targets or not isinstance(targets, list):
            QMessageBox.critical(self, "Erro", "Nenhum alvo encontrado no arquivo.")
            return

        # Get existing usernames to skip duplicates
        existing = {t.get("username", "").lower()
                    for t in self.app.target_manager.get_targets(active_only=False)}

        # Get all category names for auto-creation
        all_cats = self.app.category_manager.get_category_names()  # {id: name}
        cat_name_to_id = {name: cid for cid, name in all_cats.items()}

        added = 0
        skipped = 0
        for item in targets:
            if not isinstance(item, dict):
                continue
            username = item.get("username", "").strip().lstrip("@")
            if not username:
                continue
            if username.lower() in existing:
                skipped += 1
                continue

            url = item.get("url", f"https://x.com/{username}")
            priority = item.get("priority", 1)
            if priority not in (1, 2, 3):
                priority = 1

            tid = self.app.target_manager.add_target(
                username=username, url=url, priority=priority,
                action_like=int(item.get("action_like", True)),
                action_follow=int(item.get("action_follow", True)),
                action_retweet=int(item.get("action_retweet", True)),
                action_comment_like=int(item.get("action_comment_like", True)),
                rt_latest_post=int(item.get("rt_latest_post", False)),
                like_latest_post=int(item.get("like_latest_post", False)),
            )

            # Set active status
            if not item.get("active", True):
                self.app.target_manager.toggle_active(tid)

            # Handle categories
            cat_ids = []
            for cat_name in item.get("categories", []):
                if cat_name in cat_name_to_id:
                    cat_ids.append(cat_name_to_id[cat_name])
                else:
                    # Auto-create missing categories
                    new_id = self.app.category_manager.add_category(cat_name)
                    cat_name_to_id[cat_name] = new_id
                    cat_ids.append(new_id)
            if cat_ids:
                self.app.category_manager.set_target_categories(tid, cat_ids)

            existing.add(username.lower())
            added += 1

        msg = f"{added} alvo(s) importado(s)!"
        if skipped:
            msg += f"\n{skipped} duplicado(s) ignorado(s)."
        QMessageBox.information(self, "Sucesso", msg)
        self.refresh()
