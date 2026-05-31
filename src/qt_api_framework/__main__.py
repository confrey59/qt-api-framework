# src/qt_api_framework/__main__.py
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

def main():
    parser = argparse.ArgumentParser(description="qt-api-framework CLI")
    parser.add_argument("--config", default="config/framework.json", help="Path to framework config")
    parser.add_argument("--plugins", default="config/plugins.json", help="Path to plugins config")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")

    # Load config
    cfg_path = Path(args.config)
    plg_path = Path(args.plugins)
    framework_cfg = {}
    if cfg_path.exists():
        framework_cfg = json.loads(cfg_path.read_text())
        logging.info(f"📖 Loaded framework config from {cfg_path}")
    else:
        logging.warning("⚠️ No framework.json found. Using defaults.")

    # Init Qt
    app = QApplication(sys.argv)
    app.setApplicationName(framework_cfg.get("window_title", "qt-api-framework"))

    # Core Components
    from qt_api_framework.network.api_client import QtNetworkWorker
    from qt_api_framework.core.auth_flow import AuthFlow
    from qt_api_framework.core.plugin_loader import PluginLoader
    from qt_api_framework.core.shell import MainShell

    api_url = framework_cfg.get("api_base_url", "http://127.0.0.1:8000")
    timeout = framework_cfg.get("timeout", 10)
    retries = framework_cfg.get("max_retries", 3)

    worker = QtNetworkWorker(api_url, timeout, retries)
    auth = AuthFlow(worker)
    loader = PluginLoader(config_path=plg_path, api_client=worker)

    shell = MainShell(framework_cfg, worker, auth, loader)
    shell.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()