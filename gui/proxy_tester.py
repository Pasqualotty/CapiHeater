"""
Proxy test helper — reusable button + label for testing proxy connections.
"""

import json
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from gui.theme import COLOR_ERROR, COLOR_SUCCESS, FG_MUTED


class _ProxyTestWorker(QObject):
    """Background worker that tests a proxy connection via httpbin.org/ip."""

    finished = Signal(str)  # emits IP address on success
    error = Signal(str)     # emits error message on failure

    def test(self, proxy_string: str) -> None:
        """Spawn a thread to test the proxy. Results come via signals."""
        threading.Thread(target=self._do_test, args=(proxy_string,), daemon=True).start()

    def _do_test(self, proxy_string: str) -> None:
        try:
            from browser.proxy_config import ProxyConfig
            cfg = ProxyConfig.parse(proxy_string)

            if cfg.scheme.startswith("socks"):
                self._test_socks(cfg)
            else:
                self._test_http(cfg)

        except ValueError as exc:
            self.error.emit(f"Formato invalido: {exc}")
        except Exception as exc:
            self.error.emit(str(exc))

    def _test_http(self, cfg) -> None:
        """Test HTTP/HTTPS proxy via urllib."""
        proxy_url = f"{cfg.scheme}://"
        if cfg.requires_auth:
            proxy_url += f"{cfg.username}:{cfg.password}@"
        proxy_url += f"{cfg.host}:{cfg.port}"

        handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url,
        })
        opener = urllib.request.build_opener(handler)
        response = opener.open("https://httpbin.org/ip", timeout=10)
        data = json.loads(response.read().decode())
        ip = data.get("origin", "IP desconhecido")
        self.finished.emit(ip)

    def _test_socks(self, cfg) -> None:
        """Test SOCKS proxy via PySocks."""
        import socket
        import socks

        proxy_type = socks.SOCKS5 if "5" in cfg.scheme else socks.SOCKS4

        s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
        s.set_proxy(
            proxy_type,
            cfg.host,
            int(cfg.port),
            username=cfg.username if cfg.requires_auth else None,
            password=cfg.password if cfg.requires_auth else None,
        )
        s.settimeout(10)

        try:
            # Connect to httpbin via SOCKS and send HTTP request
            s.connect(("httpbin.org", 80))
            request = (
                "GET /ip HTTP/1.1\r\n"
                "Host: httpbin.org\r\n"
                "Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())

            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk

            body = response.decode().split("\r\n\r\n", 1)[-1]
            data = json.loads(body)
            ip = data.get("origin", "IP desconhecido")
            self.finished.emit(ip)
        finally:
            s.close()


def create_proxy_test_row(proxy_line_edit: QLineEdit) -> QWidget:
    """Create a widget with a 'Testar Proxy' button and result label.

    Parameters
    ----------
    proxy_line_edit : QLineEdit
        The proxy input field to read the proxy string from.

    Returns
    -------
    QWidget
        A widget containing the test button and result label, ready to be
        added to a layout.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    btn = QPushButton("Testar Proxy")
    btn.setObjectName("accent")
    btn.setFixedWidth(110)
    layout.addWidget(btn)

    result_lbl = QLabel("")
    result_lbl.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
    result_lbl.setWordWrap(True)
    layout.addWidget(result_lbl, 1)

    # Keep worker alive as attribute of container to prevent GC
    container._proxy_worker = None

    def on_test():
        proxy = proxy_line_edit.text().strip()
        if not proxy:
            result_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 9pt;")
            result_lbl.setText("Preencha o proxy primeiro.")
            return

        btn.setEnabled(False)
        btn.setText("Testando...")
        result_lbl.setStyleSheet(f"color: {FG_MUTED}; font-size: 9pt;")
        result_lbl.setText("Conectando...")

        worker = _ProxyTestWorker()
        container._proxy_worker = worker

        def on_success(ip: str):
            btn.setEnabled(True)
            btn.setText("Testar Proxy")
            result_lbl.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 9pt;")
            result_lbl.setText(f"OK — IP: {ip}")

        def on_error(msg: str):
            btn.setEnabled(True)
            btn.setText("Testar Proxy")
            result_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 9pt;")
            result_lbl.setText(f"Erro: {msg}")

        worker.finished.connect(on_success)
        worker.error.connect(on_error)
        worker.test(proxy)

    btn.clicked.connect(on_test)

    return container
