"""
LicenseGuard - Offline-capable license validation with encrypted local cache.
"""

import json
import os
import time
from pathlib import Path

from cryptography.fernet import Fernet

# Cache lives in the user's app-data directory
_APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "CapiHeater"
)
_CACHE_FILE = os.path.join(_APP_DATA_DIR, "license_cache.enc")
_KEY_FILE = os.path.join(_APP_DATA_DIR, "license.key")
_CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds


class LicenseGuard:
    """Validates a license using the session and keeps an encrypted local cache."""

    def __init__(self):
        os.makedirs(_APP_DATA_DIR, exist_ok=True)
        self._fernet = Fernet(self.get_or_generate_key())

    # ------------------------------------------------------------------
    # Fernet key management
    # ------------------------------------------------------------------

    @staticmethod
    def get_or_generate_key() -> bytes:
        """Load the Fernet key from disk or create a new one."""
        if os.path.exists(_KEY_FILE):
            with open(_KEY_FILE, "rb") as fh:
                key = fh.read()
            # Basic sanity check
            if len(key) >= 32:
                return key
        key = Fernet.generate_key()
        with open(_KEY_FILE, "wb") as fh:
            fh.write(key)
        return key

    # ------------------------------------------------------------------
    # Encrypted cache helpers
    # ------------------------------------------------------------------

    def _write_cache(self, data: dict):
        payload = json.dumps(data).encode("utf-8")
        token = self._fernet.encrypt(payload)
        with open(_CACHE_FILE, "wb") as fh:
            fh.write(token)

    def _read_cache(self) -> dict | None:
        if not os.path.exists(_CACHE_FILE):
            return None
        try:
            with open(_CACHE_FILE, "rb") as fh:
                token = fh.read()
            payload = self._fernet.decrypt(token)
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, session) -> bool:
        """Return ``True`` if the license is active.

        *session* is expected to be the object returned by
        ``SupabaseAuth.login()`` (or ``None``).

        Strategy:
        1. If a live session is available, query Supabase and update cache.
        2. If offline (session is None or query fails), fall back to the
           local encrypted cache (valid for 24 h).
        """
        # Try online check
        if session is not None:
            try:
                from auth.supabase_client import SupabaseAuth

                auth = SupabaseAuth()
                user_id = session.user.id if hasattr(session, "user") else None
                if user_id:
                    info = auth.check_license(user_id)
                    # Persist to cache
                    cache_data = {
                        "is_active": info.get("is_active", False),
                        "role": info.get("role", "user"),
                        "ts": time.time(),
                    }
                    self._write_cache(cache_data)
                    return bool(info.get("is_active", False))
            except Exception:
                pass  # fall through to cache

        # Offline / fallback: use cached result
        cached = self._read_cache()
        if cached is None:
            return False

        age = time.time() - cached.get("ts", 0)
        if age > _CACHE_TTL:
            return False  # cache expired

        return bool(cached.get("is_active", False))

    def cached_role(self) -> str:
        """Return the role from the local cache (or ``'user'``)."""
        cached = self._read_cache()
        if cached is None:
            return "user"
        return cached.get("role", "user")
