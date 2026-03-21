"""
CookieManager - Load, apply, and validate browser cookies
from JSON or Netscape format files.
"""

import json
import logging
from pathlib import Path

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from utils.humanizer import page_load_wait


class CookieManager:
    """Manages browser cookies for session persistence."""

    TWITTER_DOMAIN = ".x.com"
    TWITTER_URL = "https://x.com"
    LOGIN_CHECK_URL = "https://x.com/home"

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_from_json(self, filepath: str) -> list[dict]:
        """
        Load cookies from a JSON file.

        Expected format: a list of dicts, each with at least
        'name' and 'value' keys.  Optional keys: domain, path,
        secure, httpOnly, expiry/expirationDate.
        """
        path = Path(filepath)
        if not path.exists():
            self.logger.error("Cookie file not found: %s", filepath)
            return []

        with open(path, "r", encoding="utf-8") as f:
            raw_cookies = json.load(f)

        cookies = []
        for rc in raw_cookies:
            cookie = {
                "name": rc["name"],
                "value": rc["value"],
                "domain": rc.get("domain", self.TWITTER_DOMAIN),
                "path": rc.get("path", "/"),
                "secure": rc.get("secure", True),
            }
            # Handle different expiry key names
            expiry = rc.get("expiry") or rc.get("expirationDate")
            if expiry:
                cookie["expiry"] = int(expiry)
            if rc.get("httpOnly") is not None:
                cookie["httpOnly"] = rc["httpOnly"]
            cookies.append(cookie)

        self.logger.info("Loaded %d cookies from JSON: %s", len(cookies), filepath)
        return cookies

    def load_from_netscape(self, filepath: str) -> list[dict]:
        """
        Load cookies from a Netscape-format cookies.txt file.

        Each data line has 7 tab-separated fields:
        domain, flag, path, secure, expiry, name, value
        """
        path = Path(filepath)
        if not path.exists():
            self.logger.error("Cookie file not found: %s", filepath)
            return []

        cookies = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    continue
                domain, _flag, c_path, secure, expiry, name, value = parts[:7]
                cookie = {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": c_path,
                    "secure": secure.upper() == "TRUE",
                }
                if expiry and expiry != "0":
                    cookie["expiry"] = int(expiry)
                cookies.append(cookie)

        self.logger.info("Loaded %d cookies from Netscape file: %s", len(cookies), filepath)
        return cookies

    # ------------------------------------------------------------------
    # Applying
    # ------------------------------------------------------------------

    def apply_cookies(self, driver: WebDriver, cookies: list[dict]) -> None:
        """
        Apply a list of cookie dicts to the Selenium driver.

        The driver must first navigate to the cookie domain so that
        the browser accepts them.
        """
        # Navigate to the domain first so cookies can be set
        try:
            driver.get(self.TWITTER_URL)
            page_load_wait()
        except WebDriverException as exc:
            self.logger.warning("Could not navigate to %s: %s", self.TWITTER_URL, exc)

        applied = 0
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
                applied += 1
            except WebDriverException as exc:
                self.logger.debug(
                    "Failed to set cookie '%s': %s", cookie.get("name"), exc
                )

        self.logger.info("Applied %d / %d cookies to driver.", applied, len(cookies))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_cookies(self, driver: WebDriver) -> bool:
        """
        Check whether the currently loaded cookies represent a
        valid logged-in session by navigating to the home timeline
        and looking for signs of authentication.

        Returns True if the session appears valid, False otherwise.
        """
        try:
            driver.get(self.LOGIN_CHECK_URL)
            page_load_wait()

            # If redirected to a login page, cookies are invalid
            current = driver.current_url.lower()
            if "login" in current or "flow" in current or "i/flow" in current:
                self.logger.warning("Cookies invalid - redirected to login page.")
                return False

            # Verify the page title does not indicate a logged-out state
            title = driver.title.lower()
            if "log in" in title or "sign up" in title:
                self.logger.warning("Cookies invalid - login/signup page title detected.")
                return False

            self.logger.info("Cookie validation passed - session appears active.")
            return True

        except WebDriverException as exc:
            self.logger.error("Cookie validation error: %s", exc)
            return False
