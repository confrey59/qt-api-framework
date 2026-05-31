# src/qt_api_framework/core/auth_flow.py
from __future__ import annotations

import logging
from typing import Any, Optional
from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)

class AuthFlow(QObject):
    """State machine login/sessione. Comunica via segnali Qt."""
    authenticated = Signal(str)
    auth_failed = Signal(str)
    session_expired = Signal()
    logout_requested = Signal()

    def __init__(self, network_worker: QtNetworkWorker):
        super().__init__()
        self._worker = network_worker
        self._token: Optional[str] = None

    @Slot(str, str)
    def login(self, username: str, password: str) -> None:
        """Avvia login. Emette segnale → elaborato nel thread di rete."""
        self._worker.request_finished.connect(self._on_login_response)
        self._worker.request_post.emit("/auth/login", {"json": {"username": username, "password": password}})

    @Slot(str, object)
    def _on_login_response(self, method: str, result: Any) -> None:
        self._worker.request_finished.disconnect(self._on_login_response)
        if isinstance(result, str):
            self.auth_failed.emit(f"Login failed: {result}")
            return
        token = result.get("token")
        if token:
            self._token = token
            self._worker.set_token(token)
            self.authenticated.emit(token)
            logger.info("Authentication successful")
        else:
            self.auth_failed.emit("Invalid response: no token")

    def logout(self) -> None:
        self._worker.clear_token()
        self._token = None
        self.logout_requested.emit()

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None