# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CapiHeater.

Build command:
    pyinstaller capiheater.spec

This produces a single .exe with:
- Tkinter GUI (windowed, no console)
- Bundled default schedule JSON
- Application icon
"""

import os
import sys

block_cipher = None

# Locate python311.dll explicitly (GitHub Actions runners may install
# Python in non-standard paths that PyInstaller doesn't search)
_PYTHON_DLL_CANDIDATES = [
    os.path.join(os.path.dirname(sys.executable), "python311.dll"),
    os.path.join(sys.exec_prefix, "python311.dll"),
    os.path.join(sys.base_prefix, "python311.dll"),
]
_EXTRA_BINARIES = []
for _p in _PYTHON_DLL_CANDIDATES:
    if os.path.isfile(_p):
        _EXTRA_BINARIES.append((_p, "."))
        break

# Resolve paths relative to this spec file
# SPECPATH is the full path to THIS .spec file
_SPEC_DIR = os.path.dirname(SPECPATH) if os.path.isfile(SPECPATH) else SPECPATH

# Icon path (use None if icon doesn't exist yet)
_ICON = os.path.join(_SPEC_DIR, "assets", "icon.ico")
if not os.path.isfile(_ICON):
    _ICON = None

a = Analysis(
    [os.path.join(_SPEC_DIR, "main.py")],
    pathex=[_SPEC_DIR],
    binaries=_EXTRA_BINARIES,
    datas=[
        # Bundle the default schedule JSON so db.py can find it
        (os.path.join(_SPEC_DIR, "schedules", "default_schedule.json"), "schedules"),
    ],
    hiddenimports=[
        # Tkinter (sometimes missed on some Python builds)
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.simpledialog",
        # Our own packages — ensure PyInstaller picks them up
        "gui",
        "gui.app",
        "gui.dashboard_tab",
        "gui.accounts_tab",
        "gui.targets_tab",
        "gui.schedule_tab",
        "gui.logs_tab",
        "gui.settings_tab",
        "gui.login_window",
        "gui.admin_tab",
        "gui.widgets",
        "gui.widgets.account_card",
        "gui.widgets.status_indicator",
        "core",
        "core.engine",
        "core.scheduler",
        "core.account_manager",
        "core.target_manager",
        "workers",
        "workers.base_worker",
        "workers.twitter_worker",
        "workers.actions",
        "workers.actions.selectors",
        "workers.actions.like",
        "workers.actions.follow",
        "workers.actions.unfollow",
        "workers.actions.retweet",
        "browser",
        "browser.driver_factory",
        "browser.cookie_manager",
        "browser.proxy_config",
        "database",
        "database.db",
        "database.models",
        "auth",
        "auth.supabase_client",
        "auth.license_guard",
        "utils",
        "utils.config",
        "utils.logger",
        "utils.humanizer",
        # Third-party that PyInstaller may miss
        "undetected_chromedriver",
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.common.by",
        "selenium.webdriver.common.keys",
        "selenium.webdriver.support.ui",
        "selenium.webdriver.support.expected_conditions",
        "supabase",
        "cryptography",
        "cryptography.fernet",
        "mmh3",
        "pyiceberg",
        "pyparsing",
        "storage3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unnecessary modules to reduce .exe size
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "pytest",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CapiHeater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # --windowed: no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON,
)
