"""
ScheduleTab - Visualization and editing of warming schedules.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class ScheduleTab(ttk.Frame):
    """Schedule management with view, edit, create, and delete.

    Parameters
    ----------
    parent : tk.Widget
        Parent frame (notebook tab container).
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, style="Tab.TFrame", **kwargs)
        self.app = app
        self._schedules: list[dict] = []
        self._build_ui()
        self._load_schedules()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))

        ttk.Label(header, text="Gerenciar Cronogramas", style="Heading.TLabel").pack(side=tk.LEFT)

        # Schedule selector row
        sel_frame = ttk.Frame(self, style="Dark.TFrame")
        sel_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        ttk.Label(sel_frame, text="Cronograma:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self._combo = ttk.Combobox(sel_frame, state="readonly", style="Dark.TCombobox", width=30)
        self._combo.pack(side=tk.LEFT)
        self._combo.bind("<<ComboboxSelected>>", self._on_schedule_selected)

        # Info label
        self._info_var = tk.StringVar(value="")
        ttk.Label(sel_frame, textvariable=self._info_var, style="Dark.TLabel").pack(side=tk.LEFT, padx=12)

        # Buttons row
        btn_frame = ttk.Frame(self, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        ttk.Button(btn_frame, text="Novo Cronograma", style="Accent.TButton",
                   command=self._on_new).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Duplicar", style="Accent.TButton",
                   command=self._on_duplicate).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Editar Dia", style="Accent.TButton",
                   command=self._on_edit_day).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Adicionar Dia", style="Accent.TButton",
                   command=self._on_add_day).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Remover Dia", style="Accent.TButton",
                   command=self._on_remove_day).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Excluir Cronograma", style="Danger.TButton",
                   command=self._on_delete).pack(side=tk.RIGHT)

        # Treeview
        tree_frame = ttk.Frame(self, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("dia", "likes", "follows", "retweets", "unfollows", "browse_before", "browse_between", "posts_to_open")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        self._tree.heading("dia", text="Dia")
        self._tree.heading("likes", text="Likes")
        self._tree.heading("follows", text="Follows")
        self._tree.heading("retweets", text="Retweets")
        self._tree.heading("unfollows", text="Unfollows")
        self._tree.heading("browse_before", text="Feed Antes (seg)")
        self._tree.heading("browse_between", text="Feed Entre (seg)")
        self._tree.heading("posts_to_open", text="Abrir Posts")

        self._tree.column("dia", width=60, anchor=tk.CENTER)
        self._tree.column("likes", width=70, anchor=tk.CENTER)
        self._tree.column("follows", width=70, anchor=tk.CENTER)
        self._tree.column("retweets", width=80, anchor=tk.CENTER)
        self._tree.column("unfollows", width=80, anchor=tk.CENTER)
        self._tree.column("browse_before", width=120, anchor=tk.CENTER)
        self._tree.column("browse_between", width=120, anchor=tk.CENTER)
        self._tree.column("posts_to_open", width=80, anchor=tk.CENTER)

        # Double-click to edit
        self._tree.bind("<Double-1>", lambda _e: self._on_edit_day())

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tip
        ttk.Label(
            self,
            text="Dica: clique duplo em um dia para editar. Alteracoes sao salvas automaticamente.",
            style="Dark.TLabel",
        ).pack(padx=12, pady=(0, 12))

    # ==================================================================
    # Data
    # ==================================================================

    def _load_schedules(self) -> None:
        """Populate the schedule dropdown from the database."""
        self._schedules = self.app.db.fetch_all(
            "SELECT id, name, description, schedule_json FROM schedules ORDER BY id"
        )

        names = [s["name"] for s in self._schedules]
        self._combo["values"] = names

        if names:
            self._combo.current(0)
            self._display_schedule(0)

    def _on_schedule_selected(self, _event=None) -> None:
        idx = self._combo.current()
        if idx >= 0:
            self._display_schedule(idx)

    def _display_schedule(self, idx: int) -> None:
        """Show the day-by-day breakdown for the selected schedule."""
        self._tree.delete(*self._tree.get_children())

        schedule = self._schedules[idx]
        self._info_var.set(schedule.get("description", ""))

        days = self._parse_days(schedule)
        for entry in days:
            bb_min = entry.get("browse_before_min", 0)
            bb_max = entry.get("browse_before_max", 0)
            bw_min = entry.get("browse_between_min", 0)
            bw_max = entry.get("browse_between_max", 0)

            browse_before_str = f"{bb_min}-{bb_max}" if (bb_min or bb_max) else "0"
            browse_between_str = f"{bw_min}-{bw_max}" if (bw_min or bw_max) else "0"

            self._tree.insert(
                "",
                tk.END,
                values=(
                    f"Dia {entry.get('day', '?')}",
                    entry.get("likes", 0),
                    entry.get("follows", 0),
                    entry.get("retweets", 0),
                    entry.get("unfollows", 0),
                    browse_before_str,
                    browse_between_str,
                    entry.get("posts_to_open", 0),
                ),
            )

    def _parse_days(self, schedule: dict) -> list[dict]:
        raw = schedule.get("schedule_json", "[]")
        try:
            days = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            days = []
        return days if isinstance(days, list) else []

    def _current_schedule(self) -> dict | None:
        idx = self._combo.current()
        if idx < 0 or idx >= len(self._schedules):
            return None
        return self._schedules[idx]

    def _save_schedule_days(self, schedule: dict, days: list[dict]) -> None:
        """Persist updated days to the database and refresh."""
        self.app.db.execute(
            "UPDATE schedules SET schedule_json = ? WHERE id = ?",
            (json.dumps(days), schedule["id"]),
        )
        # Refresh
        cur_name = schedule["name"]
        self._load_schedules()
        # Re-select
        for i, s in enumerate(self._schedules):
            if s["name"] == cur_name:
                self._combo.current(i)
                self._display_schedule(i)
                break

    # ==================================================================
    # Actions
    # ==================================================================

    def _on_edit_day(self) -> None:
        """Edit the selected day's values."""
        schedule = self._current_schedule()
        if not schedule:
            return

        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um dia para editar.", parent=self)
            return

        item = self._tree.item(selected[0])
        values = item["values"]
        # values = ("Dia X", likes, follows, retweets, unfollows)
        day_str = str(values[0]).replace("Dia ", "")

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

        new_day = {"day": next_day, "likes": 0, "follows": 0, "retweets": 0, "unfollows": 0,
                   "browse_before_min": 0, "browse_before_max": 0,
                   "browse_between_min": 0, "browse_between_max": 0,
                   "posts_to_open": 0, "view_comments_chance": 0.3,
                   "likes_on_feed": True, "follow_initial_count": 0}
        result = self._edit_day_dialog(new_day)
        if result:
            days.append(result)
            self._save_schedule_days(schedule, days)

    def _on_remove_day(self) -> None:
        """Remove the selected day."""
        schedule = self._current_schedule()
        if not schedule:
            return

        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um dia para remover.", parent=self)
            return

        item = self._tree.item(selected[0])
        day_str = str(item["values"][0]).replace("Dia ", "")

        days = self._parse_days(schedule)
        days = [d for d in days if str(d.get("day", "")) != day_str]

        # Renumber days
        for i, d in enumerate(days):
            d["day"] = i + 1

        self._save_schedule_days(schedule, days)

    def _on_new(self) -> None:
        """Create a new empty schedule."""
        name = simpledialog.askstring(
            "Novo Cronograma", "Nome do cronograma:", parent=self
        )
        if not name or not name.strip():
            return

        desc = simpledialog.askstring(
            "Novo Cronograma", "Descricao (opcional):", parent=self
        ) or ""

        # Start with a single day
        initial = [{"day": 1, "likes": 3, "follows": 0, "retweets": 0, "unfollows": 0}]

        self.app.db.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            (name.strip(), desc.strip(), json.dumps(initial)),
        )

        self._load_schedules()
        # Select the new one
        for i, s in enumerate(self._schedules):
            if s["name"] == name.strip():
                self._combo.current(i)
                self._display_schedule(i)
                break

        messagebox.showinfo("Sucesso", f"Cronograma '{name.strip()}' criado!", parent=self)

    def _on_duplicate(self) -> None:
        """Duplicate the current schedule."""
        schedule = self._current_schedule()
        if not schedule:
            return

        name = simpledialog.askstring(
            "Duplicar Cronograma",
            "Nome para a copia:",
            initialvalue=f"{schedule['name']} (copia)",
            parent=self,
        )
        if not name or not name.strip():
            return

        self.app.db.execute(
            "INSERT INTO schedules (name, description, schedule_json) VALUES (?, ?, ?)",
            (name.strip(), schedule.get("description", ""), schedule.get("schedule_json", "[]")),
        )

        self._load_schedules()
        for i, s in enumerate(self._schedules):
            if s["name"] == name.strip():
                self._combo.current(i)
                self._display_schedule(i)
                break

        messagebox.showinfo("Sucesso", f"Cronograma duplicado como '{name.strip()}'!", parent=self)

    def _on_delete(self) -> None:
        """Delete the current schedule."""
        schedule = self._current_schedule()
        if not schedule:
            return

        if len(self._schedules) <= 1:
            messagebox.showwarning("Aviso", "Nao e possivel excluir o unico cronograma.", parent=self)
            return

        # Check if any account uses this schedule
        count = self.app.db.fetch_one(
            "SELECT COUNT(*) as c FROM accounts WHERE schedule_id = ?",
            (schedule["id"],),
        )
        if count and count.get("c", 0) > 0:
            messagebox.showwarning(
                "Aviso",
                f"Existem {count['c']} conta(s) usando este cronograma.\n"
                "Mude o cronograma dessas contas antes de excluir.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Confirmar", f"Excluir cronograma '{schedule['name']}'?", parent=self
        ):
            return

        self.app.db.execute("DELETE FROM schedules WHERE id = ?", (schedule["id"],))
        self._load_schedules()

    # ==================================================================
    # Edit dialog
    # ==================================================================

    def _edit_day_dialog(self, day: dict) -> dict | None:
        """Show a dialog to edit a single day's values. Returns updated dict or None."""
        dlg = tk.Toplevel(self)
        dlg.title(f"Dia {day.get('day', '?')}")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.geometry("400x650")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # Center
        dlg.update_idletasks()
        x = dlg.winfo_toplevel().winfo_rootx() + 200
        y = dlg.winfo_toplevel().winfo_rooty() + 80
        dlg.geometry(f"+{x}+{y}")

        bg = "#1a1a2e"
        fg = "#ffffff"
        entry_bg = "#16213e"
        section_fg = "#5588cc"

        tk.Label(dlg, text=f"Editar Dia {day.get('day', '?')}", font=("Segoe UI", 13, "bold"),
                 bg=bg, fg=fg).pack(pady=(16, 8))

        fields_frame = tk.Frame(dlg, bg=bg)
        fields_frame.pack(padx=24, fill=tk.X)

        # --- Actions section ---
        tk.Label(fields_frame, text="Acoes", font=("Segoe UI", 10, "bold"),
                 bg=bg, fg=section_fg).pack(anchor="w", pady=(4, 2))

        vars_ = {}
        for label, key in [("Likes:", "likes"), ("Follows:", "follows"),
                           ("Retweets:", "retweets"), ("Unfollows:", "unfollows")]:
            row = tk.Frame(fields_frame, bg=bg)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 10), bg=bg, fg=fg, width=14, anchor="w").pack(side=tk.LEFT)
            var = tk.IntVar(value=day.get(key, 0))
            vars_[key] = var
            sp = tk.Spinbox(row, from_=0, to=100, textvariable=var, width=8,
                            font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                            insertbackground=fg, buttonbackground="#0f3460")
            sp.pack(side=tk.LEFT, padx=(8, 0))

        # --- Feed browsing section ---
        tk.Label(fields_frame, text="Navegar pelo Feed (segundos)", font=("Segoe UI", 10, "bold"),
                 bg=bg, fg=section_fg).pack(anchor="w", pady=(12, 2))

        tk.Label(fields_frame, text="Antes das acoes (seg):", font=("Segoe UI", 9),
                 bg=bg, fg="#9e9e9e").pack(anchor="w")

        row_bb = tk.Frame(fields_frame, bg=bg)
        row_bb.pack(fill=tk.X, pady=2)
        tk.Label(row_bb, text="Min:", font=("Segoe UI", 10), bg=bg, fg=fg, width=5, anchor="w").pack(side=tk.LEFT)
        bb_min_var = tk.IntVar(value=day.get("browse_before_min", 0))
        vars_["browse_before_min"] = bb_min_var
        tk.Spinbox(row_bb, from_=0, to=3600, textvariable=bb_min_var, width=6,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(row_bb, text="Max:", font=("Segoe UI", 10), bg=bg, fg=fg, width=5, anchor="w").pack(side=tk.LEFT)
        bb_max_var = tk.IntVar(value=day.get("browse_before_max", 0))
        vars_["browse_before_max"] = bb_max_var
        tk.Spinbox(row_bb, from_=0, to=3600, textvariable=bb_max_var, width=6,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(fields_frame, text="Entre as acoes (seg):", font=("Segoe UI", 9),
                 bg=bg, fg="#9e9e9e").pack(anchor="w", pady=(6, 0))

        row_bw = tk.Frame(fields_frame, bg=bg)
        row_bw.pack(fill=tk.X, pady=2)
        tk.Label(row_bw, text="Min:", font=("Segoe UI", 10), bg=bg, fg=fg, width=5, anchor="w").pack(side=tk.LEFT)
        bw_min_var = tk.IntVar(value=day.get("browse_between_min", 0))
        vars_["browse_between_min"] = bw_min_var
        tk.Spinbox(row_bw, from_=0, to=3600, textvariable=bw_min_var, width=6,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(row_bw, text="Max:", font=("Segoe UI", 10), bg=bg, fg=fg, width=5, anchor="w").pack(side=tk.LEFT)
        bw_max_var = tk.IntVar(value=day.get("browse_between_max", 0))
        vars_["browse_between_max"] = bw_max_var
        tk.Spinbox(row_bw, from_=0, to=3600, textvariable=bw_max_var, width=6,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(4, 0))

        # Hint
        tk.Label(fields_frame, text="Ex: Antes 120-300 seg, Entre 30-90 seg",
                 font=("Segoe UI", 8), bg=bg, fg="#666688").pack(anchor="w", pady=(6, 0))

        # --- Comportamento section ---
        tk.Label(fields_frame, text="Comportamento", font=("Segoe UI", 10, "bold"),
                 bg=bg, fg=section_fg).pack(anchor="w", pady=(12, 2))

        row_pto = tk.Frame(fields_frame, bg=bg)
        row_pto.pack(fill=tk.X, pady=2)
        tk.Label(row_pto, text="Abrir postagens:", font=("Segoe UI", 10), bg=bg, fg=fg, width=14, anchor="w").pack(side=tk.LEFT)
        pto_var = tk.IntVar(value=day.get("posts_to_open", 0))
        vars_["posts_to_open"] = pto_var
        tk.Spinbox(row_pto, from_=0, to=20, textvariable=pto_var, width=8,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(8, 0))

        row_vcc = tk.Frame(fields_frame, bg=bg)
        row_vcc.pack(fill=tk.X, pady=2)
        tk.Label(row_vcc, text="Ver comentarios (%):", font=("Segoe UI", 10), bg=bg, fg=fg, width=14, anchor="w").pack(side=tk.LEFT)
        vcc_var = tk.IntVar(value=int(day.get("view_comments_chance", 0.3) * 100))
        vars_["view_comments_chance"] = vcc_var
        tk.Spinbox(row_vcc, from_=0, to=100, textvariable=vcc_var, width=8,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(8, 0))

        row_lof = tk.Frame(fields_frame, bg=bg)
        row_lof.pack(fill=tk.X, pady=2)
        tk.Label(row_lof, text="Curtir no feed:", font=("Segoe UI", 10), bg=bg, fg=fg, width=14, anchor="w").pack(side=tk.LEFT)
        lof_var = tk.BooleanVar(value=day.get("likes_on_feed", True))
        vars_["likes_on_feed"] = lof_var
        tk.Checkbutton(row_lof, variable=lof_var, bg=bg, fg=fg, selectcolor=entry_bg,
                       activebackground=bg, activeforeground=fg).pack(side=tk.LEFT, padx=(8, 0))

        row_fic = tk.Frame(fields_frame, bg=bg)
        row_fic.pack(fill=tk.X, pady=2)
        tk.Label(row_fic, text="Follows iniciais:", font=("Segoe UI", 10), bg=bg, fg=fg, width=14, anchor="w").pack(side=tk.LEFT)
        fic_var = tk.IntVar(value=day.get("follow_initial_count", 0))
        vars_["follow_initial_count"] = fic_var
        tk.Spinbox(row_fic, from_=0, to=10, textvariable=fic_var, width=8,
                   font=("Segoe UI", 10), bg=entry_bg, fg=fg,
                   insertbackground=fg, buttonbackground="#0f3460").pack(side=tk.LEFT, padx=(8, 0))

        result = {"accepted": False}

        def on_ok():
            result["accepted"] = True
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg=bg)
        btn_frame.pack(pady=16)

        tk.Button(btn_frame, text="Salvar", font=("Segoe UI", 10, "bold"), bg="#0f3460", fg=fg,
                  relief="flat", padx=16, pady=4, command=on_ok).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Cancelar", font=("Segoe UI", 10), bg="#333355", fg=fg,
                  relief="flat", padx=16, pady=4, command=dlg.destroy).pack(side=tk.LEFT, padx=6)

        dlg.wait_window()

        if result["accepted"]:
            return {
                "day": day.get("day", 1),
                "likes": vars_["likes"].get(),
                "follows": vars_["follows"].get(),
                "retweets": vars_["retweets"].get(),
                "unfollows": vars_["unfollows"].get(),
                "browse_before_min": vars_["browse_before_min"].get(),
                "browse_before_max": vars_["browse_before_max"].get(),
                "browse_between_min": vars_["browse_between_min"].get(),
                "browse_between_max": vars_["browse_between_max"].get(),
                "posts_to_open": vars_["posts_to_open"].get(),
                "view_comments_chance": vars_["view_comments_chance"].get() / 100.0,
                "likes_on_feed": vars_["likes_on_feed"].get(),
                "follow_initial_count": vars_["follow_initial_count"].get(),
            }
        return None
