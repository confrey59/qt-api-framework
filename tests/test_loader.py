# tests/test_loader.py
import sys
import logging
from pathlib import Path

# 🔧 Risolve sys.path per importlib
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 🔧 FIX: QApplication è OBBLIGATORIO per QWidget
from PySide6.QtWidgets import QApplication
from qt_api_framework.core.plugin_loader import PluginLoader

# Log pulito (niente timestamp/path di Python, solo messaggio)
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

def test_plugin_loader():
    app = QApplication(sys.argv)  # ✅ Corretto per GUI
    
    config_path = Path(__file__).parent / "plugins_test.json"
    loader = PluginLoader(config_path=config_path, api_client=None)
    
    events = {"loaded": [], "failed": []}
    loader.plugin_loaded.connect(lambda pid: events["loaded"].append(pid))
    loader.plugin_failed.connect(lambda pid, err: events["failed"].append((pid, err)))
    
    logger.info("🚀 Avvio caricamento plugin...")
    loader.load_all()
    
    passed = True
    
    if "test_dummy" not in loader.plugins:
        logger.error("❌ Plugin valido non caricato")
        passed = False
    else:
        plugin = loader.get_plugin("test_dummy")
        assert plugin.is_loaded, "Stato is_loaded non impostato"
        assert plugin.get_window() is not None, "Window non istanziata"
        logger.info("✅ test_dummy caricato correttamente")
        
    if not any(pid == "invalid_plugin" for pid, _ in events["failed"]):
        logger.error("❌ Plugin invalido non ha triggerato plugin_failed")
        passed = False
    else:
        logger.info("✅ Errore plugin invalido gestito correttamente")
        
    logger.info("🧪 Test unload_all()...")
    loader.unload_all()
    
    if loader.plugins:
        logger.error("❌ plugins dict non svuotato dopo unload")
        passed = False
    else:
        logger.info("✅ Cleanup completato, dict plugins vuoto")
        
    print("\n" + "="*50)
    if passed:
        print("🎉 PASSO 1: TUTTI I TEST SUPERATI")
    else:
        print("💥 PASSO 1: TEST FALLITI (vedi log)")
    print("="*50)
    
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    test_plugin_loader()