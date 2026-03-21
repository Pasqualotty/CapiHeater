"""
CapiHeater - Twitter/X Account Warming Tool
Entry point for the application.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

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
from utils.config import APP_NAME
from utils.logger import get_logger


def _launch_app(auth_session: dict | None = None):
    """Launch the main CapiHeater GUI.

    Parameters
    ----------
    auth_session : dict | None
        ``{"role": "user|moderator|admin", ...}`` when Supabase is configured.
        ``None`` in dev-mode (no auth).
    """
    from gui.app import CapiHeaterApp

    app = CapiHeaterApp(auth_session=auth_session)
    app.run()


def main():
    logger = get_logger(__name__)
    logger.info(f"Starting {APP_NAME} v{__version__}")

    # Check if Supabase is configured
    from auth.supabase_client import SupabaseAuth

    if not SupabaseAuth.is_configured():
        # Dev mode: Supabase placeholders still in place
        logger.warning("Supabase not configured - running in dev mode.")

        _root = tk.Tk()
        _root.withdraw()
        messagebox.showwarning(
            "Modo Desenvolvimento",
            "As credenciais do Supabase nao estao configuradas.\n"
            "O aplicativo sera iniciado sem autenticacao (modo dev).\n\n"
            "Para ativar a autenticacao, edite auth/supabase_client.py "
            "com as credenciais do seu projeto Supabase.",
        )
        _root.destroy()

        _launch_app()
        return

    # --- Normal auth flow -------------------------------------------------
    from gui.login_window import LoginWindow

    login = LoginWindow()
    login.mainloop()

    if not login.authenticated:
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

    _launch_app(auth_session=auth_session)


if __name__ == "__main__":
    main()
