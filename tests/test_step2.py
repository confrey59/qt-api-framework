# tests/test_step2.py
import sys
import json
import logging
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QTimer

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qt_api_framework.network.api_client import QtNetworkWorker
from qt_api_framework.core.auth_flow import AuthFlow
from tests.mock_server import MockAPIServer

# 🔧 FIX: Crea logger dopo basicConfig
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

def run_test():
    app = QCoreApplication(sys.argv)
    srv = MockAPIServer()
    srv.start()
    
    worker = QtNetworkWorker(srv.http_url, timeout=5, max_retries=2)
    auth = AuthFlow(worker)
    
    results = {"auth_ok": False, "auth_err": None, "ws_ok": False, "finished": False}
    
    def on_auth_ok(token):
        logger.info(f"✅ Login OK (token: {token[:10]}...)")
        results["auth_ok"] = True
        # Connetti WS dopo auth
        worker.connect_ws.emit(srv.ws_url)
        
    def on_auth_err(err):
        results["auth_err"] = err
        logger.error(f"❌ Login fallito: {err}")
        finish_test()
        
    def on_ws_status(status):
        logger.info(f"🌐 WS Status: {status}")
        if status == "connected":
            results["ws_ok"] = True
            logger.info("✅ WS connesso")
            # Invia ping e termina dopo breve delay
            QTimer.singleShot(200, send_ws_ping)
            
    def send_ws_ping():
        try:
            worker.send_ws.emit(json.dumps({"ping": True}))
            logger.info("✅ WS Ping inviato")
        except Exception as e:
            logger.error(f"❌ WS errore: {e}")
        # Termina test dopo invio
        QTimer.singleShot(100, finish_test)
        
    def finish_test():
        if results["finished"]:
            return  # Evita doppie esecuzioni
        results["finished"] = True
        
        success = results["auth_ok"] and results["ws_ok"]
        if success:
            print("\n🎉 PASSO 2: TEST DI RETE & AUTH SUPERATI")
        else:
            missing = []
            if not results["auth_ok"]: missing.append("auth")
            if not results["ws_ok"]: missing.append("ws")
            print(f"\n💥 PASSO 2 FALLITO: mancanti={missing}, err={results['auth_err']}")
            
        # Cleanup ordinato
        auth.logout()
        worker.stop()
        srv.stop()
        app.quit()

    # Collegamenti segnali
    auth.authenticated.connect(on_auth_ok)
    auth.auth_failed.connect(on_auth_err)
    worker.connection_status.connect(on_ws_status)
    
    # Timeout di sicurezza (7s)
    QTimer.singleShot(7000, finish_test)
    
    # Avvia flusso
    logger.info(f"🚀 Test start → HTTP: {srv.http_url} | WS: {srv.ws_url}")
    auth.login("testuser", "secret")
    
    # Event loop headless
    sys.exit(app.exec())

if __name__ == "__main__":
    run_test()