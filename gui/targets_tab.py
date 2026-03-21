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
        ttk.Button(btn_frame, text="Editar", style="Accent.TButton", command=self._edit_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Excluir", style="Danger.TButton", command=self._delete_targets).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Alternar Ativo", style="Accent.TButton", command=self._toggle_active).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Abrir Perfil", style="Accent.TButton", command=self._open_profile).pack(side=tk.LEFT)

        # Treeview — extended selection for multi-select
        tree_frame = ttk.Frame(self, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        columns = ("username", "url", "priority", "active")
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
        self._tree.heading("active", text="Ativo")

        self._tree.column("username", width=160, anchor=tk.W)
        self._tree.column("url", width=320, anchor=tk.W)
        self._tree.column("priority", width=100, anchor=tk.CENTER)
        self._tree.column("active", width=80, anchor=tk.CENTER)

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
        self._tree.delete(*self._tree.get_children())
        self._row_map.clear()
        self._url_map.clear()

        targets = self.app.target_manager.get_targets(active_only=False)
        for t in targets:
            priority_label = PRIORITY_LABELS.get(t.get("priority", 1), "Baixa")
            active_label = "Sim" if t.get("active", 1) else "Nao"
            iid = self._tree.insert(
                "",
                tk.END,
                values=(
                    f"@{t.get('username', '???')}",
                    t.get("url", ""),
                    priority_label,
                    active_label,
                ),
            )
            self._row_map[iid] = t["id"]
            self._url_map[iid] = t.get("url", "")

        self._sel_info.set(f"{len(targets)} alvos | Ctrl+A = selecionar todos | Duplo clique = abrir perfil")

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
        dlg.geometry("440x280")
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

        if target:
            ent_user.insert(0, target.get("username", ""))
            ent_url.insert(0, target.get("url", ""))
            prio_label = PRIORITY_LABELS.get(target.get("priority", 1), "Baixa")
            combo_prio.set(prio_label)
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

            if target:
                self.app.target_manager.update_target(
                    target["id"], username=username, url=url, priority=priority,
                )
                self.app.set_status(f"Alvo @{username} atualizado")
            else:
                self.app.target_manager.add_target(username=username, url=url, priority=priority)
                self.app.set_status(f"Alvo @{username} adicionado")

            dlg.destroy()
            self.refresh()

        ttk.Button(dlg, text="Salvar", style="Accent.TButton", command=save).pack(pady=12)

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
