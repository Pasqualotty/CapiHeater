"""
AccountsTab - CRUD interface for managing Twitter/X accounts.
"""

import json
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date

from utils.config import DEFAULT_SCROLL_CONFIG, SCROLL_PRESETS


class AccountsTab(ttk.Frame):
    """Accounts management tab with treeview table and CRUD dialogs.

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
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # ---------- Toolbar ----------
        toolbar = ttk.Frame(self, style="Dark.TFrame")
        toolbar.pack(fill=tk.X, padx=12, pady=(12, 6))

        ttk.Label(toolbar, text="Gerenciamento de Contas", style="Heading.TLabel").pack(side=tk.LEFT)

        btn_frame = ttk.Frame(toolbar, style="Dark.TFrame")
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Adicionar Conta", style="Accent.TButton", command=self._add_account_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Editar", style="Accent.TButton", command=self._edit_account_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Excluir", style="Danger.TButton", command=self._delete_account).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Importar Cookies", style="Accent.TButton", command=self._import_cookies).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Importar em Massa", style="Accent.TButton", command=self._bulk_import).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Reiniciar Cronograma", style="Danger.TButton", command=self._reset_schedule).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Categorias", style="Accent.TButton", command=self._manage_categories).pack(side=tk.LEFT)

        # ---------- Search bar ----------
        search_frame = ttk.Frame(self, style="Dark.TFrame")
        search_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        ttk.Label(search_frame, text="Pesquisar:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_tree())
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var, style="Dark.TEntry", width=30)
        search_entry.pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Limpar", command=lambda: self._search_var.set("")).pack(side=tk.LEFT, padx=(6, 0))

        # ---------- Treeview ----------
        tree_frame = ttk.Frame(self, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("username", "status", "schedule", "categoria", "dia", "proxy", "start_date")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="extended",
        )

        self._tree.heading("username", text="Usuario")
        self._tree.heading("status", text="Status")
        self._tree.heading("schedule", text="Cronograma")
        self._tree.heading("categoria", text="Categoria")
        self._tree.heading("dia", text="Dia")
        self._tree.heading("proxy", text="Proxy")
        self._tree.heading("start_date", text="Data Inicio")

        self._tree.column("username", width=140, anchor=tk.W)
        self._tree.column("status", width=80, anchor=tk.CENTER)
        self._tree.column("schedule", width=120, anchor=tk.CENTER)
        self._tree.column("categoria", width=120, anchor=tk.CENTER)
        self._tree.column("dia", width=50, anchor=tk.CENTER)
        self._tree.column("proxy", width=150, anchor=tk.W)
        self._tree.column("start_date", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store mapping iid -> account_id
        self._row_map: dict[str, int] = {}

        # Bindings
        self._tree.bind("<Control-a>", self._select_all)
        self._tree.bind("<Button-3>", self._show_context_menu)
        self._tree.bind("<Double-1>", lambda _e: self._open_profile())
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        # Selection info
        sel_frame = ttk.Frame(self, style="Dark.TFrame")
        sel_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        self._sel_info = tk.StringVar(value="")
        ttk.Label(sel_frame, textvariable=self._sel_info, style="Dark.TLabel").pack(side=tk.LEFT)

    # ==================================================================
    # Selection helpers
    # ==================================================================

    def _select_all(self, _event=None):
        self._tree.selection_set(self._tree.get_children())

    def _on_selection_changed(self, _event=None):
        count = len(self._tree.selection())
        if count == 0:
            self._sel_info.set("")
        elif count == 1:
            self._sel_info.set("1 conta selecionada")
        else:
            self._sel_info.set(f"{count} contas selecionadas")

    def _show_context_menu(self, event):
        iid = self._tree.identify_row(event.y)
        if iid and iid not in self._tree.selection():
            self._tree.selection_set(iid)

        menu = tk.Menu(self, tearoff=0, bg="#16213e", fg="#e0e0e0", activebackground="#0f3460")
        menu.add_command(label="Abrir Perfil", command=self._open_profile)
        menu.add_separator()
        menu.add_command(label="Editar", command=self._edit_account_dialog)
        menu.add_command(label="Importar Cookies", command=self._import_cookies)
        menu.add_command(label="Alternar Ativo", command=self._toggle_active)
        menu.add_separator()
        menu.add_command(label="Reiniciar Cronograma", command=self._reset_schedule)
        menu.add_command(label="Excluir Selecionados", command=self._delete_account)
        menu.add_separator()
        menu.add_command(label="Selecionar Todos", command=self._select_all)
        menu.tk_popup(event.x_root, event.y_root)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        """Reload accounts from the database into the treeview."""
        accounts = self.app.account_manager.get_all_accounts()
        schedules = self._get_schedule_names()
        cat_mgr = self.app.category_manager

        self._all_accounts = []
        for acc in accounts:
            sched_name = schedules.get(acc.get("schedule_id", 1), "Padrao")
            status_label = self._status_label(acc.get("status", "idle"))
            proxy = acc.get("proxy") or "—"
            cat_names = cat_mgr.get_account_category_names(acc["id"])
            cat_label = ", ".join(cat_names) if cat_names else "—"
            self._all_accounts.append({
                "id": acc["id"],
                "username": acc.get("username", "???"),
                "values": (
                    f"@{acc.get('username', '???')}",
                    status_label,
                    sched_name,
                    cat_label,
                    acc.get("current_day", 1),
                    proxy,
                    acc.get("start_date", ""),
                ),
            })

        self._filter_tree()

    def _filter_tree(self) -> None:
        """Apply the search filter and repopulate the treeview."""
        self._tree.delete(*self._tree.get_children())
        self._row_map.clear()
        self._username_map: dict[str, str] = {}

        query = self._search_var.get().strip().lower()

        for item in getattr(self, "_all_accounts", []):
            display_name = item["values"][0].lower()
            if query and query not in display_name:
                continue
            iid = self._tree.insert("", tk.END, values=item["values"])
            self._row_map[iid] = item["id"]
            self._username_map[iid] = item["username"]

    def _get_schedule_names(self) -> dict[int, str]:
        rows = self.app.db.fetch_all("SELECT id, name FROM schedules ORDER BY id")
        return {r["id"]: r["name"] for r in rows}

    def _get_selected_ids(self) -> list[int]:
        """Return list of selected account IDs."""
        sel = self._tree.selection()
        return [self._row_map[iid] for iid in sel if iid in self._row_map]

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
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas para editar.", parent=self)
            return
        if len(ids) == 1:
            account = self.app.account_manager.get_account(ids[0])
            if account is None:
                return
            self._open_account_form(title="Editar Conta", account=account)
        else:
            self._open_bulk_edit_form(ids)

    def _open_account_form(self, title: str, account: dict | None) -> None:
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("460x580")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        pad = {"padx": 12, "pady": 4}

        # Username
        ttk.Label(dlg, text="Usuario (sem @):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        ent_user = ttk.Entry(dlg, style="Dark.TEntry", width=40)
        ent_user.pack(**pad)
        if account:
            ent_user.insert(0, account.get("username", ""))

        # Cookies file
        ttk.Label(dlg, text="Arquivo de Cookies (.json / .txt):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        cookie_frame = ttk.Frame(dlg, style="Dark.TFrame")
        cookie_frame.pack(fill=tk.X, **pad)

        cookie_var = tk.StringVar()
        ent_cookie = ttk.Entry(cookie_frame, textvariable=cookie_var, style="Dark.TEntry", width=32)
        ent_cookie.pack(side=tk.LEFT, padx=(0, 4))

        def browse_cookies():
            path = filedialog.askopenfilename(
                title="Selecionar arquivo de cookies",
                filetypes=[("JSON", "*.json"), ("Netscape TXT", "*.txt"), ("Todos", "*.*")],
                parent=dlg,
            )
            if path:
                cookie_var.set(path)

        ttk.Button(cookie_frame, text="Procurar...", command=browse_cookies).pack(side=tk.LEFT)

        # Proxy
        ttk.Label(dlg, text="Proxy (opcional):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        ent_proxy = ttk.Entry(dlg, style="Dark.TEntry", width=40)
        ent_proxy.pack(**pad)
        if account and account.get("proxy"):
            ent_proxy.insert(0, account["proxy"])

        # Schedule dropdown
        ttk.Label(dlg, text="Cronograma:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        schedule_names = self._get_schedule_names()
        schedule_list = list(schedule_names.values()) or ["Padrao"]
        schedule_ids = list(schedule_names.keys()) or [1]
        combo_sched = ttk.Combobox(dlg, values=schedule_list, state="readonly", style="Dark.TCombobox", width=37)
        combo_sched.pack(**pad)
        if account:
            idx = schedule_ids.index(account.get("schedule_id", 1)) if account.get("schedule_id", 1) in schedule_ids else 0
            combo_sched.current(idx)
        elif schedule_list:
            combo_sched.current(0)

        # Categories (multi-select listbox)
        ttk.Label(dlg, text="Categorias (Ctrl+clique para multiplas):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        cat_names = self.app.category_manager.get_category_names()
        cat_list = list(cat_names.values())
        cat_ids = list(cat_names.keys())

        cat_listbox = tk.Listbox(
            dlg, selectmode=tk.MULTIPLE, height=4, width=40,
            bg="#0d1b2a", fg="#e0e0e0", selectbackground="#1a73e8",
            relief="flat", highlightthickness=0,
        )
        cat_listbox.pack(**pad)
        for name in cat_list:
            cat_listbox.insert(tk.END, name)

        # Pre-select existing categories
        if account:
            existing_cats = set(self.app.category_manager.get_account_categories(account["id"]))
            for i, cid in enumerate(cat_ids):
                if cid in existing_cats:
                    cat_listbox.selection_set(i)

        # Scroll config (per-account override)
        ttk.Label(dlg, text="Perfil de rolagem:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        scroll_preset_names = ["Padrao Global", "Lento", "Normal", "Rapido"]
        combo_scroll = ttk.Combobox(
            dlg, values=scroll_preset_names, state="readonly",
            style="Dark.TCombobox", width=37,
        )
        combo_scroll.pack(**pad)
        # Determine current preset for this account
        if account and account.get("scroll_config"):
            try:
                acct_cfg = json.loads(account["scroll_config"]) if isinstance(account["scroll_config"], str) else account["scroll_config"]
            except (json.JSONDecodeError, TypeError):
                acct_cfg = None
            matched = False
            if acct_cfg:
                for pname, pdata in SCROLL_PRESETS.items():
                    ref = pdata if pdata else DEFAULT_SCROLL_CONFIG
                    if acct_cfg == ref:
                        combo_scroll.set(pname)
                        matched = True
                        break
                if not matched:
                    # Check if it matches Normal (DEFAULT_SCROLL_CONFIG)
                    if acct_cfg == DEFAULT_SCROLL_CONFIG:
                        combo_scroll.set("Normal")
                    else:
                        scroll_preset_names.append("Personalizado")
                        combo_scroll["values"] = scroll_preset_names
                        combo_scroll.set("Personalizado")
            else:
                combo_scroll.set("Padrao Global")
        else:
            combo_scroll.set("Padrao Global")

        # Notes
        ttk.Label(dlg, text="Notas:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        txt_notes = tk.Text(dlg, height=3, width=40, bg="#0d1b2a", fg="#e0e0e0", insertbackground="#e0e0e0", relief="flat")
        txt_notes.pack(**pad)
        if account and account.get("notes"):
            txt_notes.insert("1.0", account["notes"])

        # Save button
        def save():
            username = ent_user.get().strip().lstrip("@")
            if not username:
                messagebox.showerror("Erro", "O nome de usuario e obrigatorio.", parent=dlg)
                return

            proxy = ent_proxy.get().strip() or None
            sched_idx = combo_sched.current()
            sched_id = schedule_ids[sched_idx] if sched_idx >= 0 else 1
            notes = txt_notes.get("1.0", tk.END).strip()

            # Resolve scroll config from preset selection
            scroll_choice = combo_scroll.get()
            if scroll_choice == "Padrao Global":
                scroll_config_json = None
            elif scroll_choice == "Personalizado":
                # Keep existing custom config unchanged
                scroll_config_json = account.get("scroll_config") if account else None
            else:
                preset_data = SCROLL_PRESETS.get(scroll_choice)
                scroll_config_json = json.dumps(preset_data if preset_data else DEFAULT_SCROLL_CONFIG)

            # Get selected categories
            selected_cat_ids = [cat_ids[i] for i in cat_listbox.curselection()]

            if account:
                # Edit mode
                updates = {
                    "username": username,
                    "proxy": proxy,
                    "schedule_id": sched_id,
                    "scroll_config": scroll_config_json,
                    "notes": notes,
                }
                cookie_path = cookie_var.get().strip()
                if cookie_path:
                    cookies = self._load_cookies(cookie_path)
                    if cookies is not None:
                        updates["cookies_json"] = cookies
                self.app.account_manager.update_account(account["id"], **updates)
                self.app.category_manager.set_account_categories(account["id"], selected_cat_ids)
                self.app.set_status(f"Conta @{username} atualizada")
            else:
                # Add mode
                cookie_path = cookie_var.get().strip()
                if not cookie_path:
                    messagebox.showerror("Erro", "Selecione o arquivo de cookies.", parent=dlg)
                    return
                cookies = self._load_cookies(cookie_path)
                if cookies is None:
                    messagebox.showerror("Erro", "Falha ao carregar cookies.", parent=dlg)
                    return
                new_id = self.app.account_manager.add_account(
                    username=username,
                    cookies_json=cookies,
                    proxy=proxy,
                    schedule_id=sched_id,
                    start_date=date.today().isoformat(),
                )
                # Save per-account scroll config if not global default
                if scroll_config_json is not None:
                    self.app.account_manager.update_account(new_id, scroll_config=scroll_config_json)
                if selected_cat_ids:
                    self.app.category_manager.set_account_categories(new_id, selected_cat_ids)
                self.app.set_status(f"Conta @{username} adicionada")

            dlg.destroy()
            self.refresh()

        ttk.Button(dlg, text="Salvar", style="Accent.TButton", command=save).pack(pady=12)

    # ==================================================================
    # Bulk edit
    # ==================================================================

    def _open_bulk_edit_form(self, account_ids: list[int]) -> None:
        """Edit shared fields across multiple accounts at once."""
        count = len(account_ids)
        dlg = tk.Toplevel(self)
        dlg.title(f"Editar {count} Contas")
        dlg.geometry("460x480")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        pad = {"padx": 12, "pady": 4}
        bg = "#1a1a2e"

        ttk.Label(
            dlg,
            text=f"Editando {count} contas simultaneamente",
            style="Heading.TLabel",
        ).pack(anchor=tk.W, padx=12, pady=(12, 4))

        ttk.Label(
            dlg,
            text="Apenas os campos alterados serao aplicados.\n"
                 "Deixe em branco ou no padrao para nao alterar.",
            style="Dark.TLabel",
        ).pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Proxy
        ttk.Label(dlg, text="Proxy (deixe vazio para nao alterar):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        ent_proxy = ttk.Entry(dlg, style="Dark.TEntry", width=40)
        ent_proxy.pack(**pad)

        # Schedule
        ttk.Label(dlg, text="Cronograma:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        schedule_names = self._get_schedule_names()
        schedule_list = ["— Nao alterar —"] + list(schedule_names.values())
        schedule_ids = [None] + list(schedule_names.keys())
        combo_sched = ttk.Combobox(dlg, values=schedule_list, state="readonly", style="Dark.TCombobox", width=37)
        combo_sched.pack(**pad)
        combo_sched.current(0)

        # Categories
        ttk.Label(dlg, text="Categorias (selecione para SUBSTITUIR, vazio = nao alterar):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        cat_names = self.app.category_manager.get_category_names()
        cat_list = list(cat_names.values())
        cat_ids = list(cat_names.keys())

        cat_listbox = tk.Listbox(
            dlg, selectmode=tk.MULTIPLE, height=4, width=40,
            bg="#0d1b2a", fg="#e0e0e0", selectbackground="#1a73e8",
            relief="flat", highlightthickness=0,
        )
        cat_listbox.pack(**pad)
        for name in cat_list:
            cat_listbox.insert(tk.END, name)

        # Scroll config
        ttk.Label(dlg, text="Perfil de rolagem:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        scroll_options = ["— Nao alterar —", "Padrao Global", "Lento", "Normal", "Rapido"]
        combo_scroll = ttk.Combobox(dlg, values=scroll_options, state="readonly", style="Dark.TCombobox", width=37)
        combo_scroll.pack(**pad)
        combo_scroll.current(0)

        # Notes
        ttk.Label(dlg, text="Notas (deixe vazio para nao alterar):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        txt_notes = tk.Text(dlg, height=3, width=40, bg="#0d1b2a", fg="#e0e0e0", insertbackground="#e0e0e0", relief="flat")
        txt_notes.pack(**pad)

        def save():
            updates = {}
            changed = 0

            # Proxy
            proxy_val = ent_proxy.get().strip()
            if proxy_val:
                updates["proxy"] = proxy_val
                changed += 1

            # Schedule
            sched_idx = combo_sched.current()
            sched_id = schedule_ids[sched_idx]
            if sched_id is not None:
                updates["schedule_id"] = sched_id
                changed += 1

            # Scroll config
            scroll_choice = combo_scroll.get()
            if scroll_choice != "— Nao alterar —":
                if scroll_choice == "Padrao Global":
                    updates["scroll_config"] = None
                else:
                    preset_data = SCROLL_PRESETS.get(scroll_choice)
                    updates["scroll_config"] = json.dumps(preset_data if preset_data else DEFAULT_SCROLL_CONFIG)
                changed += 1

            # Notes
            notes_val = txt_notes.get("1.0", tk.END).strip()
            if notes_val:
                updates["notes"] = notes_val
                changed += 1

            # Categories
            selected_cat_ids = [cat_ids[i] for i in cat_listbox.curselection()]
            cat_changed = len(cat_listbox.curselection()) > 0

            if changed == 0 and not cat_changed:
                messagebox.showinfo("Info", "Nenhum campo foi alterado.", parent=dlg)
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

            dlg.destroy()
            self.refresh()
            self.app.set_status(f"{count} conta(s) atualizadas ({', '.join(fields)})")

        ttk.Button(dlg, text="Aplicar a Todas", style="Accent.TButton", command=save).pack(pady=12)

    # ==================================================================
    # Actions
    # ==================================================================

    def _open_profile(self) -> None:
        """Open selected accounts' Twitter/X profiles in the browser."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas.", parent=self)
            return
        for iid in sel:
            username = self._username_map.get(iid, "")
            if username:
                webbrowser.open(f"https://x.com/{username}")

    def _toggle_active(self) -> None:
        """Toggle status between idle and paused for selected accounts."""
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas.", parent=self)
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
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas.", parent=self)
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
        if not messagebox.askyesno("Reiniciar Cronograma", msg, parent=self):
            return
        for aid in ids:
            self.app.account_manager.reset_schedule(aid)
        self.app.set_status(f"Cronograma reiniciado para {count} conta(s)")
        self.refresh()

    def _delete_account(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas para excluir.", parent=self)
            return
        count = len(ids)
        msg = f"Excluir {count} conta(s) selecionada(s)?" if count > 1 else "Excluir esta conta?"
        if not messagebox.askyesno("Confirmar", msg, parent=self):
            return
        for aid in ids:
            self.app.account_manager.delete_account(aid)
        self.app.set_status(f"{count} conta(s) excluida(s)")
        self.refresh()

    def _import_cookies(self) -> None:
        """Import cookies from a file and assign to selected accounts."""
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione uma ou mais contas para importar cookies.", parent=self)
            return

        path = filedialog.askopenfilename(
            title="Selecionar arquivo de cookies",
            filetypes=[("JSON", "*.json"), ("Netscape TXT", "*.txt"), ("Todos", "*.*")],
            parent=self,
        )
        if not path:
            return

        cookies = self._load_cookies(path)
        if cookies is None:
            messagebox.showerror("Erro", "Falha ao carregar cookies do arquivo.", parent=self)
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
        file_paths = filedialog.askopenfilenames(
            title="Selecionar arquivos de cookies (multiplos)",
            filetypes=[("JSON files", "*.json"), ("Todos", "*.*")],
            parent=self,
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

        messagebox.showinfo("Importacao em Massa", "\n".join(lines), parent=self)
        self.app.set_status(f"{len(successes)} conta(s) importada(s)")
        self.refresh()

    # ==================================================================
    # Category management dialog
    # ==================================================================

    def _manage_categories(self) -> None:
        """Open a dialog to create and delete categories."""
        dlg = tk.Toplevel(self)
        dlg.title("Gerenciar Categorias")
        dlg.geometry("380x400")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        bg = "#1a1a2e"
        fg = "#e0e0e0"

        ttk.Label(dlg, text="Categorias", style="Heading.TLabel").pack(pady=(12, 6))

        # Listbox
        list_frame = tk.Frame(dlg, bg=bg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        cat_listbox = tk.Listbox(
            list_frame, bg="#0d1b2a", fg=fg, selectbackground="#1a73e8",
            relief="flat", highlightthickness=0, font=("Segoe UI", 10),
        )
        cat_listbox.pack(fill=tk.BOTH, expand=True)

        def refresh_list():
            cat_listbox.delete(0, tk.END)
            for cat in self.app.category_manager.get_all_categories():
                cat_listbox.insert(tk.END, cat["name"])

        refresh_list()

        # Add section
        add_frame = tk.Frame(dlg, bg=bg)
        add_frame.pack(fill=tk.X, padx=12, pady=8)

        ent_name = ttk.Entry(add_frame, style="Dark.TEntry", width=25)
        ent_name.pack(side=tk.LEFT, padx=(0, 6))

        def on_add():
            name = ent_name.get().strip()
            if not name:
                return
            try:
                self.app.category_manager.add_category(name)
                ent_name.delete(0, tk.END)
                refresh_list()
            except Exception:
                messagebox.showerror("Erro", "Categoria ja existe ou nome invalido.", parent=dlg)

        ttk.Button(add_frame, text="Adicionar", style="Accent.TButton", command=on_add).pack(side=tk.LEFT)

        # Delete button
        def on_delete():
            sel = cat_listbox.curselection()
            if not sel:
                return
            selected_name = cat_listbox.get(sel[0])
            cats = self.app.category_manager.get_all_categories()
            cat = next((c for c in cats if c["name"] == selected_name), None)
            if cat is None:
                refresh_list()
                return
            if not messagebox.askyesno("Confirmar", f"Excluir categoria '{cat['name']}'?", parent=dlg):
                return
            self.app.category_manager.delete_category(cat["id"])
            refresh_list()

        ttk.Button(dlg, text="Excluir Selecionada", style="Danger.TButton", command=on_delete).pack(pady=(0, 12))

        def on_close():
            dlg.destroy()
            self.refresh()

        dlg.protocol("WM_DELETE_WINDOW", on_close)

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
