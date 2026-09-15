import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from config_manager import ConfigManager
import automation
from automation import apply_dictation_punctuation


def make_automation():
    tmp_dir = tempfile.mkdtemp()
    config_path = os.path.join(tmp_dir, "config.json")
    config = ConfigManager(config_path)
    return automation.Automation(config), tmp_dir, config_path


class TestCommandRouting(unittest.TestCase):
    def setUp(self):
        self.auto, self.tmp_dir, self.config_path = make_automation()

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmp_dir)

    @patch("automation.platform_utils.open_target")
    def test_open_known_local_app(self, mock_open_target):
        result = self.auto.execute_task("open notepad")
        mock_open_target.assert_called_once_with("notepad.exe")
        self.assertIn("Opening notepad", result)

    @patch("automation.platform_utils.open_url")
    def test_open_known_web_app(self, mock_open_url):
        result = self.auto.execute_task("open youtube")
        mock_open_url.assert_called_once_with("https://www.youtube.com")
        self.assertIn("browser", result)

    def test_open_unknown_app(self):
        result = self.auto.execute_task("open some totally unknown app")
        self.assertIn("not found", result)

    def test_close_untracked_app(self):
        result = self.auto.execute_task("close notepad")
        self.assertIn("isn't a tracked process", result)

    @patch("automation.platform_utils.adjust_volume", return_value=0.5)
    def test_volume_up_uses_relative_change(self, mock_adjust):
        result = self.auto.execute_task("increase volume")
        mock_adjust.assert_called_once_with(10.0)
        self.assertIn("50%", result)

    @patch("automation.platform_utils.adjust_volume", return_value=0.2)
    def test_volume_down_uses_relative_change(self, mock_adjust):
        self.auto.execute_task("decrease volume")
        mock_adjust.assert_called_once_with(-10.0)

    def test_set_volume_rejects_non_numeric(self):
        # Non-numeric volume never matches the set_volume pattern at all,
        # so it falls through to the generic "didn't understand" response.
        result = self.auto.execute_task("set volume to abc")
        self.assertIn("didn't understand", result)

    def test_set_volume_invalid_direct_call(self):
        # set_volume() itself still guards against bad input if called directly.
        result = self.auto.set_volume("abc")
        self.assertIn("isn't a valid volume level", result)

    @patch("automation.psutil.sensors_battery", return_value=None)
    @patch("automation.psutil.net_if_stats", return_value={})
    @patch("automation.psutil.cpu_percent", return_value=12.3)
    @patch("automation.psutil.virtual_memory")
    def test_system_status_format(self, mock_vm, mock_cpu, mock_net, mock_batt):
        mock_vm.return_value = MagicMock(percent=55.0)
        result = self.auto.execute_task("system status")
        self.assertIn("Battery: Unknown", result)
        self.assertIn("CPU: 12.3%", result)
        self.assertIn("Memory: 55.0%", result)

    @patch("automation.pyautogui.scroll")
    def test_scroll_up_and_down(self, mock_scroll):
        self.auto.execute_task("scroll up")
        mock_scroll.assert_called_with(300)
        self.auto.execute_task("scroll down")
        mock_scroll.assert_called_with(-300)

    @patch("automation.platform_utils.take_screenshot", return_value=True)
    def test_take_screenshot_success(self, mock_shot):
        result = self.auto.execute_task("take a screenshot")
        self.assertIn("Screenshot saved", result)
        mock_shot.assert_called_once()

    @patch("automation.platform_utils.lock_screen", return_value=True)
    def test_lock_screen(self, mock_lock):
        result = self.auto.execute_task("lock the screen")
        self.assertIn("Locking screen", result)

    @patch("automation.platform_utils.shutdown_system", return_value=True)
    def test_shutdown_requires_confirmation(self, mock_shutdown):
        request_result = self.auto.execute_task("shutdown")
        self.assertIn("confirm shutdown", request_result.lower())
        mock_shutdown.assert_not_called()

        confirm_result = self.auto.execute_task("confirm shutdown")
        self.assertIn("Shutdown confirmed", confirm_result)
        mock_shutdown.assert_called_once()

    def test_confirm_shutdown_without_request_is_noop(self):
        result = self.auto.execute_task("confirm shutdown")
        self.assertIn("No pending shutdown", result)

    @patch("automation.platform_utils.cancel_shutdown", return_value=True)
    def test_cancel_shutdown(self, mock_cancel):
        self.auto.execute_task("shutdown")
        result = self.auto.execute_task("cancel shutdown")
        self.assertIn("Shutdown cancelled", result)
        self.assertFalse(self.auto._shutdown_pending)

    def test_repeat_with_no_history(self):
        result = self.auto.execute_task("repeat")
        self.assertIn("no previous command", result)

    @patch("automation.platform_utils.open_target")
    def test_repeat_replays_last_command(self, mock_open_target):
        self.auto.execute_task("open notepad")
        mock_open_target.reset_mock()
        result = self.auto.execute_task("repeat")
        mock_open_target.assert_called_once_with("notepad.exe")
        self.assertIn("Opening notepad", result)

    def test_unmatched_command_returns_friendly_message(self):
        result = self.auto.execute_task("do a backflip")
        self.assertIn("didn't understand", result)

    def test_exit_and_quit_application_both_exit(self):
        self.assertIn("Exiting", self.auto.execute_task("exit"))
        self.assertIn("Exiting", self.auto.execute_task("quit application"))

    def test_quit_appname_closes_not_exits(self):
        result = self.auto.execute_task("quit notepad")
        self.assertIn("isn't a tracked process", result)

    @patch("automation.platform_utils.open_target")
    def test_custom_command_open_by_name(self, mock_open_target):
        self.auto.config.add_custom_command("spotify", "C:\\Spotify\\Spotify.exe")
        result = self.auto.execute_task("open spotify")
        mock_open_target.assert_called_once_with("C:\\Spotify\\Spotify.exe")
        self.assertIn("custom command 'spotify'", result)


    @patch("automation.platform_utils.set_brightness", return_value=True)
    def test_brightness_up_and_down(self, mock_set):
        result = self.auto.execute_task("increase brightness")
        mock_set.assert_called_once_with(60)
        self.assertIn("Brightness set to 60%", result)

        mock_set.reset_mock()
        result = self.auto.execute_task("decrease brightness")
        mock_set.assert_called_once_with(50)
        self.assertIn("Brightness set to 50%", result)

    @patch("automation.platform_utils.set_brightness", return_value=True)
    def test_set_brightness_absolute_clamped(self, mock_set):
        result = self.auto.execute_task("set brightness to 150")
        mock_set.assert_called_once_with(100)
        self.assertIn("Brightness set to 100%", result)

    @patch("automation.platform_utils.set_brightness", return_value=False)
    def test_brightness_unsupported(self, mock_set):
        result = self.auto.execute_task("set brightness to 50")
        self.assertIn("isn't supported", result)


class TestDictationPunctuation(unittest.TestCase):
    def test_comma_and_period(self):
        self.assertEqual(
            apply_dictation_punctuation("hello comma world period"),
            "hello, world."
        )

    def test_question_and_exclamation(self):
        self.assertEqual(
            apply_dictation_punctuation("are you there question mark"),
            "are you there?"
        )
        self.assertEqual(
            apply_dictation_punctuation("watch out exclamation mark"),
            "watch out!"
        )

    def test_new_line_and_paragraph(self):
        result = apply_dictation_punctuation("first line new line second line")
        self.assertIn("\n", result)

    def test_word_boundary_not_mangled(self):
        # "commander" must not be corrupted by the "comma" rule.
        result = apply_dictation_punctuation("the commander arrived")
        self.assertEqual(result, "the commander arrived")

    def test_case_insensitive(self):
        self.assertEqual(
            apply_dictation_punctuation("hello COMMA world"),
            "hello, world"
        )

    def test_plain_text_unchanged(self):
        self.assertEqual(
            apply_dictation_punctuation("just a normal sentence"),
            "just a normal sentence"
        )


if __name__ == "__main__":
    unittest.main()
