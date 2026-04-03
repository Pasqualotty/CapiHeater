"""
DriverFactory - Creates undetected Chrome WebDriver instances
with anti-detection measures and configurable options.
"""

import random
import threading

import undetected_chromedriver as uc

from utils.logger import get_logger

_logger = get_logger(__name__)


class DriverFactory:
    """Factory for creating configured undetected Chrome WebDriver instances."""

    # Serialize browser creation — uc.Chrome() patches the Chrome binary
    # in a shared temp directory.  Concurrent calls corrupt the patch.
    _creation_lock = threading.Lock()

    # Common desktop viewport sizes to randomize window dimensions
    _VIEWPORTS = [
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1600, 900),
        (1920, 1080),
        (1280, 800),
        (1280, 720),
    ]

    @staticmethod
    def _detect_chrome_version() -> int | None:
        """Detect the major version of the installed Chrome browser."""
        import os
        import subprocess

        # --- Attempt 1: Windows Registry (most reliable, no subprocess needed) ---
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    key = winreg.OpenKey(hive, r"SOFTWARE\Google\Chrome\BLBeacon")
                    version_str, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    major = int(version_str.split(".")[0])
                    _logger.info(f"Chrome versao detectada via Registry: {major}")
                    return major
                except (OSError, ValueError, IndexError):
                    continue
        except ImportError:
            pass  # Not on Windows

        # --- Find Chrome executable for fallback methods ---
        chrome_path = None
        for path in [
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]:
            if os.path.exists(path):
                chrome_path = path
                break

        if not chrome_path:
            try:
                chrome_path = uc.find_chrome_executable()
            except Exception:
                _logger.warning("Chrome executavel nao encontrado em nenhum caminho conhecido")
                return None

        _logger.debug(f"Chrome encontrado em: {chrome_path}")

        # --- Attempt 2: PowerShell file version ---
        try:
            out = subprocess.check_output(
                ["powershell", "-Command",
                 f"(Get-Item '{chrome_path}').VersionInfo.FileVersion"],
                text=True, timeout=10,
            )
            major = int(out.strip().split(".")[0])
            _logger.info(f"Chrome versao detectada via PowerShell: {major}")
            return major
        except Exception as exc:
            _logger.debug(f"PowerShell version detection falhou: {exc}")

        # --- Attempt 3: chrome --version ---
        try:
            out = subprocess.check_output(
                [chrome_path, "--version"], text=True, timeout=10,
            )
            for part in out.strip().split():
                if "." in part:
                    major = int(part.split(".")[0])
                    _logger.info(f"Chrome versao detectada via --version: {major}")
                    return major
        except Exception as exc:
            _logger.debug(f"Chrome --version detection falhou: {exc}")

        _logger.warning("Nenhum metodo de deteccao de versao do Chrome funcionou")
        return None

    @classmethod
    def create_driver(cls, headless: bool = False, proxy: str = None) -> uc.Chrome:
        """Create and return a configured undetected Chrome WebDriver.

        Args:
            headless: Run browser without a visible window.
            proxy: Optional proxy string (protocol://user:pass@host:port).

        Returns:
            A configured undetected_chromedriver.Chrome instance.
        """
        options = uc.ChromeOptions()

        # Randomized window size
        width, height = random.choice(cls._VIEWPORTS)
        width += random.randint(-20, 20)
        height += random.randint(-20, 20)
        options.add_argument(f"--window-size={width},{height}")

        # Basic stability flags
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--ignore-certificate-errors")

        # Headless mode
        if headless:
            options.add_argument("--headless=new")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        # Proxy configuration
        if proxy:
            from browser.proxy_config import ProxyConfig

            proxy_cfg = ProxyConfig.parse(proxy)
            if proxy_cfg.requires_auth and proxy_cfg.scheme.startswith("socks"):
                # SOCKS with auth: Chrome can't handle SOCKS auth natively.
                # Start a local relay that handles auth via PySocks.
                local_port = proxy_cfg.start_local_relay()
                options.add_argument(f"--proxy-server=socks5://127.0.0.1:{local_port}")
            elif proxy_cfg.requires_auth:
                # HTTP/HTTPS with auth: use Chrome extension
                ext_path = proxy_cfg.create_auth_extension()
                options.add_argument(f"--load-extension={ext_path}")
            else:
                # No auth: use --proxy-server flag directly
                options.add_argument(
                    f"--proxy-server={proxy_cfg.scheme}://{proxy_cfg.host}:{proxy_cfg.port}"
                )

        # Create driver - undetected_chromedriver handles anti-detection internally
        # Detect installed Chrome major version to avoid driver/browser mismatch
        version_main = cls._detect_chrome_version()

        if version_main:
            _logger.info(f"Chrome versao detectada: {version_main}")
        else:
            _logger.warning("Nao foi possivel detectar a versao do Chrome — usando deteccao automatica do uc")

        # Lock ensures only one uc.Chrome() runs at a time (patch race fix)
        with cls._creation_lock:
            try:
                driver = uc.Chrome(options=options, version_main=version_main)
            except Exception as exc:
                _logger.error(f"Falha ao criar Chrome driver (version_main={version_main}): {exc}")
                raise

        return driver
