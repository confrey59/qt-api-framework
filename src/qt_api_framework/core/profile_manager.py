"""
Profile management for qt-api-framework.
Handles creation, loading, saving, and listing of user profiles.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import paths

logger = logging.getLogger(__name__)

class ProfileManager:
    """
    Manages user profiles stored as JSON files in the user config directory.
    """
    PROFILE_EXTENSION = ".json"

    def __init__(self):
        self._profiles_dir = paths.profiles_dir
        paths.ensure_dirs_exist()

    def is_first_run(self) -> bool:
        """Returns True if no profiles exist yet (fresh install)."""
        return len(self.list_profiles()) == 0

    def list_profiles(self) -> List[str]:
        """Returns a list of available profile names."""
        if not self._profiles_dir.exists():
            return []
        return [
            f.stem for f in self._profiles_dir.glob(f"*{self.PROFILE_EXTENSION}")
        ]

    def profile_exists(self, name: str) -> bool:
        """Checks if a profile with the given name exists."""
        return (self._profiles_dir / f"{name}{self.PROFILE_EXTENSION}").exists()

    def create_profile(self, name: str, config: Optional[Dict[str, Any]] = None) -> Path:
        """
        Creates a new profile with default or custom configuration.
        Returns the path to the created profile file.
        """
        if self.profile_exists(name):
            raise FileExistsError(f"Profile '{name}' already exists.")

        default_config = {
            "name": name,
            "api_base_url": "",
            "ws_base_url": "",
            "theme": "dark",
            "mdi_mode": "tabs",
            "auth_enabled": False,
            "plugins": []
        }
        if config:
            default_config.update(config)

        profile_path = self._profiles_dir / f"{name}{self.PROFILE_EXTENSION}"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created new profile: {name}")
        return profile_path

    def load_profile(self, name: str) -> Dict[str, Any]:
        """Loads and returns the configuration for a given profile."""
        profile_path = self._profiles_dir / f"{name}{self.PROFILE_EXTENSION}"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found.")

        with open(profile_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.debug(f"Loaded profile: {name}")
        return config

    def save_profile(self, name: str, config: Dict[str, Any]) -> None:
        """Saves configuration changes to an existing profile."""
        profile_path = self._profiles_dir / f"{name}{self.PROFILE_EXTENSION}"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found. Use create_profile() first.")

        config["name"] = name  # Ensure name consistency
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Saved profile: {name}")

    def delete_profile(self, name: str) -> None:
        """Deletes a profile file."""
        profile_path = self._profiles_dir / f"{name}{self.PROFILE_EXTENSION}"
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"Deleted profile: {name}")
        else:
            logger.warning(f"Attempted to delete non-existent profile: {name}")

    def get_default_profile_path(self) -> Optional[Path]:
        """
        Returns the path to the default/last-used profile.
        For now, returns the first available profile or None.
        Can be extended to read a 'last_used' state file.
        """
        profiles = self.list_profiles()
        if not profiles:
            return None
        return self._profiles_dir / f"{profiles[0]}{self.PROFILE_EXTENSION}"