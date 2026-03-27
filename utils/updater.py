"""
Auto-updater for CapiHeater (onedir zip mode).

Checks GitHub releases for newer versions, downloads the .zip asset,
verifies integrity, and replaces the application directory via a
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

_MIN_ZIP_SIZE = 5 * 1024 * 1024


def _parse_version(tag: str) -> tuple[int, ...]:
    tag = tag.lstrip("vV")
    parts: list[int] = []
    for segment in tag.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class AutoUpdater:

    def check_for_update(self) -> dict | None:
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
        except Exception as exc:
            logger.warning(f"Update check failed: {exc}")
            return None

        tag: str = data.get("tag_name", "")
        if not tag:
            return None

        remote_ver = _parse_version(tag)
        local_ver = _parse_version(__version__)

        if remote_ver <= local_ver:
            logger.info(f"Already up-to-date ({__version__})")
            return None

        # Find the .zip or .exe asset
        download_url: str | None = None
        asset_size: int = 0
        for asset in data.get("assets", []):
            name: str = asset.get("name", "")
            if name.lower().endswith(".zip"):
                download_url = asset.get("browser_download_url")
                asset_size = asset.get("size", 0)
                break
        # Fallback to .exe for backwards compat with older releases
        if not download_url:
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    asset_size = asset.get("size", 0)
                    break

        if not download_url:
            logger.warning("No .zip or .exe asset found in release.")
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

    def download_and_apply(
        self,
        download_url: str,
        on_progress: Callable[[int, int], None] | None = None,
        expected_size: int = 0,
    ) -> None:
        if not getattr(sys, "frozen", False):
            logger.warning("Not frozen — skipping replacement.")
            return

        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        is_zip = download_url.lower().endswith(".zip")

        # Download to temp file
        suffix = ".zip" if is_zip else ".exe"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=exe_dir)
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

        if is_zip:
            # Extract zip to a temp directory next to the exe
            extract_dir = os.path.join(exe_dir, "_update_new")
            self._extract_zip(tmp_path, extract_dir)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            self._apply_dir_update(exe_dir, extract_dir)
        else:
            # Legacy: single exe update (old releases)
            target_exe = os.path.join(exe_dir, "CapiHeater.exe")
            final_tmp = tmp_path.replace(suffix, ".exe")
            try:
                if os.path.exists(final_tmp):
                    os.unlink(final_tmp)
                os.rename(tmp_path, final_tmp)
            except OSError:
                final_tmp = tmp_path
            self._apply_exe_update(target_exe, final_tmp)

    @staticmethod
    def _download_file(url, dest, on_progress=None):
        req = urllib.request.Request(
            url, headers={"User-Agent": f"CapiHeater/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)
            if total > 0 and downloaded != total:
                raise RuntimeError(f"Download incompleto: {downloaded}/{total}")

    @staticmethod
    def _verify_download(path, expected_size=0):
        file_size = os.path.getsize(path)
        if file_size < _MIN_ZIP_SIZE:
            raise RuntimeError(
                f"Arquivo muito pequeno ({file_size} bytes). Download corrompido."
            )
        if expected_size > 0:
            tolerance = expected_size * 0.01
            if abs(file_size - expected_size) > tolerance:
                raise RuntimeError(
                    f"Tamanho ({file_size}) nao confere com esperado ({expected_size})."
                )

    @staticmethod
    def _extract_zip(zip_path, dest_dir):
        import zipfile
        import shutil
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        # Verify CapiHeater.exe exists in extracted files
        exe_path = os.path.join(dest_dir, "CapiHeater.exe")
        if not os.path.isfile(exe_path):
            raise RuntimeError("Zip nao contem CapiHeater.exe")
        logger.info(f"Extracted {len(os.listdir(dest_dir))} files to {dest_dir}")

    @staticmethod
    def _apply_dir_update(app_dir, new_dir):
        """Replace app files via batch script (onedir mode)."""
        running_exe = os.path.abspath(sys.executable)
        running_pid = os.getpid()

        bat_fd, bat_path = tempfile.mkstemp(suffix=".bat")
        os.close(bat_fd)

        app_esc = app_dir.replace("/", "\\")
        new_esc = new_dir.replace("/", "\\")
        running_esc = running_exe.replace("/", "\\")
        bat_esc = bat_path.replace("/", "\\")
        target_exe = os.path.join(app_dir, "CapiHeater.exe").replace("/", "\\")
        log_path = os.path.join(app_dir, "_update.log").replace("/", "\\")

        wait_3s = "ping -n 4 127.0.0.1 >nul 2>&1"

        script = (
            "@echo off\n"
            f'echo [%date% %time%] === Onedir update started === >> "{log_path}"\n'
            f'echo   app_dir = {app_esc} >> "{log_path}"\n'
            f'echo   new_dir = {new_esc} >> "{log_path}"\n'
            f'echo   PID = {running_pid} >> "{log_path}"\n'
            "\n"
            "REM --- Wait for process to exit ---\n"
            ":wait_exit\n"
            f'tasklist /FI "PID eq {running_pid}" 2>nul | find "{running_pid}" >nul 2>&1\n'
            "if %errorlevel%==0 (\n"
            f"    {wait_3s}\n"
            "    goto wait_exit\n"
            ")\n"
            f'echo [%date% %time%] Process exited >> "{log_path}"\n'
            "ping -n 4 127.0.0.1 >nul 2>&1\n"
            "\n"
            "REM --- Copy new files over old ones ---\n"
            f'echo [%date% %time%] Copying new files >> "{log_path}"\n'
            f'xcopy /s /y /q "{new_esc}\\*" "{app_esc}\\" >nul 2>&1\n'
            "if errorlevel 1 (\n"
            f'    echo [%date% %time%] XCOPY FAILED >> "{log_path}"\n'
            "    goto abort\n"
            ")\n"
            f'echo [%date% %time%] Copy succeeded >> "{log_path}"\n'
            "\n"
            "REM --- Cleanup and launch ---\n"
            f'rmdir /s /q "{new_esc}" 2>nul\n'
            f'echo [%date% %time%] Launching updated exe >> "{log_path}"\n'
            f'start "" "{target_exe}"\n'
            f'echo [%date% %time%] Update complete >> "{log_path}"\n'
            "goto end\n"
            "\n"
            ":abort\n"
            f'echo [%date% %time%] UPDATE FAILED >> "{log_path}"\n'
            # On failure, just launch the old exe (it still works)
            f'if exist "{target_exe}" start "" "{target_exe}"\n'
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
        logger.info("Update batch launched — exiting.")
        os._exit(0)

    @staticmethod
    def _apply_exe_update(target_exe, new_exe_tmp):
        """Legacy: replace single exe (for old onefile releases)."""
        running_exe = os.path.abspath(sys.executable)
        running_pid = os.getpid()
        exe_dir = os.path.dirname(target_exe)

        bat_fd, bat_path = tempfile.mkstemp(suffix=".bat")
        os.close(bat_fd)

        target_esc = target_exe.replace("/", "\\")
        new_tmp_esc = new_exe_tmp.replace("/", "\\")
        running_esc = running_exe.replace("/", "\\")
        bat_esc = bat_path.replace("/", "\\")
        old_esc = (target_exe + ".old").replace("/", "\\")
        log_path = os.path.join(exe_dir, "_update.log").replace("/", "\\")
        wait_3s = "ping -n 4 127.0.0.1 >nul 2>&1"

        script = (
            "@echo off\n"
            f'echo [%date% %time%] === Legacy exe update === >> "{log_path}"\n'
            ":wait_exit\n"
            f'tasklist /FI "PID eq {running_pid}" 2>nul | find "{running_pid}" >nul 2>&1\n'
            "if %errorlevel%==0 (\n"
            f"    {wait_3s}\n"
            "    goto wait_exit\n"
            ")\n"
            "ping -n 4 127.0.0.1 >nul 2>&1\n"
            f'del /f "{old_esc}" 2>nul\n'
            "set RETRIES=0\n"
            ":rename_old\n"
            f'if not exist "{target_esc}" goto do_move\n'
            f'ren "{target_esc}" "CapiHeater.exe.old" 2>nul\n'
            f'if not exist "{target_esc}" goto do_move\n'
            "set /a RETRIES+=1\n"
            "if %RETRIES% GEQ 30 goto abort\n"
            f"{wait_3s}\n"
            "goto rename_old\n"
            ":do_move\n"
            f'move /y "{new_tmp_esc}" "{target_esc}"\n'
            "if errorlevel 1 goto abort\n"
            f'del /f "{old_esc}" 2>nul\n'
            f'start "" "{target_esc}"\n'
            "goto end\n"
            ":abort\n"
            f'echo [%date% %time%] FAILED >> "{log_path}"\n'
            f'if exist "{old_esc}" ren "{old_esc}" "CapiHeater.exe" 2>nul\n'
            f'if exist "{target_esc}" start "" "{target_esc}"\n'
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
        logger.info("Legacy update batch launched — exiting.")
        os._exit(0)
