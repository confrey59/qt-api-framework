"""
Entry point for qt-api-framework.
Neutral launch: empty shell by default. Config injection is optional.
"""
from __future__ import annotations

import argparse
import json
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication

from qt_api_framework.core.paths import paths
from qt_api_framework.core.shell import MainShell

def main() -> int:
    parser = argparse.ArgumentParser(description="qt-api-framework CLI")
    parser.add_argument("--config", default=None, help="Path to JSON config file (initializes core immediately)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
    logger = logging.getLogger(__name__)

    paths.ensure_dirs_exist()

    app = QApplication(sys.argv)
    app.setApplicationName("qt-api-framework")
    app.setOrganizationName("confrey59")
    # Qt6 enables HighDPI automatically. Removed deprecated setAttribute calls.

    config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"Loaded config from {config_path}")
        else:
            logger.error(f"Config file not found: {config_path}")
            return 1

    # Launch neutral shell. Core initializes only if config is provided.
    shell = MainShell(config=config)
    shell.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())