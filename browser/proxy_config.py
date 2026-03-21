"""
ProxyConfig - Parse proxy strings and configure Selenium
to route traffic through a proxy server.
"""

import os
import re
import tempfile
import zipfile
import logging
from dataclasses import dataclass


@dataclass
class ProxyConfig:
    """Parsed proxy configuration."""

    scheme: str
    host: str
    port: int
    username: str = None
    password: str = None

    @property
    def requires_auth(self) -> bool:
        return bool(self.username and self.password)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    _PROXY_RE = re.compile(
        r"^(?P<scheme>https?|socks[45]?)://"
        r"(?:(?P<user>[^:@]+):(?P<pass>[^@]+)@)?"
        r"(?P<host>[^:]+):(?P<port>\d+)$"
    )

    @classmethod
    def parse(cls, proxy_string: str, logger: logging.Logger = None) -> "ProxyConfig":
        """
        Parse a proxy string of the form:
            protocol://user:pass@host:port
            protocol://host:port

        Returns a ProxyConfig instance.
        Raises ValueError if the string cannot be parsed.
        """
        log = logger or logging.getLogger(__name__)

        match = cls._PROXY_RE.match(proxy_string.strip())
        if not match:
            raise ValueError(f"Invalid proxy string: {proxy_string}")

        cfg = cls(
            scheme=match.group("scheme"),
            host=match.group("host"),
            port=int(match.group("port")),
            username=match.group("user"),
            password=match.group("pass"),
        )
        log.debug("Parsed proxy: %s://%s:%d (auth=%s)", cfg.scheme, cfg.host, cfg.port, cfg.requires_auth)
        return cfg

    # ------------------------------------------------------------------
    # Chrome extension for authenticated proxies
    # ------------------------------------------------------------------

    def create_auth_extension(self) -> str:
        """
        Build a temporary Chrome extension that injects proxy
        authentication credentials.  Returns the path to the
        unpacked extension directory.

        This is necessary because Chrome does not support
        user:pass@host proxy strings natively.
        """
        if not self.requires_auth:
            raise RuntimeError("create_auth_extension called but proxy has no credentials")

        manifest = """{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Proxy Auth Helper",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version": "22.0.0"
}"""

        background = f"""
var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "{self.scheme}",
            host: "{self.host}",
            port: {self.port}
        }},
        bypassList: ["localhost"]
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function(){{}});

function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{self.username}",
            password: "{self.password}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""

        # Write extension to a temp directory
        ext_dir = tempfile.mkdtemp(prefix="proxy_auth_ext_")
        manifest_path = os.path.join(ext_dir, "manifest.json")
        background_path = os.path.join(ext_dir, "background.js")

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest)
        with open(background_path, "w", encoding="utf-8") as f:
            f.write(background)

        return ext_dir

    # ------------------------------------------------------------------
    # Selenium wire dict (useful if switching to seleniumwire later)
    # ------------------------------------------------------------------

    def to_selenium_wire_options(self) -> dict:
        """Return a dict suitable for seleniumwire proxy options."""
        proxy_url = f"{self.scheme}://"
        if self.requires_auth:
            proxy_url += f"{self.username}:{self.password}@"
        proxy_url += f"{self.host}:{self.port}"

        return {
            "proxy": {
                "http": proxy_url,
                "https": proxy_url,
                "no_proxy": "localhost,127.0.0.1",
            }
        }
