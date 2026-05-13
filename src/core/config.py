"""
Config module for managing game settings via JSON.
Handles cross-platform paths, default values, and file I/O.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("Scrapyard.Config")

class Config:
    """Manages game configuration settings.
    
    Settings are stored in a JSON file in the user's home directory.
    """
    
    DEFAULT_SETTINGS = {
        "graphics": {
            "resolution": [1280, 720],
            "fullscreen": False,
            "vsync": True,
            "msaa": 4,
            "render_distance": 15,
            "chunk_update_threshold": 2,
        },
        "audio": {
            "master_volume": 1.0,
            "music_volume": 0.7,
            "sfx_volume": 1.0,
            "muted": False,
        },
        "performance": {
            # "off" | "low" | "medium" | "high"
            "shadow_quality": "medium",
            # "low" | "medium" | "high"
            "texture_quality": "high",
            # 0 = unlimited
            "fps_limit": 0,
        },
        # "auto" detects system locale via i18n; or explicit code e.g. "pl"
        "language": "auto",
    }
    
    def __init__(self) -> None:
        """Initializes the Config manager and loads settings."""
        self.config_dir = Path.home() / ".scrapyard"
        self.config_path = self.config_dir / "settings.json"
        self.settings: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Loads settings from the JSON file or creates defaults if missing."""
        try:
            if not self.config_dir.exists():
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.settings = self._merge_dicts(self.DEFAULT_SETTINGS, user_settings)
            else:
                logger.info("Config file missing. Using defaults.")
                self.settings = self.DEFAULT_SETTINGS.copy()
                self.save()
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}. Falling back to defaults.")
            self.settings = self.DEFAULT_SETTINGS.copy()

    def save(self) -> None:
        """Saves current settings to the JSON file."""
        try:
            if not self.config_dir.exists():
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Settings saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Retrieves a nested setting using a dot-separated path (e.g., 'graphics.vsync')."""
        keys = key_path.split(".")
        value = self.settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """Sets a nested setting using a dot-separated path."""
        keys = key_path.split(".")
        target = self.settings
        try:
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
        except Exception as e:
            logger.error(f"Failed to set config key {key_path}: {e}")

    def _merge_dicts(self, defaults: Dict, user: Dict) -> Dict:
        """Deep merges user settings into defaults."""
        result = defaults.copy()
        for k, v in user.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_dicts(result[k], v)
            else:
                result[k] = v
        return result
