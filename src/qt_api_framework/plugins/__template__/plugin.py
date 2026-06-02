from __future__ import annotations

import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from qt_api_framework.core.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class TemplatePlugin(BasePlugin):
    """
    Minimal implementation of BasePlugin.
    Use this as a starting point for custom domain plugins.
    """

    def create_window(self) -> QWidget:
        """Creates the plugin's main UI widget."""
        self._widget = QWidget()
        layout = QVBoxLayout(self._widget)

        layout.addWidget(QLabel(f"Plugin ID: {self.plugin_id}"))
        layout.addWidget(QLabel("Status: Ready"))
        
        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setPlaceholderText("Plugin logs will appear here...")
        layout.addWidget(self._log_area)

        return self._widget

    def on_load(self) -> None:
        """Called after successful registration and before window mounting."""
        logger.info(f"[{self.plugin_id}] Plugin loaded.")
        self._log(f"✅ Initialized")
        
        # Example of thread-safe network call:
        # self.api_client.request_get.emit("/api/health")
        # self.api_client.request_finished.connect(self._handle_response)

    def on_unload(self) -> None:
        """Called during framework shutdown or plugin removal."""
        logger.info(f"[{self.plugin_id}] Plugin unloaded.")
        self._log(" Unloaded")

    def _log(self, message: str) -> None:
        """Helper to append messages to the UI log area."""
        if hasattr(self, '_log_area'):
            self._log_area.append(message)
