"""
LoginWindow - Tela de login do CapiHeater (dark themed, PT-BR).
"""

import json
import os
import threading

from PySide6.QtCore import QTimer, Qt, Signal, Slot
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from gui.theme import (
    ACCENT,
    ACCENT_HIGHLIGHT,
    BG_DARK,
    BG_SECONDARY,
    COLOR_ERROR,
    FG_MUTED,
    FG_TEXT,
    FG_TITLE,
)

# App-data directory for persisting last e-mail
_APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "CapiHeater"
)
_LAST_EMAIL_FILE = os.path.join(_APP_DATA_DIR, "last_email.json")
_REMEMBER_FILE = os.path.join(_APP_DATA_DIR, "remember.dat")
_REMEMBER_KEY_FILE = os.path.join(_APP_DATA_DIR, "rkey.dat")


class LoginWindow(QDialog):
    """Standalone login dialog. On success, stores ``session``, ``auth``,
    and ``license_info``, then accepts the dialog so the caller can proceed."""

    # Thread-safe signals for cross-thread UI updates
    _sig_login_success = Signal(object, object, object, str, bool)
    _sig_login_failed = Signal(str)
    _sig_register_done = Signal(str)
    _sig_register_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("CapiHeater - Login")
        self.setFixedSize(400, 480)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        # Centre on screen
        screen = self.screen().geometry()
        x = (screen.width() - 400) // 2
        y = (screen.height() - 480) // 2
        self.move(x, y)

        # Public attributes set after successful login
        self.session = None
        self.auth = None
        self.license_info: dict | None = None
        self._authenticated = False
        self._login_in_progress = False

        # Connect thread-safe signals
        self._sig_login_success.connect(self._login_success)
        self._sig_login_failed.connect(self._login_failed)
        self._sig_register_done.connect(self._register_done)
        self._sig_register_failed.connect(self._register_failed)

        self._build_ui()
        self._load_last_email()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 20)
        layout.setSpacing(0)

        # Title
        title_lbl = QLabel("CapiHeater")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {FG_TITLE}; font-size: 24pt; font-weight: bold;"
        )
        layout.addWidget(title_lbl)

        # Subtitle
        subtitle_lbl = QLabel("Aquecedor de Contas Twitter/X")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_lbl.setStyleSheet("color: #8888aa; font-size: 10pt;")
        layout.addWidget(subtitle_lbl)
        layout.addSpacing(30)

        # E-mail label
        email_lbl = QLabel("E-mail")
        email_lbl.setStyleSheet(f"color: {FG_TITLE}; font-size: 10pt;")
        layout.addWidget(email_lbl)
        layout.addSpacing(2)

        # E-mail input
        self._email_entry = QLineEdit()
        self._email_entry.setStyleSheet(self._entry_style())
        layout.addWidget(self._email_entry)
        layout.addSpacing(12)

        # Senha label
        pass_lbl = QLabel("Senha")
        pass_lbl.setStyleSheet(f"color: {FG_TITLE}; font-size: 10pt;")
        layout.addWidget(pass_lbl)
        layout.addSpacing(2)

        # Senha input
        self._pass_entry = QLineEdit()
        self._pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_entry.setStyleSheet(self._entry_style())
        layout.addWidget(self._pass_entry)
        layout.addSpacing(10)

        # Lembrar de mim
        self._remember_cb = QCheckBox("Lembrar de mim")
        self._remember_cb.setStyleSheet("color: #8888aa; font-size: 9pt;")
        self._remember_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._remember_cb)
        layout.addSpacing(8)

        # Error label
        self._error_lbl = QLabel("")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet(
            f"color: {COLOR_ERROR}; font-size: 9pt;"
        )
        layout.addWidget(self._error_lbl)
        layout.addSpacing(8)

        # Entrar button
        self._login_btn = QPushButton("Entrar")
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {FG_TITLE};
                font-size: 11pt;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HIGHLIGHT};
            }}
            QPushButton:disabled {{
                background-color: {BG_SECONDARY};
                color: {FG_MUTED};
            }}
        """)
        self._login_btn.clicked.connect(self._on_login)
        layout.addWidget(self._login_btn)
        layout.addSpacing(14)

        # Registrar link
        reg_lbl = QLabel("Ainda nao tem conta? Registrar")
        reg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reg_lbl.setStyleSheet(
            "color: #5588cc; font-size: 9pt; text-decoration: underline;"
        )
        reg_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        reg_lbl.mousePressEvent = lambda _e: self._on_register()
        layout.addWidget(reg_lbl)

        # Loading label
        self._loading_lbl = QLabel("")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_lbl.setStyleSheet("color: #aaaacc; font-size: 9pt;")
        layout.addWidget(self._loading_lbl)

        layout.addStretch()

        # Enter key shortcut (stored as attribute to prevent GC)
        self._shortcut_enter = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self._shortcut_enter.activated.connect(self._on_login)

    @staticmethod
    def _entry_style() -> str:
        return (
            f"background-color: {BG_SECONDARY}; color: {FG_TEXT};"
            f"font-size: 11pt; border: 1px solid {ACCENT};"
            "border-radius: 3px; padding: 6px;"
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _get_fernet(self):
        """Get or create a Fernet key for encrypting saved credentials."""
        from cryptography.fernet import Fernet
        os.makedirs(_APP_DATA_DIR, exist_ok=True)
        if os.path.exists(_REMEMBER_KEY_FILE):
            with open(_REMEMBER_KEY_FILE, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(_REMEMBER_KEY_FILE, "wb") as f:
                f.write(key)
        return Fernet(key)

    def _save_remember(self, email: str, password: str):
        """Encrypt and save credentials locally."""
        try:
            fernet = self._get_fernet()
            data = json.dumps({"email": email, "password": password}).encode()
            encrypted = fernet.encrypt(data)
            with open(_REMEMBER_FILE, "wb") as f:
                f.write(encrypted)
        except Exception:
            pass

    def _load_remember(self) -> tuple[str, str] | None:
        """Load saved credentials. Returns (email, password) or None."""
        try:
            if not os.path.exists(_REMEMBER_FILE):
                return None
            fernet = self._get_fernet()
            with open(_REMEMBER_FILE, "rb") as f:
                encrypted = f.read()
            data = json.loads(fernet.decrypt(encrypted).decode())
            return data.get("email", ""), data.get("password", "")
        except Exception:
            return None

    def _clear_remember(self):
        """Remove saved credentials."""
        for filepath in (_REMEMBER_FILE, _REMEMBER_KEY_FILE):
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

    def _load_last_email(self):
        # Try auto-login with saved credentials first
        try:
            saved = self._load_remember()
            if saved and saved[0] and saved[1]:
                self._email_entry.setText(saved[0])
                self._pass_entry.setText(saved[1])
                self._remember_cb.setChecked(True)
                QTimer.singleShot(500, self._auto_login)
                return
        except Exception:
            pass

        # Otherwise just load last email
        try:
            with open(_LAST_EMAIL_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                email = data.get("email", "")
                if email:
                    self._email_entry.setText(email)
                    self._pass_entry.setFocus()
                    return
        except Exception:
            pass
        self._email_entry.setFocus()

    def _auto_login(self):
        """Attempt auto-login with saved credentials."""
        try:
            self._loading_lbl.setText("Conectando automaticamente...")
            self._on_login()
        except Exception:
            self._loading_lbl.setText("")
            self._clear_remember()
            self._pass_entry.clear()
            self._pass_entry.setFocus()

    def _save_last_email(self, email: str):
        os.makedirs(_APP_DATA_DIR, exist_ok=True)
        try:
            with open(_LAST_EMAIL_FILE, "w", encoding="utf-8") as fh:
                json.dump({"email": email}, fh)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _set_loading(self, loading: bool):
        if loading:
            self._loading_lbl.setText("Autenticando...")
            self._login_btn.setEnabled(False)
        else:
            self._loading_lbl.setText("")
            self._login_btn.setEnabled(True)

    def _show_error(self, msg: str):
        self._error_lbl.setText(msg)

    @Slot()
    def _on_login(self):
        if self._login_in_progress:
            return
        email = self._email_entry.text().strip()
        password = self._pass_entry.text().strip()
        if not email or not password:
            self._show_error("Preencha e-mail e senha.")
            return

        self._login_in_progress = True
        self._show_error("")
        self._set_loading(True)

        def _do():
            try:
                from auth.supabase_client import SupabaseAuth

                auth = SupabaseAuth()
                session = auth.login(email, password)

                if session is None:
                    self._sig_login_failed.emit(
                        "Sessao nao retornada. Verifique suas credenciais."
                    )
                    return

                # Check license
                user_id = session.user.id if hasattr(session, "user") else None
                license_info = auth.check_license(user_id) if user_id else {}
                is_active = license_info.get("is_active", False)

                # Try to update offline cache (non-critical)
                try:
                    from auth.license_guard import LicenseGuard
                    guard = LicenseGuard()
                    guard.check(session)
                except Exception:
                    pass

                self._sig_login_success.emit(
                    auth, session, license_info, email, is_active
                )
            except Exception as exc:
                self._sig_login_failed.emit(str(exc))

        t = threading.Thread(target=_do, daemon=True)
        t.start()

        # Timeout: 15 seconds
        def _check_timeout():
            if t.is_alive() and self._login_in_progress:
                self._login_failed("Tempo esgotado. Verifique sua conexao.")
        QTimer.singleShot(15000, _check_timeout)

    def _login_success(self, auth, session, license_info, email, is_active):
        self._login_in_progress = False
        self._set_loading(False)
        self._save_last_email(email)

        if not is_active:
            self._show_error(
                "Sua licenca nao esta ativa. Entre em contato com um administrador."
            )
            self._clear_remember()
            return

        # Save or clear "remember me"
        if self._remember_cb.isChecked():
            self._save_remember(email, self._pass_entry.text().strip())
        else:
            self._clear_remember()

        # Store results and close
        self.auth = auth
        self.session = session
        self.license_info = license_info
        self._authenticated = True
        self.accept()

    def _login_failed(self, msg: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._clear_remember()
        self._show_error(msg)

    def _on_register(self):
        if self._login_in_progress:
            return
        email = self._email_entry.text().strip()
        password = self._pass_entry.text().strip()
        if not email or not password:
            self._show_error("Preencha e-mail e senha para registrar.")
            return

        self._login_in_progress = True
        self._show_error("")
        self._set_loading(True)

        def _do():
            try:
                from auth.supabase_client import SupabaseAuth

                auth = SupabaseAuth()
                auth.register(email, password)
                self._sig_register_done.emit(email)
            except Exception as exc:
                self._sig_register_failed.emit(str(exc))

        t = threading.Thread(target=_do, daemon=True)
        t.start()

        # Timeout
        def _check_timeout():
            if t.is_alive() and self._login_in_progress:
                self._register_failed("Tempo esgotado. Verifique sua conexao.")
        QTimer.singleShot(15000, _check_timeout)

    def _register_failed(self, msg: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._show_error(msg)

    def _register_done(self, email: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._save_last_email(email)
        self._show_error("")
        QMessageBox.information(
            self,
            "Registro",
            "Conta criada com sucesso!\nVerifique seu e-mail e faca login.",
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def authenticated(self) -> bool:
        return self._authenticated
