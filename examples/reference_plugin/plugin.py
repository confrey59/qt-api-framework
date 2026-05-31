from __future__ import annotations
import logging
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from qt_api_framework.core.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class ReferencePlugin(BasePlugin):
    """
    Plugin di esempio che mostra come:
    - Creare un widget Qt
    - Effettuare chiamate di rete thread-safe
    - Gestire lifecycle e stato
    """
    def create_window(self) -> QWidget:
        self._widget = QWidget()
        self._layout = QVBoxLayout(self._widget)
        
        self._label = QLabel("Plugin di esempio pronto")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._btn = QPushButton("Test API Call")
        
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._log)
        self._layout.addWidget(self._btn)
        
        self._btn.clicked.connect(self._run_test)
        return self._widget

    def on_load(self) -> None:
        self._append_log("✅ Plugin caricato correttamente")
        self._append_log(f"🔗 API Base: {self.api_client.base_url}")
        self._append_log("Clicca 'Test API Call' per inviare una richiesta")

    def on_unload(self) -> None:
        self._append_log("🧹 Plugin scaricato")

    @Slot()
    def _run_test(self) -> None:
        self._append_log("📡 Invio richiesta GET /api/status...")
        self._btn.setEnabled(False)
        
        # Chiamata thread-safe: il worker la esegue in QThread
        # Se serve autenticazione, il token viene iniettato automaticamente
        self.api_client.request_get.emit("/api/status")
        self.api_client.request_finished.connect(self._on_response, type=self.api_client.request_finished.type())

    @Slot(str, object)
    def _on_response(self, method: str, result: object) -> None:
        self._btn.setEnabled(True)
        self.api_client.request_finished.disconnect(self._on_response)
        
        if isinstance(result, str):
            self._append_log(f"❌ Errore rete: {result}")
        else:
            self._append_log(f"✅ Risposta JSON: {result}")
            
    def _append_log(self, msg: str) -> None:
        if hasattr(self, '_log'):
            self._log.append(msg)
