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
                self.error.emit(
                    "Teste de proxy SOCKS nao suportado.\n"
                    "Use o navegador para verificar proxies SOCKS."
                )
                return

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

        except ValueError as exc:
            self.error.emit(f"Formato invalido: {exc}")
        except Exception as exc:
            self.error.emit(str(exc))


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
