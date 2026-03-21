"""
LoginWindow - Tela de login do CapiHeater (dark themed, PT-BR).
"""

import json
import os
import tkinter as tk
from tkinter import messagebox
import threading

# App-data directory for persisting last e-mail
_APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "CapiHeater"
)
_LAST_EMAIL_FILE = os.path.join(_APP_DATA_DIR, "last_email.json")
_REMEMBER_FILE = os.path.join(_APP_DATA_DIR, "remember.dat")
_REMEMBER_KEY_FILE = os.path.join(_APP_DATA_DIR, "rkey.dat")

# Theme colours
BG = "#1a1a2e"
FG = "#ffffff"
ACCENT = "#0f3460"
ENTRY_BG = "#16213e"
ERROR_FG = "#ff4444"


class LoginWindow(tk.Tk):
    """Standalone login window. Sets ``self.session`` and ``self.auth``
    when login succeeds, then destroys itself so the caller can proceed."""

    def __init__(self):
        super().__init__()

        self.title("CapiHeater - Login")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("400x480")

        # Centre on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 480) // 2
        self.geometry(f"+{x}+{y}")

        # Public attributes set after successful login
        self.session = None
        self.auth = None
        self.license_info: dict | None = None
        self._authenticated = False
        self._login_in_progress = False

        self._build_ui()
        self._load_last_email()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Title / logo area
        title_lbl = tk.Label(
            self, text="CapiHeater", font=("Segoe UI", 24, "bold"), bg=BG, fg=FG
        )
        title_lbl.pack(pady=(40, 5))

        subtitle_lbl = tk.Label(
            self,
            text="Aquecedor de Contas Twitter/X",
            font=("Segoe UI", 10),
            bg=BG,
            fg="#8888aa",
        )
        subtitle_lbl.pack(pady=(0, 30))

        # E-mail
        tk.Label(self, text="E-mail", font=("Segoe UI", 10), bg=BG, fg=FG).pack(
            anchor="w", padx=50
        )
        self._email_var = tk.StringVar()
        self._email_entry = tk.Entry(
            self,
            textvariable=self._email_var,
            font=("Segoe UI", 11),
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            highlightthickness=1,
            highlightcolor=ACCENT,
        )
        self._email_entry.pack(fill="x", padx=50, pady=(2, 12), ipady=6)

        # Senha
        tk.Label(self, text="Senha", font=("Segoe UI", 10), bg=BG, fg=FG).pack(
            anchor="w", padx=50
        )
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(
            self,
            textvariable=self._pass_var,
            show="*",
            font=("Segoe UI", 11),
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            highlightthickness=1,
            highlightcolor=ACCENT,
        )
        self._pass_entry.pack(fill="x", padx=50, pady=(2, 10), ipady=6)

        # Lembrar de mim checkbox
        self._remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self,
            text="Lembrar de mim",
            variable=self._remember_var,
            font=("Segoe UI", 9),
            bg=BG,
            fg="#8888aa",
            selectcolor=ENTRY_BG,
            activebackground=BG,
            activeforeground=FG,
            cursor="hand2",
        ).pack(anchor="w", padx=50, pady=(0, 10))

        # Error label (hidden by default)
        self._error_var = tk.StringVar()
        self._error_lbl = tk.Label(
            self,
            textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg=BG,
            fg=ERROR_FG,
            wraplength=300,
        )
        self._error_lbl.pack(pady=(0, 8))

        # Entrar button
        self._login_btn = tk.Button(
            self,
            text="Entrar",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT,
            fg=FG,
            activebackground="#1a5276",
            activeforeground=FG,
            relief="flat",
            cursor="hand2",
            command=self._on_login,
        )
        self._login_btn.pack(fill="x", padx=50, ipady=6)

        # Registrar link
        reg_lbl = tk.Label(
            self,
            text="Ainda nao tem conta? Registrar",
            font=("Segoe UI", 9, "underline"),
            bg=BG,
            fg="#5588cc",
            cursor="hand2",
        )
        reg_lbl.pack(pady=(14, 0))
        reg_lbl.bind("<Button-1>", lambda _e: self._on_register())

        # Loading label
        self._loading_var = tk.StringVar()
        tk.Label(
            self,
            textvariable=self._loading_var,
            font=("Segoe UI", 9),
            bg=BG,
            fg="#aaaacc",
        ).pack(pady=(10, 0))

        # Bind Enter key
        self.bind("<Return>", lambda _e: self._on_login())

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
        for f in (_REMEMBER_FILE, _REMEMBER_KEY_FILE):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def _load_last_email(self):
        # Try auto-login with saved credentials first
        try:
            saved = self._load_remember()
            if saved and saved[0] and saved[1]:
                self._email_var.set(saved[0])
                self._pass_var.set(saved[1])
                self._remember_var.set(True)
                # Auto-login after UI fully renders
                self.after(500, self._auto_login)
                return
        except Exception:
            pass

        # Otherwise just load last email
        try:
            with open(_LAST_EMAIL_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                email = data.get("email", "")
                if email:
                    self._email_var.set(email)
                    self._pass_entry.focus_set()
                    return
        except Exception:
            pass
        self._email_entry.focus_set()

    def _auto_login(self):
        """Attempt auto-login with saved credentials. Falls back to manual on failure."""
        try:
            self._loading_var.set("Conectando automaticamente...")
            self._on_login()
        except Exception:
            self._loading_var.set("")
            self._clear_remember()
            self._pass_var.set("")
            self._pass_entry.focus_set()

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
            self._loading_var.set("Autenticando...")
            self._login_btn.config(state="disabled")
        else:
            self._loading_var.set("")
            self._login_btn.config(state="normal")

    def _show_error(self, msg: str):
        self._error_var.set(msg)

    def _on_login(self):
        if self._login_in_progress:
            return
        email = self._email_var.get().strip()
        password = self._pass_var.get().strip()
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
                    self.after(0, lambda: self._login_failed("Sessao nao retornada. Verifique suas credenciais."))
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

                self.after(0, lambda: self._login_success(auth, session, license_info, email, is_active))
            except Exception as exc:
                self.after(0, lambda: self._login_failed(str(exc)))

        t = threading.Thread(target=_do, daemon=True)
        t.start()

        # Timeout: if login takes more than 15 seconds, cancel
        def _check_timeout():
            if t.is_alive() and self._login_in_progress:
                self._login_failed("Tempo esgotado. Verifique sua conexao.")
        self.after(15000, _check_timeout)

    def _login_success(self, auth, session, license_info, email, is_active):
        self._login_in_progress = False
        self._set_loading(False)
        self._save_last_email(email)

        if not is_active:
            self._show_error(
                "Sua licenca nao esta ativa. Entre em contato com um administrador."
            )
            # Clear saved credentials if license is inactive
            self._clear_remember()
            return

        # Save or clear "remember me"
        if self._remember_var.get():
            self._save_remember(email, self._pass_var.get().strip())
        else:
            self._clear_remember()

        # Store results and close
        self.auth = auth
        self.session = session
        self.license_info = license_info
        self._authenticated = True
        self.destroy()

    def _login_failed(self, msg: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._clear_remember()
        self._show_error(msg)

    def _on_register(self):
        if self._login_in_progress:
            return
        email = self._email_var.get().strip()
        password = self._pass_var.get().strip()
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
                self.after(0, lambda: self._register_done(email))
            except Exception as exc:
                self.after(0, lambda: self._register_failed(str(exc)))

        t = threading.Thread(target=_do, daemon=True)
        t.start()

        # Timeout
        def _check_timeout():
            if t.is_alive() and self._login_in_progress:
                self._register_failed("Tempo esgotado. Verifique sua conexao.")
        self.after(15000, _check_timeout)

    def _register_failed(self, msg: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._show_error(msg)

    def _register_done(self, email: str):
        self._login_in_progress = False
        self._set_loading(False)
        self._save_last_email(email)
        self._show_error("")
        messagebox.showinfo(
            "Registro",
            "Conta criada com sucesso!\nVerifique seu e-mail e faca login.",
            parent=self,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def authenticated(self) -> bool:
        return self._authenticated
