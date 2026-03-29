# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CapiHeater (onedir mode, PySide6).

Build command:
    pyinstaller capiheater.spec

Produces dist/CapiHeater/ directory with:
- CapiHeater.exe (windowed, no console)
- All DLLs and dependencies side-by-side (no temp extraction)
- Bundled default schedule JSON
- Application icon
"""

import os
import sys

block_cipher = None

_SPEC_DIR = os.path.dirname(SPECPATH) if os.path.isfile(SPECPATH) else SPECPATH

_ICON = os.path.join(_SPEC_DIR, "assets", "icon.ico")
if not os.path.isfile(_ICON):
    _ICON = None

a = Analysis(
    [os.path.join(_SPEC_DIR, "main.py")],
    pathex=[_SPEC_DIR],
    binaries=[],
    datas=[
        (os.path.join(_SPEC_DIR, "schedules", "default_schedule.json"), "schedules"),
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui",
        # GUI modules
        "gui", "gui.app", "gui.theme", "gui.base",
        "gui.dashboard_tab", "gui.accounts_tab",
        "gui.targets_tab", "gui.schedule_tab", "gui.logs_tab",
        "gui.settings_tab", "gui.login_window", "gui.admin_tab", "gui.docs_tab",
        "gui.widgets", "gui.widgets.account_card", "gui.widgets.status_indicator",
        # Core
        "core", "core.engine", "core.scheduler",
        "core.account_manager", "core.target_manager",
        # Workers
        "workers", "workers.base_worker", "workers.twitter_worker",
        "workers.actions", "workers.actions.selectors",
        "workers.actions.like", "workers.actions.follow",
        "workers.actions.unfollow", "workers.actions.retweet",
        # Browser
        "browser", "browser.driver_factory",
        "browser.cookie_manager", "browser.proxy_config",
        # Database
        "database", "database.db", "database.models",
        # Auth
        "auth", "auth.supabase_client", "auth.license_guard",
        # Utils
        "utils", "utils.config", "utils.logger", "utils.humanizer",
        # Third-party
        "undetected_chromedriver", "selenium", "selenium.webdriver",
        "selenium.webdriver.common.by", "selenium.webdriver.common.keys",
        "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions",
        "supabase", "cryptography", "cryptography.fernet",
        "mmh3", "pyiceberg", "pyparsing", "storage3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Removed tkinter (no longer used)
        "tkinter",
        # Unused heavy packages
        "matplotlib", "numpy", "pandas", "scipy", "PIL", "pytest",
        # Unused PySide6 modules (reduce size)
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
        "PySide6.QtBluetooth", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetwork", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects",
        "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSvg",
        "PySide6.QtTest", "PySide6.QtWebChannel", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtXml",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtSql", "PySide6.QtStateMachine", "PySide6.QtSvgWidgets",
        "PySide6.QtUiTools", "PySide6.QtConcurrent", "PySide6.QtDBus",
        "PySide6.QtDataVisualization", "PySide6.QtCharts", "PySide6.QtScxml",
        "PySide6.QtTextToSpeech",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CapiHeater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="CapiHeater",
)
