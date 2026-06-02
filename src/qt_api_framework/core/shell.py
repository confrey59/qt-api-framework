"""
Main application shell.
Neutral by default. Core components initialize only when a config/profile is loaded.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QStatusBar, QLabel,
    QMenuBar, QMenu, QMessageBox, QDialog, QVBoxLayout,
    QLineEdit, QPushButton, QListWidget, QHBoxLayout
)

from .paths import paths
from .profile_manager import ProfileManager
from .plugin_loader import PluginLoader
from ..network.api_client import QtNetworkWorker
from .auth_flow import AuthFlow

logger = logging.getLogger(__name__)


class ProfileDialog(QDialog):
    """Manual dialog for profile selection or creation."""
    profile_selected = Signal(str)

    def __init__(self, manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Load Profile or Config")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self._refresh_profiles()
        layout.addWidget(self.list_widget)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("New profile name...")
        layout.addWidget(self.name_input)

        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select")
        self.create_btn = QPushButton("Create & Select")
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

        self.select_btn.clicked.connect(self._on_select)
        self.create_btn.clicked.connect(self._on_create)
        self.list_widget.itemDoubleClicked.connect(lambda item: self._on_select(item.text()))

    def _refresh_profiles(self):
        self.list_widget.clear()
        for name in self.manager.list_profiles():
            self.list_widget.addItem(name)

    def _on_select(self):
        current = self.list_widget.currentItem()
        if not current:
            QMessageBox.warning(self, "Selection Required", "Please select an existing profile.")
            return
        self.profile_selected.emit(current.text())
        self.accept()

    def _on_create(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Required", "Enter a profile name.")
            return
        if self.manager.profile_exists(name):
            QMessageBox.warning(self, "Exists", f"Profile '{name}' already exists.")
            return
        
        self.manager.create_profile(name)
        self.profile_selected.emit(name)
        self.accept()


class MainShell(QMainWindow):
    """
    Neutral application window.
    Shows empty UI on launch. Core (network/auth/plugins) initializes only via config/profile.
    """
    def __init__(self, config: Optional[dict] = None):
        super().__init__()
        self.profile_manager = ProfileManager()
        
        self.worker: Optional[QtNetworkWorker] = None
        self.auth: Optional[AuthFlow] = None
        self.loader: Optional[PluginLoader] = None
        self.current_profile_name: Optional[str] = None

        self._setup_ui()
        self._setup_mdi()
        self._setup_status_bar()

        # NEUTRAL: Initialize core only if config is explicitly provided
        if config:
            self._initialize_core(config)

    def _setup_ui(self):
        self.setWindowTitle("qt-api-framework")
        self.resize(1024, 768)

        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu for manual profile/config loading
        tools_menu = menu.addMenu("&Tools")
        load_action = QAction("Load Profile / Config", self)
        load_action.triggered.connect(self._open_profile_dialog)
        tools_menu.addAction(load_action)

        view_menu = menu.addMenu("&View")
        theme_action = QAction("Toggle Theme", self)
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

    def _setup_mdi(self):
        self.mdi = QMdiArea(self)
        self.setCentralWidget(self.mdi)
        self.mdi.setViewMode(QMdiArea.TabbedView)
        self.mdi.setTabsClosable(True)

    def _setup_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.lbl_conn = QLabel("● Offline")
        self.lbl_conn.setStyleSheet("color: #FFC107; font-weight: bold;")
        self.lbl_profile = QLabel("No Profile")
        self.lbl_theme = QLabel("")

        self.status.addPermanentWidget(self.lbl_conn)
        self.status.addPermanentWidget(self.lbl_profile)
        self.status.showMessage("Ready (Neutral Mode)", 3000)

    def _open_profile_dialog(self):
        dialog = ProfileDialog(self.profile_manager, self)
        dialog.profile_selected.connect(self._on_profile_selected)
        dialog.exec()

    def _on_profile_selected(self, profile_name: str):
        self.current_profile_name = profile_name
        self.lbl_profile.setText(f"👤 {profile_name}")
        logger.info(f"Profile selected: {profile_name}")
        config = self.profile_manager.load_profile(profile_name)
        self._initialize_core(config)

    def _initialize_core(self, config: dict):
        """Initialize network, auth, and plugins from provided config."""
        api_url = config.get("api_base_url", "http://127.0.0.1:8000")
        timeout = config.get("timeout", 10)
        retries = config.get("max_retries", 3)

        self.worker = QtNetworkWorker(api_url, timeout, retries)
        
        self.auth = AuthFlow(self.worker)
        self.auth.authenticated.connect(self._on_auth_success)
        self.auth.auth_failed.connect(self._on_auth_failed)
        self.auth.logout_requested.connect(self._on_logout)
        self.worker.connection_status.connect(self._on_conn_status)

        # Plugin loader setup
        if self.current_profile_name:
            profile_path = self.profile_manager._profiles_dir / f"{self.current_profile_name}.json"
            self.loader = PluginLoader(config_path=profile_path, api_client=self.worker)
        else:
            temp_path = paths.user_cache / "temp_config.json"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(config, f)
            self.loader = PluginLoader(config_path=temp_path, api_client=self.worker)

        self.loader.plugin_loaded.connect(self._on_plugin_loaded)
        self.loader.plugin_failed.connect(self._on_plugin_failed)
        self.loader.all_loaded.connect(lambda: self.status.showMessage("All plugins ready", 2000))

        self._apply_theme(config.get("theme", "dark"))
        logger.info("Loading plugins...")
        self.loader.load_all()

        if config.get("auth_enabled", False):
            self._show_auth_gate()

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
            self.auth.login(inp_user.text(), inp_pass.text())
            dlg.close()
        btn.clicked.connect(_do_login)
        dlg.exec()

    def _on_auth_success(self, token: str):
        self.status.showMessage("Authenticated", 3000)
        logger.info("Authentication successful")

    def _on_auth_failed(self, err: str):
        QMessageBox.critical(self, "Auth Error", f"Login failed: {err}")

    def _on_logout(self):
        self.status.showMessage("Logged out", 3000)
        if self.loader: self.loader.unload_all()
        if self.mdi: self.mdi.closeAllSubWindows()

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

    def _on_plugin_loaded(self, pid: str):
        plugin = self.loader.get_plugin(pid)
        if plugin:
            win = plugin.get_window()
            if win:
                self.mdi.addSubWindow(win)
                win.show()
                logger.info(f"Plugin '{pid}' mounted to MDI")

    def _on_plugin_failed(self, pid: str, err: str):
        logger.warning(f"Plugin {pid} failed to load: {err}")
        self.status.showMessage(f"⚠️ Plugin {pid} failed", 4000)

    def _apply_theme(self, theme: str):
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
        else:
            app.setStyle("Fusion")

    def _toggle_theme(self):
        current = self.palette().color(QPalette.Window).name()
        new_theme = "light" if current != "#1e1e1e" else "dark"
        self._apply_theme(new_theme)

    def closeEvent(self, event):
        logger.info("Initiating graceful shutdown...")
        if self.loader:
            self.loader.unload_all()
        if self.worker:
            self.worker.stop()
        event.accept()
        logger.info("Shutdown complete.")