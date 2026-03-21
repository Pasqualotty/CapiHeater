"""
SettingsTab - Application settings with persistence.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class SettingsTab(ttk.Frame):
    """Settings tab for configuring application-wide preferences.

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
        self._load_settings()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        ttk.Label(header, text="Configuracoes", style="Heading.TLabel").pack(side=tk.LEFT)

        # Settings form
        form = ttk.LabelFrame(self, text="Geral", style="Dark.TLabelframe")
        form.pack(fill=tk.X, padx=12, pady=12)

        pad = {"padx": 12, "pady": 6}

        # Max concurrent workers
        row0 = ttk.Frame(form, style="Dark.TFrame")
        row0.pack(fill=tk.X, **pad)
        ttk.Label(row0, text="Workers simultaneos (max):", style="Dark.TLabel").pack(side=tk.LEFT)
        self._spin_workers = ttk.Spinbox(
            row0,
            from_=1,
            to=10,
            width=5,
            style="Dark.TSpinbox",
        )
        self._spin_workers.pack(side=tk.RIGHT)

        # Headless mode
        row1 = ttk.Frame(form, style="Dark.TFrame")
        row1.pack(fill=tk.X, **pad)
        self._headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row1,
            text="Modo headless (navegador invisivel)",
            variable=self._headless_var,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT)

        # Default proxy
        row2 = ttk.Frame(form, style="Dark.TFrame")
        row2.pack(fill=tk.X, **pad)
        ttk.Label(row2, text="Proxy padrao:", style="Dark.TLabel").pack(side=tk.LEFT)
        self._ent_proxy = ttk.Entry(row2, style="Dark.TEntry", width=32)
        self._ent_proxy.pack(side=tk.RIGHT)

        # Log level
        row3 = ttk.Frame(form, style="Dark.TFrame")
        row3.pack(fill=tk.X, **pad)
        ttk.Label(row3, text="Nivel de log:", style="Dark.TLabel").pack(side=tk.LEFT)
        self._combo_log = ttk.Combobox(
            row3,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            style="Dark.TCombobox",
            width=12,
        )
        self._combo_log.pack(side=tk.RIGHT)

        # Save button
        btn_frame = ttk.Frame(self, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(btn_frame, text="Salvar Configuracoes", style="Accent.TButton", command=self._save_settings).pack(side=tk.LEFT)

    # ==================================================================
    # Persistence
    # ==================================================================

    def _get_setting(self, key: str, default: str = "") -> str:
        row = self.app.db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        if row:
            return row.get("value", default)
        return default

    def _set_setting(self, key: str, value: str) -> None:
        existing = self.app.db.fetch_one("SELECT key FROM settings WHERE key = ?", (key,))
        if existing:
            self.app.db.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
        else:
            self.app.db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    def _load_settings(self) -> None:
        """Load settings from database and populate the form."""
        workers = self._get_setting("max_workers", "3")
        self._spin_workers.delete(0, tk.END)
        self._spin_workers.insert(0, workers)

        headless = self._get_setting("headless", "0")
        self._headless_var.set(headless == "1")

        proxy = self._get_setting("default_proxy", "")
        self._ent_proxy.delete(0, tk.END)
        self._ent_proxy.insert(0, proxy)

        log_level = self._get_setting("log_level", "INFO")
        self._combo_log.set(log_level)

    def _save_settings(self) -> None:
        """Persist current form values to the settings table."""
        try:
            workers = int(self._spin_workers.get())
            workers = max(1, min(10, workers))
        except ValueError:
            workers = 3

        self._set_setting("max_workers", str(workers))
        self._set_setting("headless", "1" if self._headless_var.get() else "0")
        self._set_setting("default_proxy", self._ent_proxy.get().strip())
        self._set_setting("log_level", self._combo_log.get())

        # Apply max_workers to engine immediately
        self.app.engine.max_concurrent = workers

        self.app.set_status("Configuracoes salvas com sucesso")
        messagebox.showinfo("Sucesso", "Configuracoes salvas com sucesso.", parent=self)
