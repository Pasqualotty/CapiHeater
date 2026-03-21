"""
AdminTab - Painel administrativo para moderadores/admins (dark themed, PT-BR).
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Theme colours (same as login window)
BG = "#1a1a2e"
FG = "#ffffff"
ACCENT = "#0f3460"
ENTRY_BG = "#16213e"


class AdminTab(tk.Frame):
    """Frame meant to be added as a tab in a ttk.Notebook (or packed directly).

    Parameters
    ----------
    parent : tk widget
        Parent container.
    auth : SupabaseAuth
        Authenticated instance.
    session :
        Current Supabase session.
    """

    def __init__(self, parent, auth, session, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.auth = auth
        self.session = session
        self._current_filter = "Todos"

        self._build_toolbar()
        self._build_table()
        self._build_filters()
        self.refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(
            toolbar,
            text="Gerenciamento de Usuarios",
            font=("Segoe UI", 13, "bold"),
            bg=BG,
            fg=FG,
        ).pack(side="left")

        # Buttons (right side)
        btn_kw = dict(
            font=("Segoe UI", 9, "bold"),
            bg=ACCENT,
            fg=FG,
            activebackground="#1a5276",
            activeforeground=FG,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
        )

        self._refresh_btn = tk.Button(
            toolbar, text="Atualizar", command=self.refresh, **btn_kw
        )
        self._refresh_btn.pack(side="right", padx=(6, 0))

        self._revoke_btn = tk.Button(
            toolbar, text="Revogar Acesso", command=self._on_revoke, **btn_kw
        )
        self._revoke_btn.pack(side="right", padx=(6, 0))

        self._grant_btn = tk.Button(
            toolbar, text="Liberar Acesso", command=self._on_grant, **btn_kw
        )
        self._grant_btn.pack(side="right", padx=(6, 0))

    def _build_table(self):
        columns = ("email", "role", "status", "activated_at", "granted_by", "grant_reason")
        col_headings = {
            "email": "E-mail",
            "role": "Papel",
            "status": "Status",
            "activated_at": "Ativado em",
            "granted_by": "Liberado por",
            "grant_reason": "Motivo",
        }

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Admin.Treeview",
            background=ENTRY_BG,
            foreground=FG,
            fieldbackground=ENTRY_BG,
            rowheight=26,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Admin.Treeview.Heading",
            background=ACCENT,
            foreground=FG,
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Admin.Treeview", background=[("selected", ACCENT)])

        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=10, pady=6)

        self._tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            style="Admin.Treeview",
            selectmode="browse",
        )
        for col in columns:
            self._tree.heading(col, text=col_headings[col])
            width = 170 if col == "email" else 110
            self._tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _build_filters(self):
        fbar = tk.Frame(self, bg=BG)
        fbar.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(fbar, text="Filtro:", font=("Segoe UI", 9), bg=BG, fg=FG).pack(
            side="left"
        )

        self._filter_var = tk.StringVar(value="Todos")
        for label in ("Todos", "Ativos", "Inativos", "Liberados Manualmente"):
            rb = tk.Radiobutton(
                fbar,
                text=label,
                variable=self._filter_var,
                value=label,
                font=("Segoe UI", 9),
                bg=BG,
                fg=FG,
                selectcolor=ENTRY_BG,
                activebackground=BG,
                activeforeground=FG,
                command=self._apply_filter,
            )
            rb.pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        """Fetch users from Supabase and populate the table."""
        self._all_users: list[dict] = []
        try:
            self._all_users = self.auth.list_users()
        except Exception:
            pass
        self._apply_filter()

    def _apply_filter(self):
        filt = self._filter_var.get()
        self._tree.delete(*self._tree.get_children())

        for u in self._all_users:
            is_active = u.get("is_active", False)
            status = "Ativo" if is_active else "Inativo"

            if filt == "Ativos" and not is_active:
                continue
            if filt == "Inativos" and is_active:
                continue
            if filt == "Liberados Manualmente" and not u.get("granted_by"):
                continue

            self._tree.insert(
                "",
                "end",
                values=(
                    u.get("email", ""),
                    u.get("role", "user"),
                    status,
                    u.get("activated_at", ""),
                    u.get("granted_by", ""),
                    u.get("grant_reason", ""),
                ),
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_grant(self):
        email = simpledialog.askstring(
            "Liberar Acesso",
            "Digite o e-mail do usuario:",
            parent=self,
        )
        if not email:
            return

        reason = simpledialog.askstring(
            "Motivo",
            "Motivo da liberacao (opcional):",
            parent=self,
        ) or ""

        try:
            grantor_id = (
                self.session.user.id if hasattr(self.session, "user") else "unknown"
            )
            self.auth.grant_access(email, grantor_id, reason)
            messagebox.showinfo("Sucesso", f"Acesso liberado para {email}.", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)

    def _on_revoke(self):
        selected = self._tree.focus()
        if not selected:
            messagebox.showwarning(
                "Selecione", "Selecione um usuario na tabela.", parent=self
            )
            return

        values = self._tree.item(selected, "values")
        email = values[0] if values else ""

        if not messagebox.askyesno(
            "Confirmar",
            f"Deseja revogar o acesso de {email}?",
            parent=self,
        ):
            return

        try:
            self.auth.revoke_access(email)
            messagebox.showinfo("Sucesso", f"Acesso revogado de {email}.", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)
