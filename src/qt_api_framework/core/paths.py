"""
Cross-platform path management using platformdirs.
Abstracts OS-specific directories (Linux, Windows, macOS).
"""
from __future__ import annotations

from pathlib import Path
from platformdirs import PlatformDirs

class AppPaths:
    """
    Provides standardized paths for configuration, data, cache, and state.
    Paths are resolved based on the operating system standards.
    """
    def __init__(self, appname: str = "qt-api-framework", author: str = "confrey59"):
        self._dirs = PlatformDirs(appname=appname, appauthor=author, version="v1")

    # --- Standard Paths ---

    @property
    def user_config(self) -> Path:
        """Returns path to user config directory (~/.config/... on Linux)."""
        return Path(self._dirs.user_config_path)

    @property
    def user_data(self) -> Path:
        """Returns path to user data directory (~/.local/share/... on Linux)."""
        return Path(self._dirs.user_data_path)

    @property
    def user_cache(self) -> Path:
        """Returns path to cache directory (~/.cache/... on Linux)."""
        return Path(self._dirs.user_cache_path)

    @property
    def user_state(self) -> Path:
        """Returns path to state directory (~/.local/state/... on Linux)."""
        return Path(self._dirs.user_state_path)

    @property
    def user_log(self) -> Path:
        """Returns path to log directory."""
        return self.user_state

    # --- Application Specific Subdirectories ---

    @property
    def plugins_dir(self) -> Path:
        """Directory where user-installed plugins live."""
        return self.user_data / "plugins"

    @property
    def profiles_dir(self) -> Path:
        """Directory where user profiles configurations live."""
        return self.user_config / "profiles"

    def ensure_dirs_exist(self) -> None:
        """
        Creates all necessary directories if they don't exist.
        Should be called at application startup.
        """
        self.user_config.mkdir(parents=True, exist_ok=True)
        self.user_data.mkdir(parents=True, exist_ok=True)
        self.user_cache.mkdir(parents=True, exist_ok=True)
        self.user_state.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

# Singleton instance for easy import
paths = AppPaths()