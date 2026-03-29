"""
CapiHeater - Twitter/X Account Warming Tool
Entry point for the application.
"""

import sys
import os

# Ensure project root is on the path — works both from source and from
# a PyInstaller --onefile bundle (where _MEIPASS is the temp directory).
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE_DIR)

# Override APP_DIR so config.py paths resolve correctly in frozen builds
os.environ["CAPIHEATER_BASE_DIR"] = _BASE_DIR

from version import __version__
from utils.config import APP_NAME, DATA_DIR
from utils.logger import get_logger


def _cleanup_update_leftovers():
    """Delete temp files left behind by the auto-updater."""
    import shutil

    # Remove _update_new directory (onedir update temp)
    update_dir = os.path.join(_BASE_DIR, "_update_new")
    if os.path.isdir(update_dir):
        shutil.rmtree(update_dir, ignore_errors=True)

    # Remove old onefile leftovers
    import glob as _glob
    current_exe = (
        os.path.normcase(os.path.abspath(sys.executable))
        if getattr(sys, "frozen", False)
        else None
    )
    for pattern in (
        os.path.join(_BASE_DIR, "*.download"),
        os.path.join(_BASE_DIR, "tmp*.exe"),
        os.path.join(_BASE_DIR, "tmp*.zip"),
        os.path.join(_BASE_DIR, "CapiHeater.exe.old"),
    ):
        for path in _glob.glob(pattern):
            if current_exe and os.path.normcase(os.path.abspath(path)) == current_exe:
                continue
            try:
                os.remove(path)
            except OSError:
                pass


def _migrate_old_data():
    """Move database files from old location (next to .exe) to AppData."""
    import shutil
    old_data_dir = os.path.join(_BASE_DIR, "data")
    if not os.path.isdir(old_data_dir):
        return
    for fname in os.listdir(old_data_dir):
        if fname.endswith(".db"):
            old_path = os.path.join(old_data_dir, fname)
            new_path = os.path.join(DATA_DIR, fname)
            if not os.path.exists(new_path):
                try:
                    shutil.copy2(old_path, new_path)
                except Exception:
                    pass


def main():
    from PySide6.QtWidgets import QApplication, QMessageBox

    _cleanup_update_leftovers()
    _migrate_old_data()

    logger = get_logger(__name__)
    logger.info(f"Starting {APP_NAME} v{__version__}")

    app = QApplication(sys.argv)

    # Set application icon (taskbar + window)
    from gui.theme import ICON_PATH
    if os.path.isfile(ICON_PATH):
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(ICON_PATH))

    # Apply global dark theme
    from gui.theme import QSS
    app.setStyleSheet(QSS)

    # Check if Supabase is configured
    try:
        from auth.supabase_client import SupabaseAuth
    except ImportError:
        logger.warning("supabase package not installed - running in dev mode.")
        QMessageBox.warning(
            None,
            "Modo Desenvolvimento",
            "O pacote 'supabase' nao esta instalado.\n"
            "O aplicativo sera iniciado sem autenticacao (modo dev).",
        )
        _launch_app(app, auth_session=None)
        return

    if not SupabaseAuth.is_configured():
        logger.warning("Supabase not configured - running in dev mode.")
        QMessageBox.warning(
            None,
            "Modo Desenvolvimento",
            "As credenciais do Supabase nao estao configuradas.\n"
            "O aplicativo sera iniciado sem autenticacao (modo dev).\n\n"
            "Para ativar a autenticacao, edite auth/supabase_client.py "
            "com as credenciais do seu projeto Supabase.",
        )
        _launch_app(app, auth_session=None)
        return

    # --- Normal auth flow -------------------------------------------------
    from gui.login_window import LoginWindow
    from PySide6.QtWidgets import QDialog

    login = LoginWindow()
    if login.exec() != QDialog.DialogCode.Accepted:
        logger.info("Login cancelled or failed. Exiting.")
        return

    # Build a session dict the app understands
    role = "user"
    if login.license_info:
        role = login.license_info.get("role", "user")

    auth_session = {
        "role": role,
        "session": login.session,
        "auth": login.auth,
        "license_info": login.license_info,
    }

    _launch_app(app, auth_session=auth_session)


def _launch_app(app: "QApplication", auth_session: dict | None = None):
    """Launch the main CapiHeater GUI."""
    from gui.app import CapiHeaterApp

    window = CapiHeaterApp(auth_session=auth_session)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
