"""
Test suite for qt-api-framework v2.0 (GUI-first, profiles, deferred init).
Validates cross-platform paths, profile manager, and headless shell initialization.
"""
import sys
import os
import logging
from pathlib import Path
from PySide6.QtCore import QTimer, QCoreApplication
from PySide6.QtWidgets import QApplication

# Ensure project source is importable
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from qt_api_framework.core.paths import paths
from qt_api_framework.core.profile_manager import ProfileManager
from qt_api_framework.core.shell import MainShell

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

def run_v2_tests():
    # Force headless rendering
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication(sys.argv)

    logger.info(" Testing cross-platform paths...")
    paths.ensure_dirs_exist()
    assert paths.user_config.exists()
    assert paths.profiles_dir.exists()
    logger.info("✅ Paths verified")

    logger.info(" Testing ProfileManager...")
    pm = ProfileManager()
    test_profile = "test_v2_profile"
    
    if pm.profile_exists(test_profile):
        pm.delete_profile(test_profile)

    pm.create_profile(test_profile, {"api_base_url": "http://test:8000", "theme": "light"})
    assert pm.profile_exists(test_profile)
    
    loaded = pm.load_profile(test_profile)
    assert loaded["theme"] == "light"
    assert loaded["api_base_url"] == "http://test:8000"
    logger.info("✅ ProfileManager verified")

    logger.info("️ Testing MainShell deferred init (headless)...")
    
    # Subclass to bypass blocking ProfileDialog in test environment
    class TestShell(MainShell):
        def _show_profile_dialog(self):
            self._on_profile_selected(test_profile)

    shell = TestShell()
    
    # Allow Qt event loop to process deferred initialization
    QTimer.singleShot(600, lambda: verify_and_cleanup(shell, pm, test_profile))
    
    sys.exit(app.exec())

def verify_and_cleanup(shell, pm, profile_name):
    logger.info("📊 Verifying deferred core initialization...")
    assert shell.current_profile_name == profile_name
    assert shell.worker is not None
    assert shell.auth is not None
    assert shell.loader is not None
    logger.info("✅ Core components initialized correctly")
    
    logger.info("🧹 Cleaning up test artifacts...")
    shell.close()
    QTimer.singleShot(200, lambda: final_exit(pm, profile_name))

def final_exit(pm, profile_name):
    if pm.profile_exists(profile_name):
        pm.delete_profile(profile_name)
    print("\n🎉 PASSO V2: GUI-FIRST & PROFILES SUPERATI")
    QCoreApplication.exit(0)

if __name__ == "__main__":
    run_v2_tests()