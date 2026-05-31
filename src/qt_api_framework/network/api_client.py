# src/qt_api_framework/network/api_client.py
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx
from websockets.sync.client import connect as ws_connect
from PySide6.QtCore import QObject, QThread, Signal, Slot, QMutex, QMutexLocker

logger = logging.getLogger(__name__)

class APIClient:
    """Core sincrono HTTP/WS. Thread-safe tramite QMutex."""
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._mutex = QMutex()
        self._token: Optional[str] = None
        self._headers = {"Content-Type": "application/json"}
        self._http = httpx.Client(base_url=self.base_url, timeout=self.timeout, headers=self._headers)
        self._ws = None

    def set_token(self, token: str) -> None:
        with QMutexLocker(self._mutex):
            self._token = token
            self._headers["Authorization"] = f"Bearer {token}"

    def clear_token(self) -> None:
        with QMutexLocker(self._mutex):
            self._token = None
            self._headers.pop("Authorization", None)

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = getattr(self._http, method.lower())(url, **kwargs)
                if 500 <= resp.status_code < 600 and attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return resp
            except Exception as e:
                last_err = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        raise last_err or RuntimeError(f"Request to {path} failed")

    def get(self, path: str, **kwargs) -> httpx.Response: return self._request("GET", path, **kwargs)
    def post(self, path: str, **kwargs) -> httpx.Response: return self._request("POST", path, **kwargs)

    def connect_ws(self, url: str) -> None:
        self._ws = ws_connect(url, additional_headers=self._headers)

    def send_ws(self, msg: str) -> None:
        if self._ws: self._ws.send(msg)
        else: raise ConnectionError("WebSocket not connected")

    def close(self) -> None:
        try:
            if self._ws: self._ws.close()
        except: pass
        self._http.close()
        logger.info("APIClient closed.")


class QtNetworkWorker(QObject):
    """Worker Qt per esecuzione thread-safe di APIClient."""
    # 🔹 Segnali di COMANDO (emessi dal main thread)
    request_post = Signal(str, object)  # path, kwargs
    request_get = Signal(str, object)
    connect_ws = Signal(str)            # url
    send_ws = Signal(str)               # message

    # 🔹 Segnali di RISULTATO (emessi dal thread di rete)
    request_finished = Signal(str, object)  # method, result_dict | error_str
    connection_status = Signal(str)
    ws_message = Signal(str)

    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        super().__init__()
        self.client = APIClient(base_url, timeout, max_retries)
        self._thread = QThread(self)
        self.moveToThread(self._thread)
        self._thread.start()

        # Routing comandi → slot (Qt gestisce automaticamente la coda cross-thread)
        self.request_post.connect(self._on_post)
        self.request_get.connect(self._on_get)
        self.connect_ws.connect(self._on_connect_ws)
        self.send_ws.connect(self._on_send_ws)

    @Slot(str, object)
    def _on_post(self, path: str, kwargs: object):
        try:
            resp = self.client.post(path, **kwargs)
            self.request_finished.emit("POST", resp.json())
        except Exception as e:
            self.request_finished.emit("POST", str(e))

    @Slot(str, object)
    def _on_get(self, path: str, kwargs: object):
        try:
            resp = self.client.get(path, **kwargs)
            self.request_finished.emit("GET", resp.json())
        except Exception as e:
            self.request_finished.emit("GET", str(e))

    @Slot(str)
    def _on_connect_ws(self, url: str):
        try:
            self.client.connect_ws(url)
            self.connection_status.emit("connected")
        except Exception as e:
            self.connection_status.emit(f"error: {e}")

    @Slot(str)
    def _on_send_ws(self, msg: str):
        try:
            self.client.send_ws(msg)
        except Exception as e:
            logger.error(f"WS send error: {e}")

    # Metodi wrapper per comodità esterna
    def set_token(self, token: str): self.client.set_token(token)
    def clear_token(self): self.client.clear_token()

    def stop(self) -> None:
        """Chiusura ordinata thread-safe.
        🔧 FIX: Non blocca il main thread durante app.exec()"""
        self.client.close()
        if self._thread.isRunning():
            self._thread.quit()
            # 🔧 wait() rimosso qui. Il thread si chiuderà naturalmente
            # o verrà gestito asincronamente dal framework/app.quit()
        logger.info("NetworkWorker stop requested.")