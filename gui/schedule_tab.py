"""
ScheduleTab - Visualization and editing of warming schedules.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.base import BaseTab
from gui.theme import ACCENT, BG_DARK, BG_SECONDARY, FG_MUTED, FG_TEXT


class ScheduleTab(BaseTab):
    """Schedule management with view, edit, create, and delete.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._schedules: list[dict] = []
        self._filtered_schedules: list[dict] = []
        self._build_ui()
        self._load_schedules()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Header
        heading = QLabel("Gerenciar Cronogramas")
        heading.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(heading)

        # Search + Schedule selector row
        sel_layout = QHBoxLayout()
        sel_layout.setSpacing(6)

        sel_layout.addWidget(QLabel("Pesquisar:"))
        self._search_edit = QLineEdit()
        self._search_edit.setFixedWidth(160)
        self._search_edit.textChanged.connect(self._filter_schedules)
        sel_layout.addWidget(self._search_edit)

        sel_layout.addSpacing(12)
        sel_layout.addWidget(QLabel("Cronograma:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(220)
        self._combo.currentIndexChanged.connect(self._on_schedule_selected)
        sel_layout.addWidget(self._combo)

        self._info_label = QLabel("")
        self._info_label.setStyleSheet(f"color: {FG_MUTED};")
        sel_layout.addSpacing(12)
        sel_layout.addWidget(self._info_label)
        sel_layout.addStretch()

        layout.addLayout(sel_layout)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        for text, slot in [
            ("Novo Cronograma", self._on_new),
            ("Duplicar", self._on_duplicate),
            ("Exportar", self._on_export),
            ("Importar", self._on_import),
            ("Editar Dia", self._on_edit_day),
            ("Adicionar Dia", self._on_add_day),
            ("Duplicar Dia", self._on_duplicate_day),
            ("Remover Dia", self._on_remove_day),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()

        del_btn = QPushButton("Excluir Cronograma")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(del_btn)

        layout.addLayout(btn_layout)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "Dia", "Likes", "Likes Coment.", "Follows", "Retweets", "Unfollows",
            "Feed Antes (seg)", "Feed Entre (seg)", "Abrir Posts",
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(lambda _: self._on_edit_day())

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        for col in range(9):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table, stretch=1)

        # Tip
        tip = QLabel("Dica: clique duplo em um dia para editar. Alteracoes sao salvas automaticamente.")
        tip.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
        layout.addWidget(tip)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload schedules (called when tab becomes visible)."""
        self._load_schedules()

    def _load_schedules(self) -> None:
        """Populate the schedule dropdown from the database."""
        self._schedules = self.app.db.fetch_all(
            "SELECT id, name, description, schedule_json FROM schedules ORDER BY id"
        )
        self._filter_schedules()

    def _filter_schedules(self) -> None:
        """Filter the schedule dropdown based on the search text."""
        all_schedules = getattr(self, "_schedules", [])
        query = self._search_edit.text().strip().lower()

        if query:
            self._filtered_schedules = [
                s for s in all_schedules if query in s["name"].lower()
            ]
        else:
            self._filtered_schedules = list(all_schedules)

        # Block signals to avoid triggering _on_schedule_selected during rebuild
        self._combo.blockSignals(True)
        self._combo.clear()
        names = [s["name"] for s in self._filtered_schedules]
        self._combo.addItems(names)
        self._combo.blockSignals(False)

        if names:
            self._combo.setCurrentIndex(0)
            self._display_schedule(0)
        else:
            self._table.setRowCount(0)
            self._info_label.setText("")

    def _on_schedule_selected(self, idx: int = -1) -> None:
        if idx >= 0:
            self._display_schedule(idx)

    def _display_schedule(self, idx: int) -> None:
        """Show the day-by-day breakdown for the selected schedule."""
        self._table.setRowCount(0)

        filtered = getattr(self, "_filtered_schedules", self._schedules)
        if idx < 0 or idx >= len(filtered):
            return
        schedule = filtered[idx]
        self._info_label.setText(schedule.get("description", ""))

        days = self._parse_days(schedule)
        self._table.setRowCount(len(days))

        for row, entry in enumerate(days):
            bb_min = entry.get("browse_before_min", 0)
            bb_max = entry.get("browse_before_max", 0)
            bw_min = entry.get("browse_between_min", 0)
            bw_max = entry.get("browse_between_max", 0)

            browse_before_str = f"{bb_min}-{bb_max}" if (bb_min or bb_max) else "0"
            browse_between_str = f"{bw_min}-{bw_max}" if (bw_min or bw_max) else "0"

            values = [
                f"Dia {entry.get('day', '?')}",
                str(entry.get("likes", 0)),
                str(entry.get("comment_likes", 0)),
                str(entry.get("follows", 0)),
                str(entry.get("retweets", 0)),
                str(entry.get("unfollows", 0)),
                browse_before_str,
                browse_between_str,
                str(entry.get("posts_to_open", 0)),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

    def _parse_days(self, schedule: dict) -> list[dict]:
        raw = schedule.get("schedule_json", "[]")
        try:
            days = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            days = []
        return days if isinstance(days, list) else []

    def _current_schedule(self) -> dict | None:
        idx = self._combo.currentIndex()
        filtered = getattr(self, "_filtered_schedules", self._schedules)
        if idx < 0 or idx >= len(filtered):
            return None
        return filtered[idx]

    def _select_by_name(self, name: str) -> None:
        """Re-select a schedule by name in the (possibly filtered) combo."""
        for i, s in enumerate(self._filtered_schedules):
            if s["name"] == name:
                self._combo.setCurrentIndex(i)
                self._display_schedule(i)
                return

    def _save_schedule_days(self, schedule: dict, days: list[dict]) -> None:
        """Persist updated days to the database and refresh."""
        self.app.db.execute(
            "UPDATE schedules SET schedule_json = ? WHERE id = ?",
            (json.dumps(days), schedule["id"]),
        )
        self._load_schedules()
        self._select_by_name(schedule["name"])

    # ==================================================================
    # Actions
    # ==================================================================

    def _selected_day_str(self) -> str | None:
        """Return the day string of the currently selected table row, or None."""
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.text().replace("Dia ", "")

    def _on_edit_day(self) -> None:
        """Edit the selected day's values."""
        schedule = self._current_schedule()
        if not schedule:
            return

        day_str = self._selected_day_str()
        if day_str is None:
            QMessageBox.warning(self, "Aviso", "Selecione um dia para editar.")
            return

        days = self._parse_days(schedule)
        day_idx = None
        for i, d in enumerate(days):
            if str(d.get("day", "")) == day_str:
                day_idx = i
                break

        if day_idx is None:
            return

        day = days[day_idx]
        result = self._edit_day_dialog(day)
        if result:
            days[day_idx] = result
            self._save_schedule_days(schedule, days)

    def _on_add_day(self) -> None:
        """Add a new day at the end of the schedule."""
        schedule = self._current_schedule()
        if not schedule:
            return

        days = self._parse_days(schedule)
        next_day = max((d.get("day", 0) for d in days), default=0) + 1

        new_day = {
            "day": next_day, "likes": 0, "comment_likes": 0, "follows": 0, "retweets": 0, "unfollows": 0,
            "browse_before_min": 0, "browse_before_max": 0,
            "browse_between_min": 0, "browse_between_max": 0,
            "posts_to_open": 0, "view_comments_chance": 0.3,
            "likes_on_feed": False, "retweets_on_feed": False,
            "comment_likes_per_target": 3, "comment_like_skip_chance": 0.25,
            "follow_initial_count": 0,
        }
        result = self._edit_day_dialog(new_day)
        if result:
            days.append(result)
            self._save_schedule_days(schedule, days)

    def _on_duplicate_day(self) -> None:
        """Duplicate the selected day, inserting the copy right after it."""
        schedule = self._current_schedule()
        if not schedule:
            return

        day_str = self._selected_day_str()
        if day_str is None:
            QMessageBox.warning(self, "Aviso", "Selecione um dia para duplicar.")
            return

        days = self._parse_days(schedule)
        day_idx = None
        for i, d in enumerate(days):
            if str(d.get("day", "")) == day_str:
                day_idx = i
                break

        if day_idx is None:
            return

        new_day = dict(days[day_idx])
        days.insert(day_idx + 1, new_day)

        for i, d in enumerate(days):
            d["day"] = i + 1

        self._save_schedule_days(schedule, days)

    def _on_remove_day(self) -> None:
        """Remove the selected day."""
        schedule = self._current_schedule()
        if not schedule:
            return

        day_str = self._selected_day_str()
        if day_str is None:
            QMessageBox.warning(self, "Aviso", "Selecione um dia para remover.")
            return

        days = self._parse_days(schedule)
        days = [d for d in days if str(d.get("day", "")) != day_str]

        for i, d in enumerate(days):
            d["day"] = i + 1

        self._save_schedule_days(schedule, days)

    def _on_new(self) -> None:
        """Create a new empty schedule."""
        name, ok = QInputDialog.getText(self, "Novo Cronograma", "Nome do cronograma:")
        if not ok or not name or not name.strip():
            return

        desc, _ = QInputDialog.getText(self, "Novo Cronograma", "Descricao (opcional):")
        desc = desc or ""

        initial = [{"day": 1, "likes": 3, "follows": 0, "retweets": 0, "unfollows": 0}]

        self.app.db.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            (name.strip(), desc.strip(), json.dumps(initial)),
        )

        self._search_edit.clear()
        self._load_schedules()
        self._select_by_name(name.strip())

        QMessageBox.information(self, "Sucesso", f"Cronograma '{name.strip()}' criado!")

    def _on_duplicate(self) -> None:
        """Duplicate the current schedule."""
        schedule = self._current_schedule()
        if not schedule:
            return

        name, ok = QInputDialog.getText(
            self, "Duplicar Cronograma", "Nome para a copia:",
            text=f"{schedule['name']} (copia)",
        )
        if not ok or not name or not name.strip():
            return

        self.app.db.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            (name.strip(), schedule.get("description", ""), schedule.get("schedule_json", "[]")),
        )

        self._search_edit.clear()
        self._load_schedules()
        self._select_by_name(name.strip())

        QMessageBox.information(self, "Sucesso", f"Cronograma duplicado como '{name.strip()}'!")

    def _on_export(self) -> None:
        """Export the current schedule to a JSON file."""
        schedule = self._current_schedule()
        if not schedule:
            QMessageBox.warning(self, "Aviso", "Selecione um cronograma para exportar.")
            return

        suggested = f"{schedule['name']}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Cronograma", suggested, "JSON (*.json)"
        )
        if not path:
            return

        days = self._parse_days(schedule)
        export_data = {
            "capiheater_schedule": True,
            "version": 1,
            "name": schedule["name"],
            "description": schedule.get("description", ""),
            "days": days,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self, "Sucesso",
                f"Cronograma '{schedule['name']}' exportado com sucesso!"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Falha ao exportar:\n{exc}")

    def _on_import(self) -> None:
        """Import a schedule from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar Cronograma", "", "JSON (*.json);;Todos (*.*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Falha ao ler arquivo:\n{exc}")
            return

        # Accept envelope format or raw array of days
        if isinstance(data, dict) and "days" in data:
            days = data["days"]
            suggested_name = data.get("name", "")
            description = data.get("description", "")
        elif isinstance(data, list):
            days = data
            suggested_name = ""
            description = ""
        else:
            QMessageBox.critical(
                self, "Erro",
                "Formato invalido. O arquivo deve conter um cronograma CapiHeater\n"
                "ou um array JSON de dias.",
            )
            return

        # Validate days
        if not days or not isinstance(days, list):
            QMessageBox.critical(self, "Erro", "Nenhum dia encontrado no arquivo.")
            return

        required = {"day", "likes", "follows", "retweets", "unfollows"}
        for i, day in enumerate(days):
            if not isinstance(day, dict):
                QMessageBox.critical(self, "Erro", f"Dia {i+1} nao e um objeto valido.")
                return
            missing = required - set(day.keys())
            if missing:
                # Fill missing with defaults
                for key in missing:
                    day[key] = 0

        # Ask for name
        if not suggested_name:
            import os
            suggested_name = os.path.splitext(os.path.basename(path))[0]

        name, ok = QInputDialog.getText(
            self, "Importar Cronograma",
            "Nome para o cronograma importado:",
            text=suggested_name,
        )
        if not ok or not name or not name.strip():
            return

        # Insert into database
        self.app.db.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            (name.strip(), description, json.dumps(days)),
        )

        self._search_edit.clear()
        self._load_schedules()
        self._select_by_name(name.strip())

        QMessageBox.information(
            self, "Sucesso",
            f"Cronograma '{name.strip()}' importado com {len(days)} dia(s)!"
        )

    def _on_delete(self) -> None:
        """Delete the current schedule."""
        schedule = self._current_schedule()
        if not schedule:
            return

        if len(self._schedules) <= 1:
            QMessageBox.warning(self, "Aviso", "Nao e possivel excluir o unico cronograma.")
            return

        count = self.app.db.fetch_one(
            "SELECT COUNT(*) as c FROM accounts WHERE schedule_id = ?",
            (schedule["id"],),
        )
        if count and count.get("c", 0) > 0:
            QMessageBox.warning(
                self, "Aviso",
                f"Existem {count['c']} conta(s) usando este cronograma.\n"
                "Mude o cronograma dessas contas antes de excluir.",
            )
            return

        reply = QMessageBox.question(
            self, "Confirmar", f"Excluir cronograma '{schedule['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.app.db.execute("DELETE FROM schedules WHERE id = ?", (schedule["id"],))
        self._load_schedules()

    # ==================================================================
    # Edit dialog
    # ==================================================================

    def _edit_day_dialog(self, day: dict) -> dict | None:
        """Show a tabbed dialog to edit a single day's values. Returns updated dict or None."""
        dlg = QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle(f"Dia {day.get('day', '?')}")
        dlg.setFixedWidth(700)
        dlg.setStyleSheet(f"QDialog {{ background-color: {BG_DARK}; }}")

        main_layout = QVBoxLayout(dlg)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(8)

        # Title
        title = QLabel(f"Editar Dia {day.get('day', '?')}")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

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
        tab_names = ["Acoes", "Feed", "Comportamento"]

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

        spins: dict[str, QSpinBox] = {}
        hint_style = f"color: {FG_MUTED}; font-size: 8pt;"

        def _make_spin(key: str, val: int, max_val: int = 100, width: int = 80) -> QSpinBox:
            sp = QSpinBox()
            sp.setRange(0, max_val)
            sp.setValue(val)
            sp.setFixedWidth(width)
            spins[key] = sp
            return sp

        # ====================== PAGE 0: Acoes ======================
        page_actions = QWidget()
        pa_layout = QVBoxLayout(page_actions)
        pa_layout.setContentsMargins(16, 16, 16, 16)
        pa_layout.setSpacing(10)

        form_actions = QFormLayout()
        form_actions.setHorizontalSpacing(16)
        form_actions.setVerticalSpacing(10)
        for label_text, key in [("Likes:", "likes"), ("Likes coment.:", "comment_likes"),
                                ("Follows:", "follows"),
                                ("Retweets:", "retweets"), ("Unfollows:", "unfollows")]:
            form_actions.addRow(label_text, _make_spin(key, day.get(key, 0)))
        pa_layout.addLayout(form_actions)

        variation_hint = QLabel(
            "Os valores acima variam automaticamente em +/-20% para simular comportamento humano."
        )
        variation_hint.setStyleSheet(hint_style)
        variation_hint.setWordWrap(True)
        pa_layout.addWidget(variation_hint)
        pa_layout.addStretch()
        stack.addWidget(page_actions)

        # ====================== PAGE 1: Feed ======================
        page_feed = QWidget()
        pf_layout = QVBoxLayout(page_feed)
        pf_layout.setContentsMargins(16, 16, 16, 16)
        pf_layout.setSpacing(10)

        def _add_min_max_section(parent_layout, title_text: str, key_min: str, key_max: str):
            lbl = QLabel(title_text)
            lbl.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
            parent_layout.addWidget(lbl)
            row = QHBoxLayout()
            row.addWidget(QLabel("Min:"))
            row.addWidget(_make_spin(key_min, day.get(key_min, 0), max_val=3600, width=70))
            row.addSpacing(20)
            row.addWidget(QLabel("Max:"))
            row.addWidget(_make_spin(key_max, day.get(key_max, 0), max_val=3600, width=70))
            row.addStretch()
            parent_layout.addLayout(row)

        _add_min_max_section(pf_layout, "Antes das acoes (segundos):",
                             "browse_before_min", "browse_before_max")
        pf_layout.addSpacing(8)
        _add_min_max_section(pf_layout, "Entre as acoes (segundos):",
                             "browse_between_min", "browse_between_max")

        feed_hint = QLabel("Ex: Antes 120-300 seg, Entre 30-90 seg")
        feed_hint.setStyleSheet("color: #666688; font-size: 8pt;")
        pf_layout.addWidget(feed_hint)
        pf_layout.addStretch()
        stack.addWidget(page_feed)

        # ====================== PAGE 2: Comportamento ======================
        page_behavior = QWidget()
        pb_layout = QVBoxLayout(page_behavior)
        pb_layout.setContentsMargins(16, 16, 16, 16)
        pb_layout.setSpacing(10)

        form_behavior = QFormLayout()
        form_behavior.setHorizontalSpacing(16)
        form_behavior.setVerticalSpacing(10)

        form_behavior.addRow("Abrir postagens:",
                             _make_spin("posts_to_open", day.get("posts_to_open", 0), max_val=20))
        form_behavior.addRow("Ver comentarios (%):",
                             _make_spin("view_comments_chance",
                                        int(day.get("view_comments_chance", 0.3) * 100)))

        clpt_val = day.get("comment_likes_per_target", 3)
        form_behavior.addRow("Likes/alvo (coment.):",
                             _make_spin("comment_likes_per_target", clpt_val, max_val=10))

        form_behavior.addRow("Pular coment. (%):",
                             _make_spin("comment_like_skip_chance",
                                        int(day.get("comment_like_skip_chance", 0.25) * 100)))
        form_behavior.addRow("Follows iniciais:",
                             _make_spin("follow_initial_count",
                                        day.get("follow_initial_count", 0), max_val=10))
        pb_layout.addLayout(form_behavior)

        chk_likes_feed = QCheckBox("Curtir no feed")
        chk_likes_feed.setChecked(day.get("likes_on_feed", False))
        pb_layout.addWidget(chk_likes_feed)

        chk_rt_feed = QCheckBox("RT no feed")
        chk_rt_feed.setChecked(day.get("retweets_on_feed", False))
        pb_layout.addWidget(chk_rt_feed)

        pb_layout.addStretch()
        stack.addWidget(page_behavior)

        # Select first tab
        _switch_tab(0)

        # --- Save / Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)
        main_layout.addWidget(button_box)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            return {
                "day": day.get("day", 1),
                "likes": spins["likes"].value(),
                "comment_likes": spins["comment_likes"].value(),
                "follows": spins["follows"].value(),
                "retweets": spins["retweets"].value(),
                "unfollows": spins["unfollows"].value(),
                "browse_before_min": spins["browse_before_min"].value(),
                "browse_before_max": spins["browse_before_max"].value(),
                "browse_between_min": spins["browse_between_min"].value(),
                "browse_between_max": spins["browse_between_max"].value(),
                "posts_to_open": spins["posts_to_open"].value(),
                "view_comments_chance": spins["view_comments_chance"].value() / 100.0,
                "likes_on_feed": chk_likes_feed.isChecked(),
                "retweets_on_feed": chk_rt_feed.isChecked(),
                "comment_likes_per_target": spins["comment_likes_per_target"].value(),
                "comment_like_skip_chance": spins["comment_like_skip_chance"].value() / 100.0,
                "follow_initial_count": spins["follow_initial_count"].value(),
            }
        return None
