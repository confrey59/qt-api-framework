# tests/test_step3.py
import sys
import logging
from pathlib import Path
from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path: 
    sys.path.insert(0, str(PROJECT_ROOT))

from qt_api_framework.network.api_client import QtNetworkWorker
from qt_api_framework.core.auth_flow import AuthFlow
from qt_api_framework.core.plugin_loader import PluginLoader
from qt_api_framework.core.shell import MainShell
from tests.mock_server import MockAPIServer

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

def test_shell_bootstrap():
    app = QApplication(sys.argv)
    srv = MockAPIServer()
    srv.start()

    cfg = {
        "api_base_url": srv.http_url, "timeout": 5, "max_retries": 2,
        "auth_enabled": False, 
        "theme": "light", "mdi_mode": "tabs", "window_title": "TestShell"
    }

    worker = QtNetworkWorker(cfg["api_base_url"], cfg["timeout"], cfg["max_retries"])
    auth = AuthFlow(worker)
    loader = PluginLoader(config_path=Path("tests/plugins_test.json"), api_client=worker)

    # 🔧 FIX: Collega i segnali PRIMA di istanziare MainShell.
    # MainShell.__init__ avvia il caricamento in modo sincrono, quindi
    # i segnali devono essere già pronti per essere catturati.
    loaded_pids = []
    loader.plugin_loaded.connect(loaded_pids.append)
    
    # Istanziazione: triggera automaticamente _load_plugins() -> loader.load_all()
    shell = MainShell(cfg, worker, auth, loader)

    def verify_and_exit():
        logger.info("📊 Verifying results...")
        # Verifica doppia: stato interno del loader + segnali catturati
        success = len(loader.plugins) > 0 and len(loaded_pids) > 0
        status = "🎉 PASSO 3: SHELL & BOOTSTRAP SUPERATI" if success else "💥 PASSO 3 FALLITO"
        print(f"\n{status} (Plugins loaded: {len(loader.plugins)}, Signals caught: {len(loaded_pids)})")

        logger.info("🧹 Cleaning up...")
        srv.stop()
        worker.stop()
        QCoreApplication.exit(0 if success else 1)

    # Attesa breve per garantire che eventuali operazioni asincrone di mount MDI siano processate
    QTimer.singleShot(300, verify_and_exit)

    logger.info("🚀 Starting headless bootstrap test...")
    sys.exit(app.exec())

if __name__ == "__main__":
    test_shell_bootstrap()