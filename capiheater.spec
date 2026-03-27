# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CapiHeater (onedir mode).

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
        "tkinter", "tkinter.ttk", "tkinter.messagebox",
        "tkinter.filedialog", "tkinter.simpledialog",
        "gui", "gui.app", "gui.dashboard_tab", "gui.accounts_tab",
        "gui.targets_tab", "gui.schedule_tab", "gui.logs_tab",
        "gui.settings_tab", "gui.login_window", "gui.admin_tab",
        "gui.widgets", "gui.widgets.account_card", "gui.widgets.status_indicator",
        "core", "core.engine", "core.scheduler",
        "core.account_manager", "core.target_manager",
        "workers", "workers.base_worker", "workers.twitter_worker",
        "workers.actions", "workers.actions.selectors",
        "workers.actions.like", "workers.actions.follow",
        "workers.actions.unfollow", "workers.actions.retweet",
        "browser", "browser.driver_factory",
        "browser.cookie_manager", "browser.proxy_config",
        "database", "database.db", "database.models",
        "auth", "auth.supabase_client", "auth.license_guard",
        "utils", "utils.config", "utils.logger", "utils.humanizer",
        "undetected_chromedriver", "selenium", "selenium.webdriver",
        "selenium.webdriver.common.by", "selenium.webdriver.common.keys",
        "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions",
        "supabase", "cryptography", "cryptography.fernet",
        "mmh3", "pyiceberg", "pyparsing", "storage3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL", "pytest"],
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
