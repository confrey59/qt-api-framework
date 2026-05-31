# src/qt_api_framework/core/base_plugin.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

class BasePlugin(QObject):
    """
    Contratto base per i plugin del framework.
    Invece di ABC, usa NotImplementedError per garantire il contratto
    senza conflitti di metaclassi con PySide6/Shiboken.
    """
    
    # Segnali Qt per comunicare con Shell/PluginLoader
    status_changed = Signal(str)
    error_occurred = Signal(str)
    request_auth = Signal()

    def __init__(self, plugin_id: str, config: Dict[str, Any], api_client: Optional[Any] = None):
        super().__init__()
        self.plugin_id = plugin_id
        self.config = config
        self.api_client = api_client
        
        # Metadati estratti dalla config
        self.title: str = config.get("title", plugin_id)
        self.icon_path: Optional[str] = config.get("icon")
        self.requires_auth: bool = config.get("requires_auth", False)
        
        self._is_loaded = False
        self._main_window: Optional[QWidget] = None

    def create_window(self) -> QWidget:
        """Fabbrica del QWidget principale. DA IMPLEMENTARE."""
        raise NotImplementedError("Il plugin deve implementare create_window()")

    def on_load(self) -> None:
        """Hook di inizializzazione. DA IMPLEMENTARE."""
        raise NotImplementedError("Il plugin deve implementare on_load()")

    def on_unload(self) -> None:
        """Hook di cleanup thread-safe. DA IMPLEMENTARE."""
        raise NotImplementedError("Il plugin deve implementare on_unload()")

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def mark_loaded(self) -> None:
        """Internal: chiamata da PluginLoader dopo successo init."""
        self._is_loaded = True
        self.status_changed.emit(f"Plugin {self.plugin_id} loaded")

    def get_window(self) -> Optional[QWidget]:
        """Lazy instantiation sicura."""
        if self._main_window is None:
            self._main_window = self.create_window()
            self._main_window.setObjectName(f"plugin_window_{self.plugin_id}")
        return self._main_window