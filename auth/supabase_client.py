"""
SupabaseAuth - Authentication and license management via Supabase.
"""

from supabase import create_client, Client
from datetime import datetime, timezone

# ----- Placeholders: substituir pelos valores reais do seu projeto Supabase -----
SUPABASE_URL = "https://mhxsxkkmxnfpaqmfricc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHN4a2tteG5mcGFxbWZyaWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTMyNjYsImV4cCI6MjA4OTU4OTI2Nn0.kWURNeVbPgn2Az_zLs2q_eSrh61Ah6FWhXamg6YckHw"


class SupabaseAuth:
    """Handles authentication, license checking and user management."""

    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_KEY):
        self.url = url
        self.key = key
        self._session = None
        self._client: Client | None = None
        self._init_client()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_client(self):
        """Create the Supabase client. Silently fails when placeholders are used."""
        try:
            self._client = create_client(self.url, self.key)
        except Exception:
            self._client = None

    def _ensure_client(self):
        if self._client is None:
            raise ConnectionError(
                "Cliente Supabase nao inicializado. Verifique SUPABASE_URL e SUPABASE_KEY."
            )

    @staticmethod
    def is_configured() -> bool:
        """Return True when real Supabase credentials are set."""
        return (
            SUPABASE_URL != "https://your-project.supabase.co"
            and SUPABASE_KEY != "your-anon-key"
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, email: str, password: str):
        """Authenticate with email/password. Returns session dict or raises."""
        self._ensure_client()
        try:
            response = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            self._session = response.session
            return self._session
        except Exception as exc:
            raise RuntimeError(f"Erro ao fazer login: {exc}") from exc

    def register(self, email: str, password: str):
        """Create a new user account and an inactive license entry."""
        self._ensure_client()
        try:
            response = self._client.auth.sign_up(
                {"email": email, "password": password}
            )
            self._session = response.session

            # Create inactive license so the user appears in the Admin panel
            user_id = None
            if self._session and hasattr(self._session, "user"):
                user_id = self._session.user.id
            elif response.user:
                user_id = response.user.id

            if user_id:
                try:
                    self._client.table("licenses").insert({
                        "user_id": str(user_id),
                        "email": email,
                        "role": "user",
                        "is_active": False,
                        "grant_reason": "registration",
                    }).execute()
                except Exception:
                    pass  # License may already exist

            return self._session
        except Exception as exc:
            raise RuntimeError(f"Erro ao registrar: {exc}") from exc

    def logout(self):
        """Sign out the current user."""
        if self._client is not None:
            try:
                self._client.auth.sign_out()
            except Exception:
                pass
        self._session = None

    def get_session(self):
        """Return the current session object (may be None)."""
        return self._session

    # ------------------------------------------------------------------
    # License / role management  (table: ``licenses``)
    # Expected columns:
    #   user_id, email, role, is_active, expires_at,
    #   activated_at, granted_by, grant_reason
    # ------------------------------------------------------------------

    def check_license(self, user_id: str) -> dict:
        """Return license info for *user_id*.

        Returns dict with keys: is_active, role, expires_at.
        """
        self._ensure_client()
        try:
            result = (
                self._client.table("licenses")
                .select("is_active, role, expires_at")
                .eq("user_id", str(user_id))
                .execute()
            )
            rows = result.data
            if not rows:
                return {"is_active": False, "role": "user", "expires_at": None}
            data = rows[0]
            return {
                "is_active": bool(data.get("is_active", False)),
                "role": data.get("role", "user"),
                "expires_at": data.get("expires_at"),
            }
        except Exception as exc:
            print(f"[check_license] Error: {exc}")
            return {"is_active": False, "role": "user", "expires_at": None}

    def get_user_role(self, user_id: str) -> str:
        """Return the role string for *user_id* (default ``'user'``)."""
        info = self.check_license(user_id)
        return info.get("role", "user")

    def grant_access(self, email: str, granted_by_id: str, reason: str = ""):
        """Activate a license for *email*."""
        self._ensure_client()
        try:
            now = datetime.now(timezone.utc).isoformat()
            # Try to update existing license first
            result = (
                self._client.table("licenses")
                .update({
                    "is_active": True,
                    "activated_at": now,
                    "granted_by": granted_by_id,
                    "grant_reason": reason or "manual_grant",
                })
                .eq("email", email)
                .execute()
            )
            # If no rows updated, the user hasn't registered yet
            if not result.data:
                raise RuntimeError(
                    f"Usuario {email} nao encontrado. "
                    "O usuario precisa se registrar primeiro."
                )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Erro ao liberar acesso: {exc}") from exc

    def revoke_access(self, email: str):
        """Deactivate license for *email*."""
        self._ensure_client()
        try:
            self._client.table("licenses").update({"is_active": False}).eq(
                "email", email
            ).execute()
        except Exception as exc:
            raise RuntimeError(f"Erro ao revogar acesso: {exc}") from exc

    def list_users(self) -> list[dict]:
        """Return all rows from the licenses table (for the admin panel)."""
        self._ensure_client()
        try:
            result = (
                self._client.table("licenses")
                .select("email, role, is_active, activated_at, granted_by, grant_reason")
                .execute()
            )
            return result.data or []
        except Exception:
            return []
