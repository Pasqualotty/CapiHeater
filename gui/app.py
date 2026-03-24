"""
CapiHeaterApp - Main application window.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from queue import Queue
import threading

from version import __version__
from database.db import Database
from core.engine import Engine
from core.account_manager import AccountManager
from core.target_manager import TargetManager
from core.category_manager import CategoryManager
from utils.config import DB_PATH, APP_NAME, get_user_db_path
from utils.logger import get_logger

logger = get_logger(__name__)

# ======================================================================
# Theme constants
# ======================================================================
BG_DARK = "#1a1a2e"
BG_SECONDARY = "#16213e"
BG_ACCENT = "#0f3460"
BG_INPUT = "#0d1b2a"
FG_TEXT = "#e0e0e0"
FG_MUTED = "#9e9e9e"
FG_TITLE = "#ffffff"
ACCENT_BLUE = "#0f3460"
ACCENT_HIGHLIGHT = "#1a73e8"
COLOR_SUCCESS = "#00e676"
COLOR_WARNING = "#ffea00"
COLOR_ERROR = "#ff1744"

POLL_INTERVAL_MS = 100


class CapiHeaterApp:
    """Main Tkinter application window with tabbed interface.

    Parameters
    ----------
    auth_session : dict | None
        Optional authentication session payload (e.g. from a login screen).
        Expected keys: ``user``, ``role``, ``token``.
    """

    def __init__(self, auth_session: dict | None = None):
        self.auth_session = auth_session

        # ---- Tk root ----
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{__version__}")
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)
        self.root.configure(bg=BG_DARK)
        self._center_window(1100, 700)

        # ---- Backend services ----
        # Use per-user database if logged in, otherwise default
        db_path = DB_PATH
        if auth_session:
            session = auth_session.get("session")
            if session and hasattr(session, "user") and session.user:
                db_path = get_user_db_path(str(session.user.id))
                logger.info(f"Using per-user database: {db_path}")

        self.db = Database(db_path)
        self.db.init_db()

        self.message_queue: Queue = Queue()
        self.account_manager = AccountManager(self.db)
        self.target_manager = TargetManager(self.db)
        self.category_manager = CategoryManager(self.db)
        self.engine = Engine(
            db=self.db,
            message_queue=self.message_queue,
        )

        # ---- Styles ----
        self._configure_styles()

        # ---- Notebook (tabs) ----
        self.notebook = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        self._tabs: dict[str, ttk.Frame] = {}
        self._build_tabs()

        # ---- Status bar with logout button ----
        status_frame = ttk.Frame(self.root, style="Dark.TFrame")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=(0, 4))

        self._status_var = tk.StringVar(value="Pronto")
        self._status_bar = ttk.Label(
            status_frame,
            textvariable=self._status_var,
            style="StatusBar.TLabel",
            anchor=tk.W,
        )
        self._status_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)

        logout_btn = tk.Button(
            status_frame,
            text="Sair da Conta",
            font=("Segoe UI", 8),
            bg="#333355",
            fg="#e0e0e0",
            activebackground="#444466",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._on_logout,
        )
        logout_btn.pack(side=tk.RIGHT, padx=(6, 0))

        # ---- Admin tab (conditional) ----
        if auth_session:
            role = auth_session.get("role", "")
            if role in ("admin", "moderator"):
                self.add_admin_tab()

        # ---- Start polling ----
        self._poll_queue()

        # ---- Auto-update check (after 3 s) ----
        self.root.after(3000, self._check_update)

    # ==================================================================
    # Tab construction
    # ==================================================================

    def _build_tabs(self) -> None:
        from gui.dashboard_tab import DashboardTab
        from gui.accounts_tab import AccountsTab
        from gui.targets_tab import TargetsTab
        from gui.schedule_tab import ScheduleTab
        from gui.logs_tab import LogsTab
        from gui.settings_tab import SettingsTab

        tabs = [
            ("Dashboard", DashboardTab),
            ("Contas", AccountsTab),
            ("Alvos", TargetsTab),
            ("Cronogramas", ScheduleTab),
            ("Logs", LogsTab),
            ("Configurações", SettingsTab),
        ]

        for label, TabClass in tabs:
            frame = ttk.Frame(self.notebook, style="Tab.TFrame")
            tab_instance = TabClass(frame, self)
            tab_instance.pack(fill=tk.BOTH, expand=True)
            self.notebook.add(frame, text=f"  {label}  ")
            self._tabs[label] = tab_instance

        # Auto-refresh tabs when selected
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def add_admin_tab(self) -> None:
        """Dynamically add an Admin tab (for moderators/admins)."""
        if not self.auth_session:
            return

        try:
            from gui.admin_tab import AdminTab

            auth = self.auth_session.get("auth")
            session = self.auth_session.get("session")
            if not auth or not session:
                return

            frame = ttk.Frame(self.notebook, style="Tab.TFrame")
            admin = AdminTab(frame, auth=auth, session=session)
            admin.pack(fill=tk.BOTH, expand=True)
            self.notebook.add(frame, text="  Admin  ")
            self._tabs["Admin"] = admin
        except Exception as exc:
            logger.warning(f"Could not load admin tab: {exc}")

    # ==================================================================
    # Queue polling
    # ==================================================================

    def _poll_queue(self) -> None:
        """Drain the message queue and dispatch updates to the GUI."""
        while not self.message_queue.empty():
            try:
                msg = self.message_queue.get_nowait()
                self._handle_message(msg)
            except Exception:
                break

        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def _handle_message(self, msg: dict) -> None:
        """Process a single message from the engine/workers.

        Worker messages use the key ``event`` with values like
        ``status``, ``schedule``, ``action_complete``.
        """
        event = msg.get("event", "")

        if event == "status":
            dashboard = self._tabs.get("Dashboard")
            if dashboard and hasattr(dashboard, "on_status_update"):
                dashboard.on_status_update(msg)
            status = msg.get("status", "")
            if status == "error":
                self.set_status(f"Erro: {msg.get('error', 'desconhecido')}")

        elif event == "action_complete":
            logs_tab = self._tabs.get("Logs")
            if logs_tab and hasattr(logs_tab, "on_new_log"):
                logs_tab.on_new_log(msg)

        # Refresh dashboard on any message
        dashboard = self._tabs.get("Dashboard")
        if dashboard and hasattr(dashboard, "refresh"):
            dashboard.refresh()

    # ==================================================================
    # Tab change handler
    # ==================================================================

    def _on_tab_changed(self, _event=None) -> None:
        """Refresh the active tab when the user switches to it."""
        try:
            idx = self.notebook.index(self.notebook.select())
            tab_name = self.notebook.tab(idx, "text").strip()
            tab = self._tabs.get(tab_name)
            if tab and hasattr(tab, "refresh"):
                tab.refresh()
        except Exception:
            pass

    # ==================================================================
    # Logout
    # ==================================================================

    def _on_logout(self) -> None:
        """Log out: clear saved credentials, stop workers, and restart the app."""
        from tkinter import messagebox
        if not messagebox.askyesno("Sair", "Deseja sair da conta atual?"):
            return

        # Stop all workers
        try:
            self.engine.stop_all()
        except Exception:
            pass

        # Clear saved credentials (remember-me)
        import os
        app_data = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "CapiHeater"
        )
        for f in ("remember.dat", "rkey.dat"):
            path = os.path.join(app_data, f)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        # Close the app — next time it opens, login screen will appear
        from tkinter import messagebox as mb2
        mb2.showinfo("Logout", "Voce foi desconectado.\nAbra o app novamente para fazer login.")
        self.root.destroy()

    # ==================================================================
    # Auto-update
    # ==================================================================

    def _check_update(self) -> None:
        """Run the update check in a background thread."""
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        from utils.updater import AutoUpdater

        updater = AutoUpdater()
        try:
            info = updater.check_for_update()
        except Exception:
            return
        if info:
            self.root.after(0, lambda: self._prompt_update(info))

    def _prompt_update(self, info: dict) -> None:
        version = info["version"]
        notes = info.get("notes", "")
        msg = f"Nova versao {version} disponivel!"
        if notes:
            msg += f"\n\n{notes}"
        msg += "\n\nDeseja atualizar agora?"

        if not messagebox.askyesno("Atualização", msg):
            return

        self._start_update_download(info["download_url"])

    def _start_update_download(self, download_url: str) -> None:
        # Build a small progress window
        win = tk.Toplevel(self.root)
        win.title("Atualizando...")
        win.geometry("400x120")
        win.resizable(False, False)
        win.configure(bg=BG_DARK)
        win.transient(self.root)
        win.grab_set()

        ttk.Label(
            win, text="Baixando atualização...", style="Dark.TLabel",
        ).pack(pady=(16, 4))

        progress_var = tk.DoubleVar(value=0.0)
        bar = ttk.Progressbar(
            win,
            variable=progress_var,
            maximum=100,
            mode="determinate",
            style="Card.Horizontal.TProgressbar",
            length=350,
        )
        bar.pack(pady=8)

        def on_progress(downloaded: int, total: int) -> None:
            if total > 0:
                pct = downloaded / total * 100
                self.root.after(0, lambda p=pct: progress_var.set(p))

        def worker() -> None:
            from utils.updater import AutoUpdater

            updater = AutoUpdater()
            try:
                updater.download_and_apply(download_url, on_progress=on_progress)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: (
                        win.destroy(),
                        messagebox.showerror(
                            "Erro",
                            f"Falha ao baixar atualização:\n{exc}",
                        ),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    # ==================================================================
    # Public helpers
    # ==================================================================

    def set_status(self, text: str) -> None:
        """Update the status bar text."""
        self._status_var.set(text)

    def run(self) -> None:
        """Start the Tkinter main loop."""
        logger.info("GUI started")
        self.root.mainloop()

    # ==================================================================
    # Styling
    # ==================================================================

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # ----- General -----
        style.configure(".", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 10))

        # ----- TNotebook -----
        style.configure(
            "Dark.TNotebook",
            background=BG_DARK,
            borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background=BG_SECONDARY,
            foreground=FG_MUTED,
            padding=[14, 6],
            font=("Segoe UI", 10),
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", BG_ACCENT)],
            foreground=[("selected", FG_TITLE)],
        )

        # ----- TFrame -----
        style.configure("Tab.TFrame", background=BG_DARK)
        style.configure("Card.TFrame", background=BG_SECONDARY, relief="flat")
        style.configure("Dark.TFrame", background=BG_DARK)

        # ----- TLabel -----
        style.configure("Dark.TLabel", background=BG_DARK, foreground=FG_TEXT)
        style.configure("Heading.TLabel", background=BG_DARK, foreground=FG_TITLE, font=("Segoe UI", 14, "bold"))
        style.configure("CardTitle.TLabel", background=BG_SECONDARY, foreground=FG_TITLE, font=("Segoe UI", 10, "bold"))
        style.configure("CardStatus.TLabel", background=BG_SECONDARY, foreground=FG_MUTED, font=("Segoe UI", 9))
        style.configure("CardDetail.TLabel", background=BG_SECONDARY, foreground=FG_MUTED, font=("Segoe UI", 9))
        style.configure("StatusBar.TLabel", background=BG_SECONDARY, foreground=FG_MUTED, font=("Segoe UI", 9), padding=[8, 4])
        style.configure("OverviewValue.TLabel", background=BG_SECONDARY, foreground=FG_TITLE, font=("Segoe UI", 22, "bold"))
        style.configure("OverviewCaption.TLabel", background=BG_SECONDARY, foreground=FG_MUTED, font=("Segoe UI", 9))

        # ----- TButton -----
        style.configure(
            "Accent.TButton",
            background=ACCENT_HIGHLIGHT,
            foreground=FG_TITLE,
            font=("Segoe UI", 10),
            padding=[12, 6],
        )
        style.map(
            "Accent.TButton",
            background=[("active", BG_ACCENT)],
        )
        style.configure(
            "Danger.TButton",
            background=COLOR_ERROR,
            foreground=FG_TITLE,
            font=("Segoe UI", 10),
            padding=[12, 6],
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#d50000")],
        )

        # ----- Treeview -----
        style.configure(
            "Dark.Treeview",
            background=BG_SECONDARY,
            foreground=FG_TEXT,
            fieldbackground=BG_SECONDARY,
            borderwidth=0,
            font=("Segoe UI", 10),
            rowheight=28,
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=BG_ACCENT,
            foreground=FG_TITLE,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", ACCENT_HIGHLIGHT)],
            foreground=[("selected", FG_TITLE)],
        )

        # ----- TEntry / TSpinbox -----
        style.configure(
            "Dark.TEntry",
            fieldbackground=BG_INPUT,
            foreground=FG_TEXT,
            insertcolor=FG_TEXT,
        )
        style.configure(
            "Dark.TSpinbox",
            fieldbackground=BG_INPUT,
            foreground=FG_TEXT,
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground=BG_INPUT,
            foreground=FG_TEXT,
            selectbackground=ACCENT_HIGHLIGHT,
        )

        # ----- Progressbar -----
        style.configure(
            "Card.Horizontal.TProgressbar",
            troughcolor=BG_DARK,
            background=ACCENT_HIGHLIGHT,
            thickness=6,
        )

        # ----- TCheckbutton -----
        style.configure(
            "Dark.TCheckbutton",
            background=BG_DARK,
            foreground=FG_TEXT,
        )

        # ----- TLabelframe -----
        style.configure(
            "Dark.TLabelframe",
            background=BG_DARK,
            foreground=FG_TEXT,
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=BG_DARK,
            foreground=FG_TITLE,
            font=("Segoe UI", 10, "bold"),
        )

    # ==================================================================
    # Window helpers
    # ==================================================================

    def _center_window(self, width: int, height: int) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
