import json
import os
import tempfile
import unittest

from config_manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmp_dir, "config.json")

    def _write(self, data):
        with open(self.config_path, "w") as f:
            json.dump(data, f)

    def test_missing_file_falls_back_to_defaults(self):
        cm = ConfigManager(self.config_path)
        self.assertEqual(cm.get("wake_word"), DEFAULT_CONFIG["wake_word"])

    def test_corrupt_file_falls_back_to_defaults(self):
        with open(self.config_path, "w") as f:
            f.write("{not valid json")
        cm = ConfigManager(self.config_path)
        self.assertEqual(cm.get("wake_word"), DEFAULT_CONFIG["wake_word"])

    def test_partial_file_merges_with_defaults(self):
        self._write({"wake_word": "hey robot"})
        cm = ConfigManager(self.config_path)
        self.assertEqual(cm.get("wake_word"), "hey robot")
        # Untouched keys still come from defaults.
        self.assertEqual(cm.get("listen_timeout"), DEFAULT_CONFIG["listen_timeout"])
        self.assertIn("notepad", cm.app_paths)

    def test_nested_get_and_set(self):
        cm = ConfigManager(self.config_path)
        cm.set(True, "ui", "high_contrast")
        self.assertTrue(cm.get("ui", "high_contrast"))
        self.assertIsNone(cm.get("nonexistent", "key"))
        self.assertEqual(cm.get("nonexistent", "key", default="fallback"), "fallback")

    def test_save_and_reload_roundtrip(self):
        cm = ConfigManager(self.config_path)
        cm.set("hey test", "wake_word")
        self.assertTrue(cm.save())

        cm2 = ConfigManager(self.config_path)
        self.assertEqual(cm2.get("wake_word"), "hey test")

    def test_custom_commands_add_and_remove(self):
        cm = ConfigManager(self.config_path)
        cm.add_custom_command("Spotify", "C:\\Spotify\\Spotify.exe")
        self.assertIn("spotify", cm.custom_commands)

        removed = cm.remove_custom_command("spotify")
        self.assertTrue(removed)
        self.assertNotIn("spotify", cm.custom_commands)

        self.assertFalse(cm.remove_custom_command("does-not-exist"))

    def tearDown(self):
        for name in os.listdir(self.tmp_dir):
            os.remove(os.path.join(self.tmp_dir, name))
        os.rmdir(self.tmp_dir)


if __name__ == "__main__":
    unittest.main()
