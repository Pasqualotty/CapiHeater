"""
Auto-updater for CapiHeater.

Checks GitHub releases for newer versions, downloads the .exe asset,
and replaces the running executable via a helper batch script.
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
            ``{"version": "0.1.1", "download_url": "...", "notes": "..."}``
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
        for asset in data.get("assets", []):
            name: str = asset.get("name", "")
            if name.lower().endswith(".exe"):
                download_url = asset.get("browser_download_url")
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
        }

    # ------------------------------------------------------------------
    # Download & apply
    # ------------------------------------------------------------------

    def download_and_apply(
        self,
        download_url: str,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Download the new .exe and schedule replacement on exit.

        Parameters
        ----------
        download_url:
            Direct URL to the ``.exe`` asset.
        on_progress:
            Optional callback ``(bytes_downloaded, total_bytes)``
            called periodically during the download.
        """
        # Where is the currently running exe?
        current_exe = sys.executable
        if not getattr(sys, "frozen", False):
            logger.warning(
                "Not running as a frozen exe — update will download "
                "but skip the replacement step."
            )

        # Always target the canonical exe name so temp files don't accumulate.
        exe_dir = os.path.dirname(os.path.abspath(current_exe))
        current_exe = os.path.join(exe_dir, "CapiHeater.exe")
        fd, tmp_path = tempfile.mkstemp(suffix=".exe", dir=exe_dir)
        os.close(fd)

        try:
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": f"CapiHeater/{__version__}"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024

                with open(tmp_path, "wb") as out:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if on_progress:
                            on_progress(downloaded, total)
        except Exception:
            # Clean up partial download
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Build a small batch script that:
        #   1. Waits for the current process to exit
        #   2. Replaces the old exe with the new one
        #   3. Launches the new exe
        #   4. Deletes itself
        self._apply_via_batch(current_exe, tmp_path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_via_batch(target_exe: str, new_exe_tmp: str) -> None:
        """Create and run a batch script that swaps executables."""
        running_exe = os.path.abspath(sys.executable)
        running_pid = os.getpid()
        exe_dir = os.path.dirname(target_exe)

        bat_fd, bat_path = tempfile.mkstemp(suffix=".bat")
        os.close(bat_fd)

        target_esc = target_exe.replace("/", "\\")
        new_tmp_esc = new_exe_tmp.replace("/", "\\")
        running_esc = running_exe.replace("/", "\\")
        bat_esc = bat_path.replace("/", "\\")
        dir_esc = exe_dir.replace("/", "\\")

        old_backup = target_exe + ".old"
        old_esc = old_backup.replace("/", "\\")

        log_path = os.path.join(exe_dir, "_update.log").replace("/", "\\")

        # ping -n N waits (N-1) seconds — works without a console window,
        # unlike 'timeout' which fails silently under CREATE_NO_WINDOW.
        wait_2s = "ping -n 3 127.0.0.1 >nul 2>&1"

        script = (
            "@echo off\n"
            f'echo [%date% %time%] Update script started >> "{log_path}"\n'
            f'echo   target  = {target_esc} >> "{log_path}"\n'
            f'echo   new_tmp = {new_tmp_esc} >> "{log_path}"\n'
            f'echo   running = {running_esc} (PID {running_pid}) >> "{log_path}"\n'
            # --- Wait for the parent process to fully exit ---
            # Poll until the PID is gone (max ~30 seconds)
            ":wait_exit\n"
            f'tasklist /FI "PID eq {running_pid}" 2>nul | find "{running_pid}" >nul 2>&1\n'
            "if %errorlevel%==0 (\n"
            f"    {wait_2s}\n"
            "    goto wait_exit\n"
            ")\n"
            f'echo [%date% %time%] Parent process exited >> "{log_path}"\n'
            # Extra 1-second grace period for file handles to release
            "ping -n 2 127.0.0.1 >nul 2>&1\n"
            # --- Delete any previous .old backup ---
            f'del /f "{old_esc}" 2>nul\n'
            # --- Rename current exe out of the way ---
            "set RETRIES=0\n"
            ":rename_old\n"
            f'if not exist "{target_esc}" goto do_move\n'
            f'ren "{target_esc}" "CapiHeater.exe.old" 2>nul\n'
            f'if not exist "{target_esc}" goto do_move\n'
            "set /a RETRIES+=1\n"
            f'echo [%date% %time%] rename attempt %RETRIES% failed >> "{log_path}"\n'
            "if %RETRIES% GEQ 10 goto force_copy\n"
            f"{wait_2s}\n"
            "goto rename_old\n"
            # --- Move new exe into place ---
            ":do_move\n"
            f'echo [%date% %time%] Moving new exe into place >> "{log_path}"\n'
            f'move /y "{new_tmp_esc}" "{target_esc}"\n'
            "if errorlevel 1 (\n"
            f'    echo [%date% %time%] MOVE FAILED, trying copy >> "{log_path}"\n'
            "    goto force_copy\n"
            ")\n"
            f'echo [%date% %time%] Move succeeded >> "{log_path}"\n'
            "goto cleanup\n"
            # --- Fallback: copy over the target if rename+move failed ---
            ":force_copy\n"
            f'echo [%date% %time%] Falling back to copy >> "{log_path}"\n'
            f'copy /y "{new_tmp_esc}" "{target_esc}" >nul 2>&1\n'
            "if errorlevel 1 (\n"
            f'    echo [%date% %time%] COPY ALSO FAILED >> "{log_path}"\n'
            "    goto cleanup\n"
            ")\n"
            f'del /f "{new_tmp_esc}" 2>nul\n'
            f'echo [%date% %time%] Copy succeeded >> "{log_path}"\n'
            # --- Cleanup ---
            ":cleanup\n"
            f'del /f "{old_esc}" 2>nul\n'
            f'if /i not "{running_esc}"=="{target_esc}" (\n'
            f'    del /f "{running_esc}" 2>nul\n'
            ")\n"
            f'pushd "{dir_esc}"\n'
            f'for %%F in (tmp*.exe) do del /f "%%F" 2>nul\n'
            f'del /f "CapiHeater.exe.old" 2>nul\n'
            f"popd\n"
            f'echo [%date% %time%] Launching updated exe >> "{log_path}"\n'
            f'start "" "{target_esc}"\n'
            f'echo [%date% %time%] Done >> "{log_path}"\n'
            f'del /f "{bat_esc}"\n'
        )

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(script)

        # CREATE_NO_WINDOW (not DETACHED_PROCESS): allocates a hidden
        # console so cmd.exe built-ins work.  DETACHED_PROCESS gives
        # cmd.exe NO console at all, which broke 'timeout' silently.
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        logger.info("Update batch script launched — exiting current process.")
        os._exit(0)
