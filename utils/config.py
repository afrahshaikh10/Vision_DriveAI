import os
import json
from typing import Any, Dict
from utils.logger import logger

DEFAULT_CONFIG = {
    "camera_id": 0,
    "steering_sensitivity": 1.0,
    "steering_dead_zone": 5.0,  # in degrees
    "min_detection_confidence": 0.7,
    "min_tracking_confidence": 0.7,
    "smoothing_amount": 5,  # Moving average window size
    "fps_limit": 30,
    "key_bindings": {
        "accelerate": "up",
        "brake": "down",
        "left": "left",
        "right": "right",
        "handbrake": "space"
    },
    "calibration": {
        "neutral_angle": 0.0,
        "max_left_angle": -45.0,
        "max_right_angle": 45.0,
        "neutral_distance": 200.0, # distance between hands
        "calibrated": False
    }
}

class ConfigManager:
    """Manages loading and saving configuration parameters to a JSON file."""
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        """Loads configuration from the file. Creates default if file doesn't exist."""
        if not os.path.exists(self.config_path):
            logger.info(f"Config file not found at {self.config_path}. Creating default config.")
            self.save()
            return

        try:
            with open(self.config_path, "r") as f:
                loaded_config = json.load(f)
                # Merge loaded config with defaults to ensure all keys exist
                self.config = self._merge_dicts(DEFAULT_CONFIG, loaded_config)
            logger.info(f"Config loaded successfully from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}. Using defaults.")
            self.config = DEFAULT_CONFIG.copy()

    def save(self) -> bool:
        """Saves current configuration to the file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Config saved successfully to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a configuration setting."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Sets a configuration setting and saves it."""
        self.config[key] = value
        self.save()

    def update_multiple(self, settings: Dict[str, Any]) -> None:
        """Updates multiple settings at once and saves them."""
        for key, value in settings.items():
            if isinstance(value, dict) and key in self.config:
                self.config[key].update(value)
            else:
                self.config[key] = value
        self.save()

    def _merge_dicts(self, defaults: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merges configuration dicts to prevent missing sub-keys."""
        merged = defaults.copy()
        for k, v in loaded.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = self._merge_dicts(merged[k], v)
            else:
                merged[k] = v
        return merged
