"""
DriverFactory - Creates undetected Chrome WebDriver instances
with anti-detection measures and configurable options.
"""

import random
import undetected_chromedriver as uc


class DriverFactory:
    """Factory for creating configured undetected Chrome WebDriver instances."""

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
            if proxy_cfg.requires_auth:
                ext_path = proxy_cfg.create_auth_extension()
                options.add_argument(f"--load-extension={ext_path}")
            else:
                options.add_argument(f"--proxy-server={proxy_cfg.scheme}://{proxy_cfg.host}:{proxy_cfg.port}")

        # Create driver - undetected_chromedriver handles anti-detection internally
        driver = uc.Chrome(options=options)

        return driver
