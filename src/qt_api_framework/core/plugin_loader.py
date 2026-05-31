# src/qt_api_framework/core/plugin_loader.py
from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from .base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class PluginLoader(QObject):
    """Gestisce il caricamento dinamico dei plugin."""
    
    plugin_loaded = Signal(str)
    plugin_failed = Signal(str, str)
    all_loaded = Signal()
    unloading = Signal()

    def __init__(self, config_path: Optional[Path] = None, api_client: Optional[Any] = None):
        super().__init__()
        self.config_path = config_path
        self.api_client = api_client
        self._configs: List[Dict[str, Any]] = []
        self.plugins: Dict[str, BasePlugin] = {}

    def load_config(self) -> bool:
        if not self.config_path or not self.config_path.exists():
            logger.warning("No plugin configuration provided or file missing.")
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._configs = data.get("plugins", [])
            logger.info(f"Loaded {len(self._configs)} plugin definitions.")
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to parse plugin config: {e}")
            return False

    def load_all(self) -> None:
        if not self._configs:
            if not self.load_config():
                return
        
        for cfg in self._configs:
            self._load_single(cfg)
        self.all_loaded.emit()

    def _load_single(self, cfg: Dict[str, Any]) -> Optional[BasePlugin]:
        pid = cfg.get("id")
        mod_path = cfg.get("module")
        cls_name = cfg.get("class")
        
        if not all([pid, mod_path, cls_name]):
            logger.error(f"Invalid plugin config: {cfg}")
            return None

        try:
            module = importlib.import_module(mod_path)
            plugin_cls = getattr(module, cls_name)
            
            if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, BasePlugin):
                raise TypeError(f"{cls_name} does not inherit from BasePlugin")
            
            instance = plugin_cls(plugin_id=pid, config=cfg, api_client=self.api_client)
            instance.on_load()
            instance.mark_loaded()
            
            self.plugins[pid] = instance
            self.plugin_loaded.emit(pid)
            logger.info(f"Successfully loaded plugin: {pid}")
            return instance
            
        except Exception as e:
            logger.exception(f"Failed to load plugin '{pid}': {e}")
            self.plugin_failed.emit(pid, str(e))
            return None

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self.plugins.get(plugin_id)

    def unload_all(self) -> None:
        """Chiusura ordinata e thread-safe."""
        self.unloading.emit()
        for pid, plugin in list(self.plugins.items()):
            try:
                logger.debug(f"Unloading plugin: {pid}")
                plugin.on_unload()
                try:
                    plugin.disconnect()
                except Exception:
                    pass
                plugin.deleteLater()
            except Exception as e:
                logger.warning(f"Error during unload of {pid}: {e}")
        
        self.plugins.clear()
        logger.info("All plugins unloaded.")