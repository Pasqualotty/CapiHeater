"""
TargetsTab - CRUD interface for managing target accounts/URLs.
"""

import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox


# Priority int <-> label mapping
PRIORITY_LABELS = {1: "Baixa", 2: "Media", 3: "Alta"}
PRIORITY_VALUES = {"Baixa": 1, "Media": 2, "Alta": 3}


class TargetsTab(ttk.Frame):
    """Targets management tab with treeview and CRUD dialogs.

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
        # Toolbar
        toolbar = ttk.Frame(self, style="Dark.TFrame")
        toolbar.pack(fill=tk.X, padx=12, pady=(12, 6))

        ttk.Label(toolbar, text="Gerenciamento de Alvos", style="Heading.TLabel").pack(side=tk.LEFT)

        btn_frame = ttk.Frame(toolbar, style="Dark.TFrame")
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Adicionar Alvo", style="Accent.TButton", command=self._add_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Adicionar em Massa", style="Accent.TButton", command=self._add_bulk_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Editar", style="Accent.TButton", command=self._edit_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Excluir", style="Danger.TButton", command=self._delete_targets).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Alternar Ativo", style="Accent.TButton", command=self._toggle_active).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Abrir Perfil", style="Accent.TButton", command=self._open_profile).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Categorias", style="Accent.TButton", command=self._manage_categories).pack(side=tk.LEFT)

        # ---------- Search bar ----------
        search_frame = ttk.Frame(self, style="Dark.TFrame")
        search_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        ttk.Label(search_frame, text="Pesquisar:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_tree())
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var, style="Dark.TEntry", width=20)
        search_entry.pack(side=tk.LEFT)

        ttk.Label(search_frame, text="Categoria:", style="Dark.TLabel").pack(side=tk.LEFT, padx=(12, 6))
        self._cat_filter_var = tk.StringVar(value="Todas")
        self._cat_filter_combo = ttk.Combobox(
            search_frame, textvariable=self._cat_filter_var,
            state="readonly", style="Dark.TCombobox", width=14,
        )
        self._cat_filter_combo.pack(side=tk.LEFT)
        self._cat_filter_combo.bind("<<ComboboxSelected>>", lambda *_: self._filter_tree())

        ttk.Button(search_frame, text="Limpar", command=self._clear_filters).pack(side=tk.LEFT, padx=(6, 0))

        # Treeview — extended selection for multi-select
        tree_frame = ttk.Frame(self, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("username", "url", "priority", "categoria", "active")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="extended",
        )

        self._tree.heading("username", text="Usuario")
        self._tree.heading("url", text="URL")
        self._tree.heading("priority", text="Prioridade")
        self._tree.heading("categoria", text="Categoria")
        self._tree.heading("active", text="Ativo")

        self._tree.column("username", width=140, anchor=tk.W)
        self._tree.column("url", width=260, anchor=tk.W)
        self._tree.column("priority", width=80, anchor=tk.CENTER)
        self._tree.column("categoria", width=120, anchor=tk.CENTER)
        self._tree.column("active", width=60, anchor=tk.CENTER)

        # Double-click opens profile
        self._tree.bind("<Double-1>", lambda _e: self._open_profile())
        # Right-click context menu
        self._tree.bind("<Button-3>", self._show_context_menu)
        # Ctrl+A to select all
        self._tree.bind("<Control-a>", self._select_all)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Selection info bar
        self._sel_info = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._sel_info, style="Dark.TLabel").pack(
            padx=12, pady=(0, 6), anchor=tk.W
        )

        self._row_map: dict[str, int] = {}
        self._url_map: dict[str, str] = {}

        # Update selection count on click
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

    # ==================================================================
    # Data
    # ==================================================================

    def refresh(self) -> None:
        targets = self.app.target_manager.get_targets(active_only=False)
        cat_mgr = self.app.category_manager

        self._all_targets = []
        for t in targets:
            priority_label = PRIORITY_LABELS.get(t.get("priority", 1), "Baixa")
            active_label = "Sim" if t.get("active", 1) else "Nao"
            cat_names = cat_mgr.get_target_category_names(t["id"])
            cat_label = ", ".join(cat_names) if cat_names else "—"
            self._all_targets.append({
                "id": t["id"],
                "url": t.get("url", ""),
                "cat_names": cat_names,
                "values": (
                    f"@{t.get('username', '???')}",
                    t.get("url", ""),
                    priority_label,
                    cat_label,
                    active_label,
                ),
            })

        # Update category filter combo
        all_cats = sorted({n for item in self._all_targets for n in item["cat_names"]})
        self._cat_filter_combo["values"] = ["Todas", "Sem categoria"] + all_cats
        if self._cat_filter_var.get() not in self._cat_filter_combo["values"]:
            self._cat_filter_var.set("Todas")

        self._filter_tree()

    def _clear_filters(self):
        self._search_var.set("")
        self._cat_filter_var.set("Todas")

    def _filter_tree(self) -> None:
        """Apply search and category filters and repopulate the treeview."""
        self._tree.delete(*self._tree.get_children())
        self._row_map.clear()
        self._url_map.clear()

        query = self._search_var.get().strip().lower()
        cat_filter = self._cat_filter_var.get()
        shown = 0

        for item in getattr(self, "_all_targets", []):
            username = item["values"][0].lower()
            if query and query not in username:
                continue
            if cat_filter == "Sem categoria" and item["cat_names"]:
                continue
            if cat_filter not in ("Todas", "Sem categoria") and cat_filter not in item["cat_names"]:
                continue
            iid = self._tree.insert("", tk.END, values=item["values"])
            self._row_map[iid] = item["id"]
            self._url_map[iid] = item["url"]
            shown += 1

        total = len(getattr(self, "_all_targets", []))
        if query or cat_filter != "Todas":
            self._sel_info.set(f"{shown}/{total} alvos encontrados")
        else:
            self._sel_info.set(f"{total} alvos | Ctrl+A = selecionar todos | Duplo clique = abrir perfil")

    def _get_selected_ids(self) -> list[int]:
        """Return list of selected target IDs."""
        sel = self._tree.selection()
        return [self._row_map[iid] for iid in sel if iid in self._row_map]

    def _get_selected_id(self) -> int | None:
        ids = self._get_selected_ids()
        return ids[0] if ids else None

    def _on_selection_changed(self, _event=None):
        count = len(self._tree.selection())
        if count == 0:
            self._sel_info.set("Nenhum selecionado")
        elif count == 1:
            self._sel_info.set("1 alvo selecionado")
        else:
            self._sel_info.set(f"{count} alvos selecionados")

    def _select_all(self, _event=None):
        all_items = self._tree.get_children()
        self._tree.selection_set(all_items)

    # ==================================================================
    # Context menu
    # ==================================================================

    def _show_context_menu(self, event):
        iid = self._tree.identify_row(event.y)
        if iid and iid not in self._tree.selection():
            self._tree.selection_set(iid)

        menu = tk.Menu(self, tearoff=0, bg="#16213e", fg="#e0e0e0", activebackground="#0f3460")
        menu.add_command(label="Abrir Perfil", command=self._open_profile)
        menu.add_separator()
        menu.add_command(label="Editar", command=self._edit_dialog)
        menu.add_command(label="Alternar Ativo", command=self._toggle_active)
        menu.add_separator()
        menu.add_command(label="Excluir Selecionados", command=self._delete_targets)
        menu.add_separator()
        menu.add_command(label="Selecionar Todos", command=self._select_all)
        menu.tk_popup(event.x_root, event.y_root)

    # ==================================================================
    # Bulk add dialog
    # ==================================================================

    def _add_bulk_dialog(self) -> None:
        """Open a dialog to add multiple targets at once via links or usernames."""
        import re

        dlg = tk.Toplevel(self)
        dlg.title("Adicionar Alvos em Massa")
        dlg.geometry("500x520")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, True)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        bg = "#1a1a2e"
        fg = "#ffffff"
        entry_bg = "#16213e"

        tk.Label(dlg, text="Adicionar Alvos em Massa", font=("Segoe UI", 13, "bold"),
                 bg=bg, fg=fg).pack(pady=(16, 4))

        tk.Label(dlg, text="Cole links ou usernames (um por linha):",
                 font=("Segoe UI", 9), bg=bg, fg="#9e9e9e").pack(anchor="w", padx=20)

        # Text area
        text_frame = tk.Frame(dlg, bg=bg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 8))

        self._bulk_text = tk.Text(
            text_frame, bg=entry_bg, fg=fg, insertbackground=fg,
            font=("Segoe UI", 10), relief="flat", highlightthickness=1,
            highlightcolor="#0f3460", wrap="word",
        )
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._bulk_text.yview)
        self._bulk_text.configure(yscrollcommand=scrollbar.set)
        self._bulk_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Example hint
        tk.Label(dlg, text="Exemplos aceitos:\nhttps://x.com/usuario\nhttps://twitter.com/usuario\n@usuario\nusuario",
                 font=("Segoe UI", 8), bg=bg, fg="#666688", justify="left").pack(anchor="w", padx=20)

        # Priority + Category row
        opts_frame = tk.Frame(dlg, bg=bg)
        opts_frame.pack(fill=tk.X, padx=20, pady=(8, 4))

        tk.Label(opts_frame, text="Prioridade:", font=("Segoe UI", 10), bg=bg, fg=fg).pack(side=tk.LEFT)
        prio_combo = ttk.Combobox(opts_frame, values=["Baixa", "Media", "Alta"],
                                   state="readonly", style="Dark.TCombobox", width=10)
        prio_combo.pack(side=tk.LEFT, padx=(8, 16))
        prio_combo.set("Alta")

        # Categories (multi-select listbox)
        cat_frame = tk.Frame(dlg, bg=bg)
        cat_frame.pack(fill=tk.X, padx=20, pady=(4, 4))

        tk.Label(cat_frame, text="Categorias (Ctrl+clique para multiplas):",
                 font=("Segoe UI", 9), bg=bg, fg="#9e9e9e").pack(anchor="w")

        cat_names_map = self.app.category_manager.get_category_names()
        cat_list = list(cat_names_map.values())
        cat_ids = list(cat_names_map.keys())

        bulk_cat_listbox = tk.Listbox(
            cat_frame, selectmode=tk.MULTIPLE, height=4, width=40,
            bg="#0d1b2a", fg="#e0e0e0", selectbackground="#1a73e8",
            relief="flat", highlightthickness=0, font=("Segoe UI", 9),
        )
        bulk_cat_listbox.pack(fill=tk.X)
        for name in cat_list:
            bulk_cat_listbox.insert(tk.END, name)

        # Buttons
        btn_frame = tk.Frame(dlg, bg=bg)
        btn_frame.pack(pady=12)

        def on_add():
            raw = self._bulk_text.get("1.0", tk.END).strip()
            if not raw:
                messagebox.showwarning("Aviso", "Cole pelo menos um link ou username.", parent=dlg)
                return

            priority = PRIORITY_VALUES.get(prio_combo.get(), 3)
            selected_cat_ids = [cat_ids[i] for i in bulk_cat_listbox.curselection()]
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
                    new_id = self.app.target_manager.add_target(username=username, url=url, priority=priority)
                    if selected_cat_ids:
                        self.app.category_manager.set_target_categories(new_id, selected_cat_ids)
                    added += 1
                except Exception:
                    skipped += 1  # Probably duplicate

            dlg.destroy()
            self.refresh()
            self.app.set_status(f"{added} alvo(s) adicionado(s), {skipped} ignorado(s)")
            messagebox.showinfo("Resultado",
                                f"{added} alvo(s) adicionado(s) com sucesso!\n{skipped} ignorado(s) (duplicados ou invalidos).",
                                parent=self)

        tk.Button(btn_frame, text="Adicionar Todos", font=("Segoe UI", 10, "bold"),
                  bg="#0f3460", fg=fg, relief="flat", padx=16, pady=4,
                  command=on_add).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Cancelar", font=("Segoe UI", 10),
                  bg="#333355", fg=fg, relief="flat", padx=16, pady=4,
                  command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    @staticmethod
    def _extract_username(text: str) -> str | None:
        """Extract a Twitter username from a URL or raw text."""
        import re
        text = text.strip().rstrip("/")

        # Match https://x.com/username or https://twitter.com/username
        match = re.match(r'https?://(?:www\.)?(?:x|twitter)\.com/(@?[\w]+)', text)
        if match:
            return match.group(1).lstrip("@")

        # Match @username
        match = re.match(r'^@([\w]+)$', text)
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

    def _add_dialog(self) -> None:
        self._open_target_form(title="Adicionar Alvo", target=None)

    def _edit_dialog(self) -> None:
        tid = self._get_selected_id()
        if tid is None:
            messagebox.showwarning("Aviso", "Selecione um alvo para editar.", parent=self)
            return
        target = self.app.target_manager.get_target(tid)
        if target is None:
            return
        self._open_target_form(title="Editar Alvo", target=target)

    def _open_target_form(self, title: str, target: dict | None) -> None:
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("440x400")
        dlg.configure(bg="#1a1a2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        pad = {"padx": 12, "pady": 4}

        # Username
        ttk.Label(dlg, text="Usuario alvo (sem @):", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        ent_user = ttk.Entry(dlg, style="Dark.TEntry", width=40)
        ent_user.pack(**pad)

        # URL
        ttk.Label(dlg, text="URL do perfil:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        ent_url = ttk.Entry(dlg, style="Dark.TEntry", width=40)
        ent_url.pack(**pad)

        # Auto-fill URL from username
        def on_username_change(*_args):
            user = ent_user.get().strip().lstrip("@")
            if user and not ent_url.get().strip():
                ent_url.delete(0, tk.END)
                ent_url.insert(0, f"https://x.com/{user}")

        ent_user.bind("<FocusOut>", on_username_change)

        # Priority
        ttk.Label(dlg, text="Prioridade:", style="Dark.TLabel").pack(anchor=tk.W, **pad)
        combo_prio = ttk.Combobox(
            dlg, values=["Baixa", "Media", "Alta"], state="readonly", style="Dark.TCombobox", width=37,
        )
        combo_prio.pack(**pad)

        # Categories (multi-select)
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

        if target:
            ent_user.insert(0, target.get("username", ""))
            ent_url.insert(0, target.get("url", ""))
            prio_label = PRIORITY_LABELS.get(target.get("priority", 1), "Baixa")
            combo_prio.set(prio_label)
            # Pre-select existing categories
            existing_cats = set(self.app.category_manager.get_target_categories(target["id"]))
            for i, cid in enumerate(cat_ids):
                if cid in existing_cats:
                    cat_listbox.selection_set(i)
        else:
            combo_prio.current(0)

        # Save
        def save():
            username = ent_user.get().strip().lstrip("@")
            url = ent_url.get().strip()
            if not username:
                messagebox.showerror("Erro", "O nome de usuario e obrigatorio.", parent=dlg)
                return
            if not url:
                url = f"https://x.com/{username}"

            priority = PRIORITY_VALUES.get(combo_prio.get(), 1)
            selected_cat_ids = [cat_ids[i] for i in cat_listbox.curselection()]

            if target:
                self.app.target_manager.update_target(
                    target["id"], username=username, url=url, priority=priority,
                )
                self.app.category_manager.set_target_categories(target["id"], selected_cat_ids)
                self.app.set_status(f"Alvo @{username} atualizado")
            else:
                new_id = self.app.target_manager.add_target(username=username, url=url, priority=priority)
                if selected_cat_ids:
                    self.app.category_manager.set_target_categories(new_id, selected_cat_ids)
                self.app.set_status(f"Alvo @{username} adicionado")

            dlg.destroy()
            self.refresh()

        ttk.Button(dlg, text="Salvar", style="Accent.TButton", command=save).pack(pady=12)

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
    # Actions
    # ==================================================================

    def _open_profile(self) -> None:
        """Open selected profiles in the default browser."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um ou mais alvos.", parent=self)
            return
        for iid in sel:
            url = self._url_map.get(iid, "")
            if url:
                webbrowser.open(url)

    def _delete_targets(self) -> None:
        """Delete all selected targets."""
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione um ou mais alvos para excluir.", parent=self)
            return

        count = len(ids)
        msg = f"Excluir {count} alvo(s) selecionado(s)?" if count > 1 else "Excluir este alvo?"
        if not messagebox.askyesno("Confirmar", msg, parent=self):
            return

        for tid in ids:
            self.app.target_manager.delete_target(tid)

        self.app.set_status(f"{count} alvo(s) excluido(s)")
        self.refresh()

    def _toggle_active(self) -> None:
        """Toggle active status for all selected targets."""
        ids = self._get_selected_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione um ou mais alvos.", parent=self)
            return

        for tid in ids:
            self.app.target_manager.toggle_active(tid)

        self.app.set_status(f"{len(ids)} alvo(s) alternado(s)")
        self.refresh()
