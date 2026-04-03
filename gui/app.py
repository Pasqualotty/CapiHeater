"""
CapiHeaterApp - Main application window (PySide6).
"""

import os
import threading
from queue import Queue

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from version import __version__
from database.db import Database
from core.engine import Engine
from core.account_manager import AccountManager
from core.target_manager import TargetManager
from core.category_manager import CategoryManager
from core.sfs_manager import SfsManager
from utils.config import DB_PATH, APP_NAME, get_user_db_path
from utils.logger import get_logger

logger = get_logger(__name__)

POLL_INTERVAL_MS = 100


class CapiHeaterApp(QMainWindow):
    """Main application window with tabbed interface.

    Parameters
    ----------
    auth_session : dict | None
        Optional authentication session payload (e.g. from a login screen).
        Expected keys: ``user``, ``role``, ``token``.
    """

    # Thread-safe signals for update checker
    _sig_prompt_update = Signal(dict)
    _sig_update_progress = Signal(int)
    _sig_update_error = Signal(str)
    _sig_update_done = Signal()

    def __init__(self, auth_session: dict | None = None, parent=None):
        super().__init__(parent)
        self.auth_session = auth_session

        # ---- Window setup ----
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(900, 550)
        self._center_window(1100, 700)

        # ---- Window icon ----
        from gui.theme import ICON_PATH
        import os
        if os.path.isfile(ICON_PATH):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(ICON_PATH))

        # ---- Backend services ----
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
        self.sfs_manager = SfsManager(self.db)
        self.engine = Engine(
            db=self.db,
            message_queue=self.message_queue,
        )

        # ---- Central widget with tabs ----
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 0)
        main_layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        main_layout.addWidget(self._tab_widget)

        self._tabs: dict[str, QWidget] = {}
        self._tab_names: list[str] = []
        self._build_tabs()

        # Tab change handler
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        # ---- Status bar ----
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._status_label = QLabel("Pronto")
        status_bar.addWidget(self._status_label, 1)

        logout_btn = QPushButton("Sair da Conta")
        logout_btn.setStyleSheet(
            "font-size: 8pt; padding: 2px 8px;"
        )
        logout_btn.clicked.connect(self._on_logout)
        status_bar.addPermanentWidget(logout_btn)

        # ---- Admin tab (conditional) ----
        if auth_session:
            role = auth_session.get("role", "")
            if role in ("admin", "moderator"):
                self.add_admin_tab()

        # ---- Connect signals ----
        self._sig_prompt_update.connect(self._prompt_update)
        self._sig_update_error.connect(self._on_update_error)

        # ---- Start queue polling ----
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_queue)
        self._poll_timer.start(POLL_INTERVAL_MS)

        # ---- Auto-update check (after 3 s) ----
        QTimer.singleShot(3000, self._check_update)

    # ==================================================================
    # Tab construction
    # ==================================================================

    def _build_tabs(self) -> None:
        from gui.dashboard_tab import DashboardTab
        from gui.accounts_tab import AccountsTab
        from gui.targets_tab import TargetsTab
        from gui.sfs_tab import SfsTab
        from gui.schedule_tab import ScheduleTab
        from gui.logs_tab import LogsTab
        from gui.settings_tab import SettingsTab
        from gui.docs_tab import DocsTab

        tabs = [
            ("Dashboard", DashboardTab),
            ("Contas", AccountsTab),
            ("Alvos", TargetsTab),
            ("SFS", SfsTab),
            ("Cronogramas", ScheduleTab),
            ("Logs", LogsTab),
            ("Configurações", SettingsTab),
            ("Documentação", DocsTab),
        ]

        for label, TabClass in tabs:
            tab_instance = TabClass(app=self)
            self._tab_widget.addTab(tab_instance, f"  {label}  ")
            self._tabs[label] = tab_instance
            self._tab_names.append(label)

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

            admin = AdminTab(auth=auth, session=session)
            self._tab_widget.addTab(admin, "  Admin  ")
            self._tabs["Admin"] = admin
            self._tab_names.append("Admin")
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

    def _handle_message(self, msg: dict) -> None:
        """Process a single message from the engine/workers."""
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

        elif event == "warning":
            warning_msg = msg.get("message", "")
            username = msg.get("username", "")
            if warning_msg:
                self.set_status(f"Aviso ({username}): {warning_msg}")
                QMessageBox.warning(
                    self,
                    "Aviso - CapiHeater",
                    f"Conta @{username}:\n\n{warning_msg}",
                )

        elif event == "sfs_error":
            username = msg.get("username", "")
            session_id = msg.get("session_id", "")
            error_detail = msg.get("error", "Erro desconhecido")
            self.set_status(f"SFS @{username}: erro — {error_detail}")
            QMessageBox.critical(
                self,
                "Erro na Sessao SFS",
                f"Falha ao executar sessao SFS da conta @{username}.\n\n"
                f"{error_detail}\n\n"
                "Verifique os cookies, o proxy e se o Chrome esta instalado corretamente.",
            )
            # Refresh SFS tab so status column mostra 'error'
            sfs_tab = self._tabs.get("SFS")
            if sfs_tab and hasattr(sfs_tab, "refresh"):
                sfs_tab.refresh()

        elif event == "sfs_started":
            username = msg.get("username", "")
            self.set_status(f"SFS @{username}: iniciado")

        elif event == "sfs_completed":
            username = msg.get("username", "")
            total = msg.get("total", 0)
            self.set_status(f"SFS @{username}: concluido ({total} alvo(s))")
            sfs_tab = self._tabs.get("SFS")
            if sfs_tab and hasattr(sfs_tab, "refresh"):
                sfs_tab.refresh()

        # Refresh dashboard on any message
        dashboard = self._tabs.get("Dashboard")
        if dashboard and hasattr(dashboard, "refresh"):
            dashboard.refresh()

    # ==================================================================
    # Tab change handler
    # ==================================================================

    def _on_tab_changed(self, index: int) -> None:
        """Refresh the active tab when the user switches to it."""
        if 0 <= index < len(self._tab_names):
            tab_name = self._tab_names[index]
            tab = self._tabs.get(tab_name)
            if tab and hasattr(tab, "refresh"):
                tab.refresh()

    # ==================================================================
    # Logout
    # ==================================================================

    def _on_logout(self) -> None:
        """Log out: clear saved credentials, stop workers, and close."""
        reply = QMessageBox.question(
            self,
            "Sair",
            "Deseja sair da conta atual?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Stop all workers
        try:
            self.engine.stop_all()
        except Exception:
            pass

        # Clear saved credentials (remember-me)
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

        QMessageBox.information(
            self,
            "Logout",
            "Voce foi desconectado.\nAbra o app novamente para fazer login.",
        )
        self.close()

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
            self._sig_prompt_update.emit(info)

    def _prompt_update(self, info: dict) -> None:
        version = info["version"]
        notes = info.get("notes", "")
        msg = f"Nova versao {version} disponivel!"
        if notes:
            msg += f"\n\n{notes}"
        msg += "\n\nDeseja atualizar agora?"

        reply = QMessageBox.question(
            self,
            "Atualização",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._start_update_download(info["download_url"], info.get("size", 0))

    def _start_update_download(self, download_url: str, expected_size: int = 0) -> None:
        # Build a progress dialog
        self._update_dlg = QDialog(self)
        self._update_dlg.setWindowTitle("Atualizando...")
        self._update_dlg.setFixedSize(400, 120)
        self._update_dlg.setModal(True)

        dlg_layout = QVBoxLayout(self._update_dlg)
        dlg_layout.setContentsMargins(16, 16, 16, 16)

        dlg_layout.addWidget(QLabel("Baixando atualização..."))

        self._update_bar = QProgressBar()
        self._update_bar.setRange(0, 100)
        self._update_bar.setValue(0)
        dlg_layout.addWidget(self._update_bar)

        self._update_dlg.show()

        # Connect progress signal
        self._sig_update_progress.connect(self._update_bar.setValue)
        self._sig_update_done.connect(self._update_dlg.accept)

        def on_progress(downloaded: int, total: int) -> None:
            if total > 0:
                pct = downloaded / total * 100
                self._sig_update_progress.emit(int(pct))

        def worker() -> None:
            from utils.updater import AutoUpdater

            updater = AutoUpdater()
            try:
                updater.download_and_apply(
                    download_url,
                    on_progress=on_progress,
                    expected_size=expected_size,
                )
                self._sig_update_done.emit()
            except Exception as exc:
                self._sig_update_error.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_error(self, error_msg: str) -> None:
        if hasattr(self, "_update_dlg"):
            self._update_dlg.close()
        QMessageBox.critical(
            self,
            "Erro",
            f"Falha ao baixar atualização:\n{error_msg}",
        )

    # ==================================================================
    # Public helpers
    # ==================================================================

    def set_status(self, text: str) -> None:
        """Update the status bar text."""
        self._status_label.setText(text)

    # ==================================================================
    # Window helpers
    # ==================================================================

    def _center_window(self, width: int, height: int) -> None:
        screen = self.screen().geometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
