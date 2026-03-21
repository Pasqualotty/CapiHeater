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
            # During development the script is run via python.exe.
            # We still allow testing, but the batch-replace step would be
            # a no-op.
            logger.warning(
                "Not running as a frozen exe — update will download "
                "but skip the replacement step."
            )

        # Download to a temp file next to the current exe so the later
        # rename stays on the same filesystem.
        exe_dir = os.path.dirname(os.path.abspath(current_exe))
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
    def _apply_via_batch(current_exe: str, new_exe_tmp: str) -> None:
        """Create and run a batch script that swaps executables."""
        bat_fd, bat_path = tempfile.mkstemp(suffix=".bat")
        os.close(bat_fd)

        current_exe_esc = current_exe.replace("/", "\\")
        new_exe_tmp_esc = new_exe_tmp.replace("/", "\\")
        bat_path_esc = bat_path.replace("/", "\\")

        script = (
            "@echo off\n"
            "echo Atualizando CapiHeater...\n"
            # Wait a bit for the current process to fully exit
            "timeout /t 3 /nobreak >nul\n"
            # Retry loop — the exe might still be locked briefly
            ":retry\n"
            f'del /f "{current_exe_esc}" 2>nul\n'
            f'if exist "{current_exe_esc}" (\n'
            "    timeout /t 1 /nobreak >nul\n"
            "    goto retry\n"
            ")\n"
            f'move /y "{new_exe_tmp_esc}" "{current_exe_esc}"\n'
            f'start "" "{current_exe_esc}"\n'
            # Delete this batch script
            f'del /f "{bat_path_esc}"\n'
        )

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(script)

        # Launch the batch script detached and exit this process
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
        logger.info("Update batch script launched — exiting current process.")
        os._exit(0)
