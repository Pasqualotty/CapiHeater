"""
LogsTab - Activity log viewer with filters and auto-refresh.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class LogsTab(ttk.Frame):
    """Activity logs tab with filtering, auto-refresh, and clear functionality.

    Parameters
    ----------
    parent : tk.Widget
        Parent frame (notebook tab container).
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    AUTO_REFRESH_MS = 5000

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, style="Tab.TFrame", **kwargs)
        self.app = app
        self._auto_refresh_id = None
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))

        ttk.Label(header, text="Logs de Atividade", style="Heading.TLabel").pack(side=tk.LEFT)

        # Filters row
        filter_frame = ttk.Frame(self, style="Dark.TFrame")
        filter_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        # Account filter
        ttk.Label(filter_frame, text="Conta:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._filter_account = ttk.Combobox(filter_frame, state="readonly", style="Dark.TCombobox", width=16)
        self._filter_account.pack(side=tk.LEFT, padx=(0, 12))
        self._filter_account.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # Action type filter
        ttk.Label(filter_frame, text="Acao:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._filter_action = ttk.Combobox(
            filter_frame,
            values=["Todas", "like", "follow", "retweet", "unfollow", "login", "browse", "sistema"],
            state="readonly",
            style="Dark.TCombobox",
            width=12,
        )
        self._filter_action.pack(side=tk.LEFT, padx=(0, 12))
        self._filter_action.set("Todas")
        self._filter_action.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # Status filter
        ttk.Label(filter_frame, text="Status:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._filter_status = ttk.Combobox(
            filter_frame,
            values=["Todos", "success", "failed", "skipped"],
            state="readonly",
            style="Dark.TCombobox",
            width=10,
        )
        self._filter_status.pack(side=tk.LEFT, padx=(0, 12))
        self._filter_status.set("Todos")
        self._filter_status.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # Auto-refresh checkbox
        self._auto_refresh_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(
            filter_frame,
            text="Atualizar automaticamente",
            variable=self._auto_refresh_var,
            style="Dark.TCheckbutton",
            command=self._toggle_auto_refresh,
        )
        chk.pack(side=tk.LEFT, padx=(0, 12))

        # Clear button
        ttk.Button(filter_frame, text="Limpar Logs", style="Danger.TButton", command=self._clear_logs).pack(side=tk.RIGHT)
        ttk.Button(filter_frame, text="Atualizar", style="Accent.TButton", command=self.refresh).pack(side=tk.RIGHT, padx=(0, 6))

        # Treeview
        tree_frame = ttk.Frame(self, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("timestamp", "account", "action", "target", "status", "error")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        self._tree.heading("timestamp", text="Data/Hora")
        self._tree.heading("account", text="Conta")
        self._tree.heading("action", text="Acao")
        self._tree.heading("target", text="Alvo")
        self._tree.heading("status", text="Status")
        self._tree.heading("error", text="Erro")

        self._tree.column("timestamp", width=150, anchor=tk.W)
        self._tree.column("account", width=120, anchor=tk.W)
        self._tree.column("action", width=90, anchor=tk.CENTER)
        self._tree.column("target", width=140, anchor=tk.W)
        self._tree.column("status", width=80, anchor=tk.CENTER)
        self._tree.column("error", width=200, anchor=tk.W)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload logs from the database, applying current filters."""
        self._tree.delete(*self._tree.get_children())
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
        acct = self._filter_account.get()
        if acct and acct != "Todas":
            query += " AND a.username = ?"
            params.append(acct.lstrip("@"))

        # Action filter
        action = self._filter_action.get()
        if action and action != "Todas":
            query += " AND al.action_type = ?"
            params.append(action)

        # Status filter
        status = self._filter_status.get()
        if status and status != "Todos":
            query += " AND al.status = ?"
            params.append(status)

        query += " ORDER BY al.executed_at DESC LIMIT 1000"

        rows = self.app.db.fetch_all(query, tuple(params))

        for row in rows:
            status_val = row.get("status", "")
            tag = f"log_{status_val}"
            iid = self._tree.insert(
                "",
                tk.END,
                values=(
                    row.get("executed_at", ""),
                    f"@{row.get('username', '???')}",
                    row.get("action_type", ""),
                    f"@{row.get('target_username', '')}" if row.get("target_username") else "—",
                    status_val,
                    row.get("error_message") or "—",
                ),
                tags=(tag,),
            )

        self._tree.tag_configure("log_success", foreground="#00e676")
        self._tree.tag_configure("log_failed", foreground="#ff1744")
        self._tree.tag_configure("log_error", foreground="#ff1744")
        self._tree.tag_configure("log_skipped", foreground="#ffea00")

    def _update_account_filter(self) -> None:
        """Refresh the account filter dropdown."""
        accounts = self.app.account_manager.get_all_accounts()
        names = ["Todas"] + [f"@{a.get('username', '???')}" for a in accounts]
        current = self._filter_account.get()
        self._filter_account["values"] = names
        if current not in names:
            self._filter_account.set("Todas")

    def on_new_log(self, msg: dict) -> None:
        """Handle a log message from the engine queue (trigger refresh)."""
        if self._auto_refresh_var.get():
            self.refresh()

    # ==================================================================
    # Actions
    # ==================================================================

    def _clear_logs(self) -> None:
        if not messagebox.askyesno(
            "Confirmar",
            "Tem certeza que deseja limpar todos os logs?\nEsta acao nao pode ser desfeita.",
            parent=self,
        ):
            return
        self.app.db.execute("DELETE FROM activity_logs")
        self.app.set_status("Logs limpos")
        self.refresh()

    def _toggle_auto_refresh(self) -> None:
        if self._auto_refresh_var.get():
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _start_auto_refresh(self) -> None:
        self.refresh()
        self._auto_refresh_id = self.after(self.AUTO_REFRESH_MS, self._start_auto_refresh)

    def _stop_auto_refresh(self) -> None:
        if self._auto_refresh_id is not None:
            self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None
