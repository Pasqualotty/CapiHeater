"""
SettingsTab - Application settings with persistence.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox

from utils.config import DEFAULT_SCROLL_CONFIG, SCROLL_PRESETS


class SettingsTab(ttk.Frame):
    """Settings tab for configuring application-wide preferences.

    Parameters
    ----------
    parent : tk.Widget
        Parent frame (notebook tab container).
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    # Labels for scroll config fields (key -> (label, unit, is_float))
    _SCROLL_FIELDS = [
        ("scroll_small_min", "Scroll pequeno min", "px", False),
        ("scroll_small_max", "Scroll pequeno max", "px", False),
        ("scroll_medium_min", "Scroll medio min", "px", False),
        ("scroll_medium_max", "Scroll medio max", "px", False),
        ("scroll_large_min", "Scroll grande min", "px", False),
        ("scroll_large_max", "Scroll grande max", "px", False),
        ("weight_scroll_small", "Peso scroll pequeno", "%", False),
        ("weight_scroll_medium", "Peso scroll medio", "%", False),
        ("weight_scroll_large", "Peso scroll grande", "%", False),
        ("weight_pause_read", "Peso pausa leitura", "%", False),
        ("weight_distracted_pause", "Peso pausa distraida", "%", False),
        ("pause_after_small_min", "Pausa apos scroll pequeno min", "s", True),
        ("pause_after_small_max", "Pausa apos scroll pequeno max", "s", True),
        ("pause_after_medium_min", "Pausa apos scroll medio min", "s", True),
        ("pause_after_medium_max", "Pausa apos scroll medio max", "s", True),
        ("pause_after_large_min", "Pausa apos scroll grande min", "s", True),
        ("pause_after_large_max", "Pausa apos scroll grande max", "s", True),
        ("distracted_pause_min", "Pausa distraida min", "s", True),
        ("distracted_pause_max", "Pausa distraida max", "s", True),
        ("post_read_time_min", "Tempo leitura post min", "s", True),
        ("post_read_time_max", "Tempo leitura post max", "s", True),
        ("comment_read_time_min", "Tempo leitura comentario min", "s", True),
        ("comment_read_time_max", "Tempo leitura comentario max", "s", True),
        ("hover_chance", "Chance de hover", "0-1", True),
    ]

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, style="Tab.TFrame", **kwargs)
        self.app = app
        self._scroll_vars: dict[str, tk.StringVar] = {}
        self._scroll_widgets: list[tk.Widget] = []
        self._build_ui()
        self._load_settings()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # Scrollable canvas for all content
        canvas = tk.Canvas(self, bg="#0a1628", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self._inner = ttk.Frame(canvas, style="Dark.TFrame")

        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling only when mouse is over this tab
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(_event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # Header
        header = ttk.Frame(self._inner, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        ttk.Label(header, text="Configuracoes", style="Heading.TLabel").pack(side=tk.LEFT)

        # Settings form
        form = ttk.LabelFrame(self._inner, text="Geral", style="Dark.TLabelframe")
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

        # ==============================================================
        # Advanced scroll configuration
        # ==============================================================
        scroll_frame = ttk.LabelFrame(
            self._inner, text="Rolagem Avancada", style="Dark.TLabelframe"
        )
        scroll_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        # Preset selector
        preset_row = ttk.Frame(scroll_frame, style="Dark.TFrame")
        preset_row.pack(fill=tk.X, **pad)
        ttk.Label(preset_row, text="Perfil de rolagem:", style="Dark.TLabel").pack(side=tk.LEFT)

        preset_names = list(SCROLL_PRESETS.keys()) + ["Personalizado"]
        self._combo_preset = ttk.Combobox(
            preset_row,
            values=preset_names,
            state="readonly",
            style="Dark.TCombobox",
            width=16,
        )
        self._combo_preset.set("Normal")
        self._combo_preset.pack(side=tk.RIGHT)
        self._combo_preset.bind("<<ComboboxSelected>>", self._on_preset_changed)

        # Scroll config fields (two columns)
        fields_frame = ttk.Frame(scroll_frame, style="Dark.TFrame")
        fields_frame.pack(fill=tk.X, padx=12, pady=6)

        # Create a grid of fields
        half = len(self._SCROLL_FIELDS) // 2 + len(self._SCROLL_FIELDS) % 2
        left_col = ttk.Frame(fields_frame, style="Dark.TFrame")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right_col = ttk.Frame(fields_frame, style="Dark.TFrame")
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        for idx, (key, label, unit, is_float) in enumerate(self._SCROLL_FIELDS):
            parent_col = left_col if idx < half else right_col
            row = ttk.Frame(parent_col, style="Dark.TFrame")
            row.pack(fill=tk.X, pady=2)

            var = tk.StringVar(value=str(DEFAULT_SCROLL_CONFIG[key]))
            self._scroll_vars[key] = var

            ttk.Label(row, text=f"{label} ({unit}):", style="Dark.TLabel").pack(side=tk.LEFT)
            spin = ttk.Spinbox(
                row,
                from_=0,
                to=9999 if not is_float else 999.0,
                width=6,
                textvariable=var,
                style="Dark.TSpinbox",
                increment=0.1 if is_float else 1,
            )
            spin.pack(side=tk.RIGHT)
            self._scroll_widgets.append(spin)

        # Restore defaults button
        btn_row = ttk.Frame(scroll_frame, style="Dark.TFrame")
        btn_row.pack(fill=tk.X, **pad)
        ttk.Button(
            btn_row, text="Restaurar Padrao", style="Accent.TButton",
            command=self._restore_scroll_defaults,
        ).pack(side=tk.LEFT)

        # Save button
        btn_frame = ttk.Frame(self._inner, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(btn_frame, text="Salvar Configuracoes", style="Accent.TButton", command=self._save_settings).pack(side=tk.LEFT)

    # ==================================================================
    # Scroll preset handling
    # ==================================================================

    def _on_preset_changed(self, _event=None) -> None:
        preset_name = self._combo_preset.get()
        if preset_name == "Personalizado":
            return  # Keep current values, let user edit freely

        preset_data = SCROLL_PRESETS.get(preset_name)
        config = preset_data if preset_data else DEFAULT_SCROLL_CONFIG
        for key, var in self._scroll_vars.items():
            var.set(str(config[key]))

    def _restore_scroll_defaults(self) -> None:
        self._combo_preset.set("Normal")
        for key, var in self._scroll_vars.items():
            var.set(str(DEFAULT_SCROLL_CONFIG[key]))

    def _get_scroll_config(self) -> dict:
        """Read current scroll config from the form."""
        config = {}
        for key, label, unit, is_float in self._SCROLL_FIELDS:
            try:
                val = self._scroll_vars[key].get()
                config[key] = float(val) if is_float else int(float(val))
            except (ValueError, KeyError):
                config[key] = DEFAULT_SCROLL_CONFIG[key]
        return config

    def _set_scroll_config(self, config: dict) -> None:
        """Populate scroll form fields from a config dict."""
        for key, var in self._scroll_vars.items():
            if key in config:
                var.set(str(config[key]))

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

        # Load scroll config
        scroll_json = self._get_setting("scroll_config", "")
        if scroll_json:
            try:
                saved = json.loads(scroll_json)
                self._set_scroll_config(saved)
                # Determine if it matches a preset
                preset_match = "Personalizado"
                for name, preset_data in SCROLL_PRESETS.items():
                    ref = preset_data if preset_data else DEFAULT_SCROLL_CONFIG
                    if all(str(saved.get(k)) == str(ref.get(k)) for k in DEFAULT_SCROLL_CONFIG):
                        preset_match = name
                        break
                self._combo_preset.set(preset_match)
            except (json.JSONDecodeError, TypeError):
                pass

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

        # Save scroll config
        scroll_config = self._get_scroll_config()
        self._set_setting("scroll_config", json.dumps(scroll_config))

        # Apply max_workers to engine immediately
        self.app.engine.max_concurrent = workers

        self.app.set_status("Configuracoes salvas com sucesso")
        messagebox.showinfo("Sucesso", "Configuracoes salvas com sucesso.", parent=self)
