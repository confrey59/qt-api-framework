# src/qt_api_framework/core/shell.py
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QStatusBar, QLabel,
    QMenuBar, QMenu, QMessageBox, QDialog, QVBoxLayout, 
    QLineEdit, QPushButton
)

from .plugin_loader import PluginLoader

logger = logging.getLogger(__name__)

class MainShell(QMainWindow):
    """
    Shell principale del framework.
    Gestisce UI, MDI, autenticazione, caricamento plugin e shutdown.
    """
    def __init__(self, config: dict, api_worker: Any, auth_flow: Any, plugin_loader: PluginLoader):
        super().__init__()
        self.config = config
        self.api_worker = api_worker
        self.auth_flow = auth_flow
        self.loader = plugin_loader

        self._setup_ui()
        self._setup_mdi()
        self._setup_status_bar()
        self._connect_signals()
        self._apply_theme()

        # Auth gate o caricamento diretto
        if self.config.get("auth_enabled", False):
            self._show_auth_gate()
        else:
            self._load_plugins()

    def _setup_ui(self):
        self.setWindowTitle(self.config.get("window_title", "qt-api-framework"))
        self.resize(1024, 768)

        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_mdi(self):
        self.mdi = QMdiArea(self)
        self.setCentralWidget(self.mdi)

        mode = self.config.get("mdi_mode", "tabs").lower()
        if mode == "tabs":
            self.mdi.setViewMode(QMdiArea.TabbedView)
            self.mdi.setTabsClosable(True)
        else:
            self.mdi.setViewMode(QMdiArea.SubWindowView)

    def _setup_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.lbl_conn = QLabel("● Offline")
        self.lbl_conn.setStyleSheet("color: #FFC107; font-weight: bold;")
        self.lbl_user = QLabel("👤 Guest")
        self.lbl_theme = QLabel("🌓")

        self.status.addPermanentWidget(self.lbl_conn)
        self.status.addPermanentWidget(self.lbl_user)
        self.status.showMessage("✅ Framework initialized", 3000)

    def _connect_signals(self):
        self.auth_flow.authenticated.connect(self._on_auth_success)
        self.auth_flow.auth_failed.connect(self._on_auth_failed)
        self.auth_flow.logout_requested.connect(self._on_logout)
        self.api_worker.connection_status.connect(self._on_conn_status)
        self.loader.plugin_loaded.connect(self._on_plugin_loaded)
        self.loader.plugin_failed.connect(self._on_plugin_failed)
        self.loader.all_loaded.connect(lambda: self.status.showMessage("✅ All plugins ready", 2000))

    def _apply_theme(self):
        theme = self.config.get("theme", "system")
        app = QApplication.instance()
        if not app: return

        if theme == "dark":
            app.setStyle("Fusion")
            pal = QPalette()
            pal.setColor(QPalette.Window, QColor(30, 30, 30))
            pal.setColor(QPalette.WindowText, Qt.white)
            pal.setColor(QPalette.Base, QColor(20, 20, 20))
            pal.setColor(QPalette.Text, Qt.white)
            pal.setColor(QPalette.Button, QColor(40, 40, 40))
            pal.setColor(QPalette.ButtonText, Qt.white)
            pal.setColor(QPalette.Highlight, QColor(42, 130, 218))
            pal.setColor(QPalette.HighlightedText, Qt.white)
            app.setPalette(pal)
        elif theme == "light":
            app.setStyle("Fusion")

    def _show_auth_gate(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Authentication Required")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Username:"))
        inp_user = QLineEdit(dlg)
        lay.addWidget(inp_user)
        lay.addWidget(QLabel("Password:"))
        inp_pass = QLineEdit(dlg)
        inp_pass.setEchoMode(QLineEdit.Password)
        lay.addWidget(inp_pass)
        btn = QPushButton("Login")
        lay.addWidget(btn)

        def _do_login():
            self.auth_flow.login(inp_user.text(), inp_pass.text())
            dlg.close()
        btn.clicked.connect(_do_login)
        dlg.exec()

    def _on_auth_success(self, token: str):
        self.lbl_user.setText("👤 Authenticated")
        self._load_plugins()

    def _on_auth_failed(self, err: str):
        QMessageBox.critical(self, "Auth Error", f"Login failed: {err}")

    def _on_logout(self):
        self.lbl_user.setText("👤 Guest")
        self.loader.unload_all()
        self.mdi.closeAllSubWindows()

    def _on_conn_status(self, status: str):
        if "connected" in status.lower():
            self.lbl_conn.setText("● Online")
            self.lbl_conn.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif "error" in status.lower():
            self.lbl_conn.setText("● Error")
            self.lbl_conn.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.lbl_conn.setText("● Offline")
            self.lbl_conn.setStyleSheet("color: #FFC107; font-weight: bold;")

    def _load_plugins(self):
        logger.info("Loading plugins via configuration...")
        self.loader.load_all()

    def _on_plugin_loaded(self, pid: str):
        plugin = self.loader.get_plugin(pid)
        if plugin:
            win = plugin.get_window()
            if win:
                self.mdi.addSubWindow(win)
                win.show()
                logger.info(f"Plugin window '{pid}' mounted to MDI")

    def _on_plugin_failed(self, pid: str, err: str):
        logger.warning(f"Plugin {pid} failed to load: {err}")
        self.status.showMessage(f"⚠️ Plugin {pid} failed", 4000)

    def closeEvent(self, event):
        logger.info("🛑 Initiating graceful shutdown...")
        self.loader.unload_all()
        self.api_worker.stop()
        # 🔧 FIX: Quit esplicito per garantire uscita dal loop headless
        QApplication.instance().quit()
        event.accept()
        logger.info("✅ Shutdown complete.")