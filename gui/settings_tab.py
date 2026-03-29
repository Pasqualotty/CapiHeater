"""
SettingsTab - Application settings with persistence.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.base import BaseTab
from utils.config import DEFAULT_SCROLL_CONFIG, SCROLL_PRESETS


class SettingsTab(BaseTab):
    """Settings tab for configuring application-wide preferences.

    Parameters
    ----------
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

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._scroll_spins: dict[str, QDoubleSpinBox | QSpinBox] = {}
        self._build_ui()
        self._load_settings()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll_area)

        container = QWidget()
        scroll_area.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header
        header_lbl = QLabel("Configuracoes")
        header_lbl.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(header_lbl)

        # ---- General settings group ----
        general_group = QGroupBox("Geral")
        general_form = QFormLayout(general_group)
        general_form.setContentsMargins(12, 16, 12, 12)
        general_form.setSpacing(8)

        # Max concurrent workers
        self._spin_workers = QSpinBox()
        self._spin_workers.setRange(1, 10)
        self._spin_workers.setValue(3)
        general_form.addRow("Workers simultaneos (max):", self._spin_workers)

        # Headless mode
        self._headless_cb = QCheckBox("Modo headless (navegador invisivel)")
        general_form.addRow(self._headless_cb)

        # Default proxy
        self._ent_proxy = QLineEdit()
        self._ent_proxy.setPlaceholderText("socks5://ip:porta ou http://ip:porta")
        general_form.addRow("Proxy padrao:", self._ent_proxy)

        # Log level
        self._combo_log = QComboBox()
        self._combo_log.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._combo_log.setCurrentText("INFO")
        general_form.addRow("Nivel de log:", self._combo_log)

        layout.addWidget(general_group)

        # ---- Advanced scroll configuration ----
        scroll_group = QGroupBox("Rolagem Avancada")
        scroll_layout = QVBoxLayout(scroll_group)
        scroll_layout.setContentsMargins(12, 16, 12, 12)
        scroll_layout.setSpacing(8)

        # Preset selector
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Perfil de rolagem:"))
        preset_names = list(SCROLL_PRESETS.keys()) + ["Personalizado"]
        self._combo_preset = QComboBox()
        self._combo_preset.addItems(preset_names)
        self._combo_preset.setCurrentText("Normal")
        self._combo_preset.currentTextChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self._combo_preset)
        preset_row.addStretch()
        scroll_layout.addLayout(preset_row)

        # Scroll config fields — two-column grid
        fields_layout = QHBoxLayout()
        half = len(self._SCROLL_FIELDS) // 2 + len(self._SCROLL_FIELDS) % 2

        left_form = QFormLayout()
        left_form.setSpacing(4)
        right_form = QFormLayout()
        right_form.setSpacing(4)

        for idx, (key, label, unit, is_float) in enumerate(self._SCROLL_FIELDS):
            form = left_form if idx < half else right_form

            if is_float:
                spin = QDoubleSpinBox()
                spin.setRange(0.0, 999.0)
                spin.setDecimals(1)
                spin.setSingleStep(0.1)
                spin.setValue(float(DEFAULT_SCROLL_CONFIG[key]))
            else:
                spin = QSpinBox()
                spin.setRange(0, 9999)
                spin.setValue(int(DEFAULT_SCROLL_CONFIG[key]))

            spin.setMinimumWidth(70)
            self._scroll_spins[key] = spin
            form.addRow(f"{label} ({unit}):", spin)

        left_widget = QWidget()
        left_widget.setLayout(left_form)
        right_widget = QWidget()
        right_widget.setLayout(right_form)

        fields_layout.addWidget(left_widget)
        fields_layout.addWidget(right_widget)
        scroll_layout.addLayout(fields_layout)

        # Restore defaults button
        btn_restore = QPushButton("Restaurar Padrao")
        btn_restore.setObjectName("accent")
        btn_restore.clicked.connect(self._restore_scroll_defaults)
        scroll_layout.addWidget(btn_restore, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(scroll_group)

        # ---- Save button ----
        btn_save = QPushButton("Salvar Configuracoes")
        btn_save.setObjectName("accent")
        btn_save.clicked.connect(self._save_settings)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

    # ==================================================================
    # Scroll preset handling
    # ==================================================================

    def _on_preset_changed(self, preset_name: str) -> None:
        if preset_name == "Personalizado":
            return
        preset_data = SCROLL_PRESETS.get(preset_name)
        config = preset_data if preset_data else DEFAULT_SCROLL_CONFIG
        self._set_scroll_config(config)

    def _restore_scroll_defaults(self) -> None:
        self._combo_preset.setCurrentText("Normal")
        self._set_scroll_config(DEFAULT_SCROLL_CONFIG)

    def _get_scroll_config(self) -> dict:
        """Read current scroll config from the form."""
        config = {}
        for key, label, unit, is_float in self._SCROLL_FIELDS:
            spin = self._scroll_spins.get(key)
            if spin is None:
                config[key] = DEFAULT_SCROLL_CONFIG[key]
                continue
            config[key] = spin.value()
        return config

    def _set_scroll_config(self, config: dict) -> None:
        """Populate scroll form fields from a config dict."""
        for key, spin in self._scroll_spins.items():
            if key in config:
                spin.setValue(float(config[key]) if isinstance(spin, QDoubleSpinBox) else int(config[key]))

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
        try:
            self._spin_workers.setValue(int(workers))
        except ValueError:
            self._spin_workers.setValue(3)

        headless = self._get_setting("headless", "0")
        self._headless_cb.setChecked(headless == "1")

        proxy = self._get_setting("default_proxy", "")
        self._ent_proxy.setText(proxy)

        log_level = self._get_setting("log_level", "INFO")
        self._combo_log.setCurrentText(log_level)

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
                self._combo_preset.setCurrentText(preset_match)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_settings(self) -> None:
        """Persist current form values to the settings table."""
        workers = self._spin_workers.value()

        self._set_setting("max_workers", str(workers))
        self._set_setting("headless", "1" if self._headless_cb.isChecked() else "0")
        self._set_setting("default_proxy", self._ent_proxy.text().strip())
        self._set_setting("log_level", self._combo_log.currentText())

        # Save scroll config
        scroll_config = self._get_scroll_config()
        self._set_setting("scroll_config", json.dumps(scroll_config))

        # Apply max_workers to engine immediately
        self.app.engine.max_concurrent = workers

        self.app.set_status("Configuracoes salvas com sucesso")
        QMessageBox.information(self, "Sucesso", "Configuracoes salvas com sucesso.")
