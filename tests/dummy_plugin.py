from qt_api_framework.core.base_plugin import BasePlugin
from PySide6.QtWidgets import QLabel

class DummyPlugin(BasePlugin):
    def create_window(self):
        return QLabel("🔌 Dummy Plugin Loaded")

    def on_load(self):
        print(f"[{self.plugin_id}] Initializing resources...")
        # Simula sottoscrizione WS o avvio QThread

    def on_unload(self):
        print(f"[{self.plugin_id}] Cleaning up resources...")
        # Stop thread, chiudi socket