import json
import os
import logging
import copy
import threading

DEFAULT_CONFIG = {
    "wake_word": "hey cerp",
    "listen_timeout": 5,
    "phrase_time_limit": 5,
    "energy_threshold": 300,
    "vosk_model_path": "model",
    "ui": {
        "high_contrast": False,
        "large_text": False,
        "tts_feedback": True,
        "font_scale": 1.0
    },
    "app_paths": {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "word": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "excel": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        "powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"
    },
    "web_apps": {
        "gmail": "https://mail.google.com",
        "youtube": "https://www.youtube.com",
        "instagram": "https://www.instagram.com",
        "google": "https://www.google.com"
    },
    "custom_commands": {}
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """Loads, validates, and persists CERP configuration.

    Falls back to DEFAULT_CONFIG (merged with whatever partial/valid data
    exists on disk) if the config file is missing, unreadable, or corrupt,
    so the app never fails to start because of a bad config.json.
    """

    def __init__(self, path: str = "config.json"):
        self.path = path
        self._lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            logging.warning(f"Config file not found at {self.path}, using defaults.")
            return copy.deepcopy(DEFAULT_CONFIG)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("Config root must be a JSON object.")
            merged = _deep_merge(DEFAULT_CONFIG, raw)
            logging.info("Config loaded successfully.")
            return merged
        except Exception as e:
            logging.error(f"Failed to load config ({e}); falling back to defaults.")
            return copy.deepcopy(DEFAULT_CONFIG)

    def reload(self):
        with self._lock:
            self.data = self._load()

    def save(self) -> bool:
        try:
            with self._lock:
                tmp_path = self.path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2)
                os.replace(tmp_path, self.path)
            logging.info("Config saved successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            return False

    def get(self, *keys, default=None):
        """Get a nested value, e.g. get('ui', 'font_scale')."""
        node = self.data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, value, *keys):
        """Set a nested value, e.g. set(1.5, 'ui', 'font_scale')."""
        if not keys:
            return
        node = self.data
        for key in keys[:-1]:
            if key not in node or not isinstance(node[key], dict):
                node[key] = {}
            node = node[key]
        node[keys[-1]] = value

    @property
    def app_paths(self) -> dict:
        return self.data.get("app_paths", {})

    @property
    def web_apps(self) -> dict:
        return self.data.get("web_apps", {})

    @property
    def custom_commands(self) -> dict:
        return self.data.get("custom_commands", {})

    def add_custom_command(self, name: str, path_or_url: str) -> None:
        self.data.setdefault("custom_commands", {})[name.lower().strip()] = path_or_url
        self.save()

    def remove_custom_command(self, name: str) -> bool:
        cmds = self.data.get("custom_commands", {})
        key = name.lower().strip()
        if key in cmds:
            del cmds[key]
            self.save()
            return True
        return False
