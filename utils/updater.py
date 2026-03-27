"""
Auto-updater for CapiHeater.

Checks GitHub releases for newer versions, downloads the .exe asset,
verifies its integrity, and replaces the running executable via a
helper batch script with rollback support.
"""

import json
import os
import sys
import tempfile
import subprocess
import urllib.request
import urllib.error
from typing import Callable

from version import __version__
from utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_API_LATEST = (
    "https://api.github.com/repos/Pasqualotty/CapiHeater/releases/latest"
)

# Minimum valid exe size (5 MB) — prevents applying truncated downloads
_MIN_EXE_SIZE = 5 * 1024 * 1024


def _parse_version(tag: str) -> tuple[int, ...]:
    """Turn a tag like 'v0.1.1' or '0.1.1' into a comparable tuple."""
    tag = tag.lstrip("vV")
    parts: list[int] = []
    for segment in tag.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _is_valid_pe(path: str) -> bool:
    """Check if a file is a valid PE executable (MZ header)."""
    try:
        with open(path, "rb") as f:
            magic = f.read(2)
        return magic == b"MZ"
    except Exception:
        return False


class AutoUpdater:
    """Handles checking, downloading, and applying updates from GitHub."""

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def check_for_update(self) -> dict | None:
        """Return info about the latest release if it is newer, else *None*.

        Returns
        -------
        dict | None
            ``{"version": "0.1.1", "download_url": "...", "notes": "...",
               "size": 12345678}``
            or *None* when already up-to-date or on error.
        """
        try:
            req = urllib.request.Request(
                GITHUB_API_LATEST,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"CapiHeater/{__version__}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            logger.warning(f"Update check failed: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"Unexpected error during update check: {exc}")
            return None

        tag: str = data.get("tag_name", "")
        if not tag:
            return None

        remote_ver = _parse_version(tag)
        local_ver = _parse_version(__version__)

        if remote_ver <= local_ver:
            logger.info(f"Already up-to-date ({__version__})")
            return None

        # Find the .exe asset
        download_url: str | None = None
        asset_size: int = 0
        for asset in data.get("assets", []):
            name: str = asset.get("name", "")
            if name.lower().endswith(".exe"):
                download_url = asset.get("browser_download_url")
                asset_size = asset.get("size", 0)
                break

        if not download_url:
            logger.warning("New release found but no .exe asset attached.")
            return None

        version_str = tag.lstrip("vV")
        notes = data.get("body", "") or ""

        logger.info(f"Update available: {version_str} ({download_url})")
        return {
            "version": version_str,
            "download_url": download_url,
            "notes": notes,
            "size": asset_size,
        }

    # ------------------------------------------------------------------
    # Download & apply
    # ------------------------------------------------------------------

    def download_and_apply(
        self,
        download_url: str,
        on_progress: Callable[[int, int], None] | None = None,
        expected_size: int = 0,
    ) -> None:
        """Download the new .exe, verify it, and schedule replacement.

        Parameters
        ----------
        download_url:
            Direct URL to the ``.exe`` asset.
        on_progress:
            Optional callback ``(bytes_downloaded, total_bytes)``
            called periodically during the download.
        expected_size:
            Expected file size from the GitHub API (for validation).
        """
        if not getattr(sys, "frozen", False):
            logger.warning(
                "Not running as a frozen exe — update will download "
                "but skip the replacement step."
            )

        # Always target the canonical exe name.
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        target_exe = os.path.join(exe_dir, "CapiHeater.exe")

        # Download to a .download file (NOT .exe) to avoid antivirus
        # interference during the download.
        fd, tmp_path = tempfile.mkstemp(suffix=".download", dir=exe_dir)
        os.close(fd)

        try:
            self._download_file(download_url, tmp_path, on_progress)
            self._verify_download(tmp_path, expected_size)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Rename to .exe now that it's verified
        final_tmp = tmp_path.replace(".download", ".exe")
        try:
            if os.path.exists(final_tmp):
                os.unlink(final_tmp)
            os.rename(tmp_path, final_tmp)
        except OSError:
            # Fallback: keep .download extension, batch will handle it
            final_tmp = tmp_path

        logger.info(f"Download verified: {os.path.getsize(final_tmp)} bytes, valid PE")
        self._apply_via_batch(target_exe, final_tmp)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @staticmethod
    def _download_file(
        url: str,
        dest: str,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Download a file with progress reporting."""
        req = urllib.request.Request(
            url, headers={"User-Agent": f"CapiHeater/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024

            with open(dest, "wb") as out:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)

            # Verify complete download
            if total > 0 and downloaded != total:
                raise RuntimeError(
                    f"Download incompleto: {downloaded}/{total} bytes"
                )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_download(path: str, expected_size: int = 0) -> None:
        """Verify the downloaded file is a valid PE executable."""
        file_size = os.path.getsize(path)

        # Check minimum size
        if file_size < _MIN_EXE_SIZE:
            raise RuntimeError(
                f"Arquivo muito pequeno ({file_size} bytes). "
                f"Minimo esperado: {_MIN_EXE_SIZE} bytes. "
                f"Download provavelmente corrompido."
            )

        # Check against expected size from GitHub API
        if expected_size > 0:
            tolerance = expected_size * 0.01  # 1% tolerance
            if abs(file_size - expected_size) > tolerance:
                raise RuntimeError(
                    f"Tamanho do arquivo ({file_size}) nao confere com "
                    f"esperado ({expected_size}). Download corrompido."
                )

        # Verify PE header (MZ magic bytes)
        if not _is_valid_pe(path):
            raise RuntimeError(
                "Arquivo baixado nao e um executavel valido (header MZ ausente)."
            )

        logger.info(
            f"Download verificado: {file_size} bytes, PE valido"
        )

    # ------------------------------------------------------------------
    # Apply via batch script
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_via_batch(target_exe: str, new_exe_tmp: str) -> None:
        """Create and run a batch script that swaps executables."""
        running_exe = os.path.abspath(sys.executable)
        running_pid = os.getpid()
        exe_dir = os.path.dirname(target_exe)

        bat_fd, bat_path = tempfile.mkstemp(suffix=".bat")
        os.close(bat_fd)

        # Escape paths for batch (forward slash → backslash)
        target_esc = target_exe.replace("/", "\\")
        new_tmp_esc = new_exe_tmp.replace("/", "\\")
        running_esc = running_exe.replace("/", "\\")
        bat_esc = bat_path.replace("/", "\\")
        dir_esc = exe_dir.replace("/", "\\")

        old_esc = (target_exe + ".old").replace("/", "\\")
        log_path = os.path.join(exe_dir, "_update.log").replace("/", "\\")

        # ping -n N waits (N-1) seconds — works without a console window.
        wait_3s = "ping -n 4 127.0.0.1 >nul 2>&1"

        script = (
            "@echo off\n"
            f'echo [%date% %time%] ====== Update script started ====== >> "{log_path}"\n'
            f'echo   target  = {target_esc} >> "{log_path}"\n'
            f'echo   new_tmp = {new_tmp_esc} >> "{log_path}"\n'
            f'echo   running = {running_esc} (PID {running_pid}) >> "{log_path}"\n'
            "\n"
            "REM --- Wait for the parent process to fully exit ---\n"
            ":wait_exit\n"
            f'tasklist /FI "PID eq {running_pid}" 2>nul | find "{running_pid}" >nul 2>&1\n'
            "if %errorlevel%==0 (\n"
            f"    {wait_3s}\n"
            "    goto wait_exit\n"
            ")\n"
            f'echo [%date% %time%] Parent process exited >> "{log_path}"\n'
            "\n"
            "REM --- Grace period for file handles to release ---\n"
            "ping -n 6 127.0.0.1 >nul 2>&1\n"
            "\n"
            "REM --- Verify the new file exists and is valid ---\n"
            f'if not exist "{new_tmp_esc}" (\n'
            f'    echo [%date% %time%] FATAL: new exe not found: {new_tmp_esc} >> "{log_path}"\n'
            "    goto abort\n"
            ")\n"
            "\n"
            "REM --- Delete any previous .old backup ---\n"
            f'del /f "{old_esc}" 2>nul\n'
            "\n"
            "REM --- Rename current exe out of the way (30 retries = ~90 sec) ---\n"
            "set RETRIES=0\n"
            ":rename_old\n"
            f'if not exist "{target_esc}" goto do_move\n'
            f'ren "{target_esc}" "CapiHeater.exe.old" 2>nul\n'
            f'if not exist "{target_esc}" goto do_move\n'
            "set /a RETRIES+=1\n"
            f'echo [%date% %time%] rename attempt %RETRIES% failed >> "{log_path}"\n'
            "if %RETRIES% GEQ 30 goto force_copy\n"
            f"{wait_3s}\n"
            "goto rename_old\n"
            "\n"
            "REM --- Move new exe into place ---\n"
            ":do_move\n"
            f'echo [%date% %time%] Moving new exe into place >> "{log_path}"\n'
            f'move /y "{new_tmp_esc}" "{target_esc}"\n'
            "if errorlevel 1 (\n"
            f'    echo [%date% %time%] MOVE FAILED, trying copy >> "{log_path}"\n'
            "    goto force_copy\n"
            ")\n"
            f'echo [%date% %time%] Move succeeded >> "{log_path}"\n'
            "goto launch\n"
            "\n"
            "REM --- Fallback: copy over the target ---\n"
            ":force_copy\n"
            f'echo [%date% %time%] Falling back to copy >> "{log_path}"\n'
            f'copy /y "{new_tmp_esc}" "{target_esc}" >nul 2>&1\n'
            "if errorlevel 1 (\n"
            f'    echo [%date% %time%] COPY ALSO FAILED - aborting >> "{log_path}"\n'
            "    goto abort\n"
            ")\n"
            f'del /f "{new_tmp_esc}" 2>nul\n'
            f'echo [%date% %time%] Copy succeeded >> "{log_path}"\n'
            "goto launch\n"
            "\n"
            "REM --- Abort: restore backup if available ---\n"
            ":abort\n"
            f'echo [%date% %time%] UPDATE FAILED - attempting recovery >> "{log_path}"\n'
            f'if exist "{old_esc}" (\n'
            f'    echo [%date% %time%] Restoring backup >> "{log_path}"\n'
            f'    if not exist "{target_esc}" (\n'
            f'        ren "{old_esc}" "CapiHeater.exe" 2>nul\n'
            "    ) else (\n"
            f'        copy /y "{old_esc}" "{target_esc}" >nul 2>&1\n'
            "    )\n"
            ")\n"
            f'if exist "{target_esc}" (\n'
            f'    echo [%date% %time%] Launching recovered exe >> "{log_path}"\n'
            f'    start "" "{target_esc}"\n'
            ")\n"
            f'echo [%date% %time%] Abort complete >> "{log_path}"\n'
            "goto end\n"
            "\n"
            "REM --- Launch updated exe ---\n"
            ":launch\n"
            # Clean up temp files and old backup
            f'del /f "{old_esc}" 2>nul\n'
            f'if /i not "{running_esc}"=="{target_esc}" (\n'
            f'    del /f "{running_esc}" 2>nul\n'
            ")\n"
            # Delete only the specific temp file, not a glob
            f'del /f "{new_tmp_esc}" 2>nul\n'
            f'echo [%date% %time%] Launching updated exe >> "{log_path}"\n'
            f'start "" "{target_esc}"\n'
            f'echo [%date% %time%] Update complete >> "{log_path}"\n'
            "\n"
            ":end\n"
            f'del /f "{bat_esc}"\n'
        )

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(script)

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        logger.info("Update batch script launched — exiting current process.")
        os._exit(0)
