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
    # Local SOCKS relay for authenticated SOCKS proxies
    # ------------------------------------------------------------------

    def start_local_relay(self) -> int:
        """Start a local TCP relay that forwards traffic through the
        authenticated SOCKS proxy.  Chrome connects to 127.0.0.1:<port>
        without auth; the relay handles SOCKS auth via PySocks.

        Returns the local port number.
        """
        import socket
        import threading
        import socks

        proxy_type = socks.SOCKS5 if "5" in self.scheme else socks.SOCKS4
        log = logging.getLogger(__name__)

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        local_port = server.getsockname()[1]
        server.listen(32)
        server.settimeout(1.0)

        log.info(f"SOCKS relay listening on 127.0.0.1:{local_port}")

        def _forward(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dst.close()
                except Exception:
                    pass

        def _handle(client):
            # Read SOCKS5 handshake from Chrome
            try:
                data = client.recv(512)
                if not data or data[0] != 0x05:
                    client.close()
                    return

                # Reply: no auth required locally
                client.sendall(b"\x05\x00")

                # Read connect request
                req = client.recv(512)
                if not req or req[1] != 0x01:
                    client.close()
                    return

                # Parse destination
                atyp = req[3]
                if atyp == 0x01:  # IPv4
                    dst_host = socket.inet_ntoa(req[4:8])
                    dst_port = int.from_bytes(req[8:10], "big")
                elif atyp == 0x03:  # Domain
                    domain_len = req[4]
                    dst_host = req[5:5 + domain_len].decode()
                    dst_port = int.from_bytes(req[5 + domain_len:7 + domain_len], "big")
                elif atyp == 0x04:  # IPv6
                    dst_host = socket.inet_ntop(socket.AF_INET6, req[4:20])
                    dst_port = int.from_bytes(req[20:22], "big")
                else:
                    client.close()
                    return

                # Connect to destination via remote SOCKS proxy
                remote = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
                remote.set_proxy(
                    proxy_type,
                    self.host,
                    self.port,
                    username=self.username,
                    password=self.password,
                )
                remote.settimeout(15)
                remote.connect((dst_host, dst_port))

                # Send success reply
                reply = b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + (0).to_bytes(2, "big")
                client.sendall(reply)

                # Forward bidirectionally
                t1 = threading.Thread(target=_forward, args=(client, remote), daemon=True)
                t2 = threading.Thread(target=_forward, args=(remote, client), daemon=True)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

            except Exception as exc:
                log.debug(f"Relay connection error: {exc}")
                try:
                    client.close()
                except Exception:
                    pass

        self._relay_server = server
        self._relay_running = True

        def _accept_loop():
            while self._relay_running:
                try:
                    client, _ = server.accept()
                    threading.Thread(target=_handle, args=(client,), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception:
                    if self._relay_running:
                        continue
                    break

        threading.Thread(target=_accept_loop, daemon=True).start()
        return local_port

    def stop_relay(self):
        """Stop the local SOCKS relay server."""
        self._relay_running = False
        if hasattr(self, "_relay_server"):
            try:
                self._relay_server.close()
            except Exception:
                pass

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
