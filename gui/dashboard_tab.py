"""
DashboardTab - Overview of all accounts and quick controls.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date, timedelta

from gui.widgets.status_indicator import StatusIndicator, STATUS_COLORS
from gui.widgets.account_card import AccountCard


class DashboardTab(ttk.Frame):
    """Dashboard showing overview cards and per-account status list.

    Parameters
    ----------
    parent : tk.Widget
        Parent frame (the notebook tab container).
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, style="Tab.TFrame", **kwargs)
        self.app = app

        self._account_cards: dict[int, AccountCard] = {}
        self._account_rows: dict[int, dict] = {}

        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        # ---------- Overview cards row ----------
        overview_frame = ttk.Frame(self, style="Dark.TFrame")
        overview_frame.pack(fill=tk.X, padx=12, pady=(12, 6))

        self._card_data = {
            "total": {"label": "Total de Contas", "var": tk.StringVar(value="0")},
            "running": {"label": "Rodando", "var": tk.StringVar(value="0")},
            "paused": {"label": "Pausadas", "var": tk.StringVar(value="0")},
            "errors": {"label": "Erros", "var": tk.StringVar(value="0")},
        }

        for key, info in self._card_data.items():
            card = ttk.Frame(overview_frame, style="Card.TFrame")
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6, pady=4)

            val_lbl = ttk.Label(card, textvariable=info["var"], style="OverviewValue.TLabel")
            val_lbl.pack(padx=16, pady=(12, 0))

            cap_lbl = ttk.Label(card, text=info["label"], style="OverviewCaption.TLabel")
            cap_lbl.pack(padx=16, pady=(0, 12))

        # ---------- Buttons row ----------
        btn_frame = ttk.Frame(self, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, padx=12, pady=6)

        ttk.Button(btn_frame, text="Iniciar Todos", style="Accent.TButton", command=self._start_all).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Parar Todos", style="Danger.TButton", command=self._stop_all).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Atualizar", style="Accent.TButton", command=self.refresh).pack(side=tk.LEFT)

        # ---------- Account list ----------
        list_frame = ttk.Frame(self, style="Dark.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("status_icon", "username", "status", "dia", "acoes")
        self._tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="extended",
        )

        self._tree.heading("status_icon", text="")
        self._tree.heading("username", text="Conta")
        self._tree.heading("status", text="Status")
        self._tree.heading("dia", text="Dia")
        self._tree.heading("acoes", text="")

        self._tree.column("status_icon", width=30, anchor=tk.CENTER, stretch=False)
        self._tree.column("username", width=200, anchor=tk.W)
        self._tree.column("status", width=120, anchor=tk.CENTER)
        self._tree.column("dia", width=80, anchor=tk.CENTER)
        self._tree.column("acoes", width=200, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Per-account action buttons (context menu)
        self._tree.bind("<Button-3>", self._show_context_menu)
        self._tree.bind("<Control-a>", self._select_all)
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        # Selection info
        sel_frame = ttk.Frame(self, style="Dark.TFrame")
        sel_frame.pack(fill=tk.X, padx=12, pady=(0, 2))
        self._sel_info = tk.StringVar(value="")
        ttk.Label(sel_frame, textvariable=self._sel_info, style="Dark.TLabel").pack(side=tk.LEFT)

        # Action buttons below tree
        action_frame = ttk.Frame(self, style="Dark.TFrame")
        action_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        ttk.Button(action_frame, text="Iniciar Selecionadas", style="Accent.TButton", command=self._start_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(action_frame, text="Pausar Selecionadas", style="Accent.TButton", command=self._pause_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(action_frame, text="Parar Selecionadas", style="Danger.TButton", command=self._stop_selected).pack(side=tk.LEFT)

    # ==================================================================
    # Data refresh
    # ==================================================================

    def refresh(self) -> None:
        """Reload account data from the database and update the view."""
        accounts = self.app.account_manager.get_all_accounts()

        # Update overview cards
        total = len(accounts)
        running = sum(1 for a in accounts if a.get("status") == "running")
        paused = sum(1 for a in accounts if a.get("status") == "paused")
        errors = sum(1 for a in accounts if a.get("status") == "error")

        self._card_data["total"]["var"].set(str(total))
        self._card_data["running"]["var"].set(str(running))
        self._card_data["paused"]["var"].set(str(paused))
        self._card_data["errors"]["var"].set(str(errors))

        # Update tree
        self._tree.delete(*self._tree.get_children())
        self._account_rows.clear()

        for acc in accounts:
            aid = acc.get("id", 0)
            status = acc.get("status", "idle")
            status_display = self._status_label(status)
            dot = self._status_dot(status)
            day = acc.get("current_day", 1)

            iid = self._tree.insert(
                "",
                tk.END,
                values=(dot, f"@{acc.get('username', '???')}", status_display, f"Dia {day}", ""),
            )
            self._account_rows[aid] = {"iid": iid, "account": acc}

        # Tag-based coloring for status dots
        for aid, row_info in self._account_rows.items():
            status = row_info["account"].get("status", "idle")
            tag = f"status_{status}"
            self._tree.item(row_info["iid"], tags=(tag,))

        self._tree.tag_configure("status_running", foreground="#00e676")
        self._tree.tag_configure("status_paused", foreground="#ffea00")
        self._tree.tag_configure("status_error", foreground="#ff1744")
        self._tree.tag_configure("status_idle", foreground="#9e9e9e")
        self._tree.tag_configure("status_completed", foreground="#2979ff")

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
        selection = self._tree.selection()
        ids = []
        for iid in selection:
            for aid, row_info in self._account_rows.items():
                if row_info["iid"] == iid:
                    ids.append(aid)
                    break
        return ids

    def _select_all(self, _event=None) -> None:
        self._tree.selection_set(self._tree.get_children())

    def _on_selection_changed(self, _event=None) -> None:
        count = len(self._tree.selection())
        if count == 0:
            self._sel_info.set("")
        elif count == 1:
            self._sel_info.set("1 conta selecionada")
        else:
            self._sel_info.set(f"{count} contas selecionadas")

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

    def _show_context_menu(self, event) -> None:
        """Right-click context menu for per-account actions."""
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        # Only change selection on right-click if the clicked item isn't already selected
        if iid not in self._tree.selection():
            self._tree.selection_set(iid)

        menu = tk.Menu(self, tearoff=0, bg="#16213e", fg="#e0e0e0", activebackground="#0f3460")
        menu.add_command(label="Iniciar", command=self._start_selected)
        menu.add_command(label="Pausar", command=self._pause_selected)
        menu.add_command(label="Parar", command=self._stop_selected)
        menu.add_separator()
        menu.add_command(label="Editar Dia", command=self._edit_day)
        menu.tk_popup(event.x_root, event.y_root)

    def _edit_day(self) -> None:
        """Let the user change which warming day an account will run next."""
        ids = self._get_selected_account_ids()
        if len(ids) != 1:
            self.app.set_status("Selecione exatamente uma conta para editar o dia")
            return

        aid = ids[0]
        account = self._account_rows[aid]["account"]
        status = account.get("status", "idle")

        if status in ("running", "paused"):
            messagebox.showwarning(
                "Aviso", "Pare a conta antes de editar o dia.", parent=self,
            )
            return

        current = account.get("current_day", 1)
        new_day = simpledialog.askinteger(
            "Editar Dia",
            f"Dia atual: {current}\nNovo dia:",
            initialvalue=current,
            minvalue=1,
            maxvalue=365,
            parent=self,
        )
        if new_day is None or new_day == current:
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

    @staticmethod
    def _status_dot(status: str) -> str:
        dots = {
            "running": "\u25cf",   # ●
            "paused": "\u25cf",
            "error": "\u25cf",
            "idle": "\u25cb",      # ○
            "completed": "\u25cf",
        }
        return dots.get(status, "\u25cb")
