import os
import re
import time
import datetime
import logging
import threading
from typing import Dict, List, Optional, Callable
from logging.handlers import RotatingFileHandler

import psutil
import pyautogui
import speech_recognition as sr

import platform_utils
from config_manager import ConfigManager

# Ensure the logs directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

handler = RotatingFileHandler('logs/cerp.log', maxBytes=5 * 1024 * 1024, backupCount=2)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Spoken punctuation/control words recognized during dictation ("voice typing").
# Longer phrases are matched before shorter ones that could be a substring of them.
DICTATION_PUNCTUATION = [
    ("new paragraph", "\n\n"),
    ("new line", "\n"),
    ("open quote", " \""),
    ("close quote", "\" "),
    ("open bracket", " ("),
    ("close bracket", ") "),
    ("exclamation mark", "! "),
    ("exclamation point", "! "),
    ("question mark", "? "),
    ("comma", ", "),
    ("period", ". "),
    ("full stop", ". "),
    ("colon", ": "),
    ("semicolon", "; "),
    ("dash", " - "),
    ("hyphen", "-"),
]


def apply_dictation_punctuation(text: str) -> str:
    """Convert spoken punctuation words in `text` into literal punctuation.

    Pure function (no I/O) so it can be unit-tested independently of the
    microphone/typing loop. Case-insensitive; word-boundary matched so
    "commander" isn't mangled by the "comma" rule.
    """
    result = text
    for phrase, replacement in DICTATION_PUNCTUATION:
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        result = pattern.sub(replacement, result)
    # Collapse any double spaces created by adjacent punctuation substitutions.
    result = re.sub(r' {2,}', ' ', result)
    # Tidy up a space introduced before sentence-ending punctuation.
    result = re.sub(r'\s+([.,!?;:])', r'\1', result)
    return result.strip()


class Automation:
    """Handles computer automation tasks with history, config, and cross-platform support."""

    # Ordered (pattern, handler_name) pairs. Order matters: more specific
    # patterns must come before their more general prefixes.
    COMMAND_PATTERNS = [
        (r"^set volume(?:\s+to)?\s+(\d{1,3})\s*%?$", "set_volume"),
        (r"^(?:increase|raise|turn up) volume$", "volume_up"),
        (r"^(?:decrease|lower|turn down) volume$", "volume_down"),
        (r"^set brightness(?:\s+to)?\s+(\d{1,3})\s*%?$", "set_brightness"),
        (r"^(?:increase|raise|turn up) brightness$", "brightness_up"),
        (r"^(?:decrease|lower|turn down) brightness$", "brightness_down"),
        (r"^(?:exit|quit application)$", "exit_application"),
        (r"^open (.+)$", "open_application"),
        (r"^(?:close|quit) (.+)$", "close_application"),
        (r"^system status$", "get_system_status"),
        (r"^start voice typing$", "start_voice_typing"),
        (r"^stop voice typing$", "stop_voice_typing"),
        (r"^skip shorts?$", "skip_shorts"),
        (r"^skip next$", "skip_next"),
        (r"^scroll up$", "scroll_up"),
        (r"^scroll down$", "scroll_down"),
        (r"^(?:take a )?screenshot$", "take_screenshot"),
        (r"^lock(?: the)? screen$", "lock_screen"),
        (r"^(?:go to )?sleep$", "sleep_system"),
        (r"^confirm shutdown$", "confirm_shutdown"),
        (r"^shut ?down$", "request_shutdown"),
        (r"^cancel shutdown$", "cancel_shutdown"),
        (r"^repeat(?: that| last command)?$", "repeat_last"),
    ]

    def __init__(self, config: Optional[ConfigManager] = None):
        pyautogui.FAILSAFE = True
        self.config = config or ConfigManager()
        self.processes: Dict[str, psutil.Process] = {}
        self.history: List[str] = []
        self.max_history = 10
        self.voice_typing_active = False
        self.recognizer = sr.Recognizer()
        self._last_command: Optional[str] = None
        self._shutdown_pending = False
        self._brightness_estimate = 50  # best-effort tracker; platform APIs rarely expose "get"
        self._compiled_patterns = [(re.compile(p), name) for p, name in self.COMMAND_PATTERNS]
        logging.info("Automation module initialized.")

    # ------------------------------------------------------------------ #
    # Command routing
    # ------------------------------------------------------------------ #
    def execute_task(self, command: str) -> str:
        """Parse a natural-language command and dispatch to the matching handler."""
        if not command:
            return "No command received."
        normalized = command.strip().lower()
        logging.info(f"Executing command: {normalized}")
        try:
            for pattern, handler_name in self._compiled_patterns:
                match = pattern.match(normalized)
                if match:
                    handler_fn: Callable = getattr(self, handler_name)
                    result = handler_fn(*match.groups()) if match.groups() else handler_fn()
                    if handler_name != "repeat_last":
                        self._last_command = normalized
                    return result

            # Fall back to user-defined custom commands (exact name match).
            custom = self.config.custom_commands
            for name, target in custom.items():
                if normalized == name or normalized == f"open {name}":
                    self._last_command = normalized
                    return self._open_custom(name, target)

            logging.warning(f"No handler matched command: {normalized}")
            return f"Sorry, I didn't understand: '{command}'."
        except Exception as e:
            logging.error(f"Command execution failed: {normalized}, Error: {e}")
            return f"Error executing command: {str(e)}"

    def repeat_last(self) -> str:
        if not self._last_command:
            return "There's no previous command to repeat."
        cmd, self._last_command = self._last_command, None  # avoid recursive loops
        result = self.execute_task(cmd)
        self._last_command = cmd
        return result

    # ------------------------------------------------------------------ #
    # Applications
    # ------------------------------------------------------------------ #
    def open_application(self, app_name: str) -> str:
        logging.info(f"Attempting to open: {app_name}")
        try:
            key = app_name.lower().replace(" ", "")

            if key in self.config.web_apps:
                platform_utils.open_url(self.config.web_apps[key])
                message = f"Opening {app_name} in browser..."
                self._add_to_history(message)
                logging.info(f"Successfully opened: {app_name}")
                return message

            if key in self.config.custom_commands:
                return self._open_custom(key, self.config.custom_commands[key])

            app_path = self.config.app_paths.get(key)
            if app_path:
                platform_utils.open_target(app_path)
                message = f"Opening {app_name}..."
                self._add_to_history(message)
                logging.info(f"Successfully opened: {app_name}")
                return message

            logging.warning(f"Application not found: {app_name}")
            return f"Application '{app_name}' not found. Add it via Settings > Custom Commands."
        except Exception as e:
            logging.error(f"Failed to open {app_name}: {e}")
            return f"Error opening {app_name}: {str(e)}"

    def _open_custom(self, name: str, target: str) -> str:
        try:
            if target.startswith("http://") or target.startswith("https://"):
                platform_utils.open_url(target)
            else:
                platform_utils.open_target(target)
            message = f"Opening custom command '{name}'..."
            self._add_to_history(message)
            return message
        except Exception as e:
            logging.error(f"Failed to open custom command {name}: {e}")
            return f"Error opening '{name}': {str(e)}"

    def close_application(self, app_name: str) -> str:
        logging.info(f"Attempting to close: {app_name}")
        try:
            key = app_name.lower().replace(" ", "")
            if key in self.processes:
                process = self.processes[key]
                if process.is_running():
                    process.terminate()
                    process.wait(timeout=5)
                del self.processes[key]
                message = f"Closed {app_name}."
                self._add_to_history(message)
                logging.info(f"Successfully closed: {app_name}")
                return message
            logging.warning(f"Application not tracked: {app_name}")
            return f"'{app_name}' isn't a tracked process (it may not have been opened by CERP)."
        except Exception as e:
            logging.error(f"Failed to close {app_name}: {e}")
            return f"Error closing {app_name}: {str(e)}"

    # ------------------------------------------------------------------ #
    # System control
    # ------------------------------------------------------------------ #
    def volume_up(self) -> str:
        return self.set_volume_relative(10.0)

    def volume_down(self) -> str:
        return self.set_volume_relative(-10.0)

    def set_volume_relative(self, change: float) -> str:
        new_volume = platform_utils.adjust_volume(change)
        if new_volume < 0:
            message = "Volume adjusted (exact level unavailable on this system)."
        else:
            message = f"Volume adjusted to {int(new_volume * 100)}%."
        logging.info(message)
        self._add_to_history(message)
        return message

    def set_volume(self, level_str: str) -> str:
        try:
            level = max(0, min(100, int(level_str)))
        except ValueError:
            return f"'{level_str}' isn't a valid volume level."
        current = platform_utils.adjust_volume(0)  # read-ish; harmless no-op change
        # Compute an approximate delta since adjust_volume works relatively.
        # For Windows this still ends accurately because adjust_volume sets scalar directly on read.
        change = (level - (current * 100 if current >= 0 else level))
        new_volume = platform_utils.adjust_volume(change)
        message = f"Volume set to {level}%." if new_volume >= 0 else f"Volume set to approximately {level}%."
        logging.info(message)
        self._add_to_history(message)
        return message

    def brightness_up(self) -> str:
        return self._set_brightness_absolute(self._brightness_estimate + 10)

    def brightness_down(self) -> str:
        return self._set_brightness_absolute(self._brightness_estimate - 10)

    def set_brightness(self, level_str: str) -> str:
        try:
            level = int(level_str)
        except ValueError:
            return f"'{level_str}' isn't a valid brightness level."
        return self._set_brightness_absolute(level)

    def _set_brightness_absolute(self, level: int) -> str:
        level = max(0, min(100, level))
        ok = platform_utils.set_brightness(level)
        if ok:
            self._brightness_estimate = level
            message = f"Brightness set to {level}%."
        else:
            message = "Brightness control isn't supported on this system."
        logging.info(message)
        self._add_to_history(message)
        return message

    def get_system_status(self) -> str:
        try:
            battery = psutil.sensors_battery()
            battery_status = f"{battery.percent}%" if battery else "Unknown"
            internet_status = "Connected" if any(iface.isup for iface in psutil.net_if_stats().values()) else "Disconnected"
            cpu_usage = f"{psutil.cpu_percent()}%"
            memory_usage = f"{psutil.virtual_memory().percent}%"
            status = (
                f"Battery: {battery_status}, Time: {datetime.datetime.now().strftime('%H:%M:%S')}, "
                f"Internet: {internet_status}, CPU: {cpu_usage}, Memory: {memory_usage}"
            )
            logging.info("System status retrieved")
            self._add_to_history(status)
            return status
        except Exception as e:
            logging.error(f"System status failed: {e}")
            return f"Error retrieving status: {str(e)}"

    def scroll_up(self) -> str:
        pyautogui.scroll(300)
        message = "Scrolled up."
        self._add_to_history(message)
        return message

    def scroll_down(self) -> str:
        pyautogui.scroll(-300)
        message = "Scrolled down."
        self._add_to_history(message)
        return message

    def take_screenshot(self) -> str:
        os.makedirs("screenshots", exist_ok=True)
        filename = f"screenshots/screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ok = platform_utils.take_screenshot(filename)
        message = f"Screenshot saved to {filename}." if ok else "Failed to take screenshot."
        logging.info(message)
        self._add_to_history(message)
        return message

    def lock_screen(self) -> str:
        ok = platform_utils.lock_screen()
        message = "Locking screen..." if ok else "Screen lock isn't supported on this system."
        self._add_to_history(message)
        return message

    def sleep_system(self) -> str:
        ok = platform_utils.sleep_system()
        message = "Putting system to sleep..." if ok else "Sleep isn't supported on this system."
        self._add_to_history(message)
        return message

    def request_shutdown(self) -> str:
        """Two-step shutdown: requires an explicit 'confirm shutdown' follow-up."""
        self._shutdown_pending = True
        message = "Shutdown requested. Say 'confirm shutdown' within 15 seconds to proceed, or 'cancel shutdown'."
        self._add_to_history(message)
        threading.Timer(15.0, self._expire_shutdown_request).start()
        return message

    def _expire_shutdown_request(self):
        if self._shutdown_pending:
            self._shutdown_pending = False
            logging.info("Shutdown request expired (not confirmed in time).")

    def confirm_shutdown(self) -> str:
        if not self._shutdown_pending:
            return "No pending shutdown to confirm. Say 'shutdown' first."
        self._shutdown_pending = False
        ok = platform_utils.shutdown_system(delay_seconds=10)
        message = "Shutdown confirmed. The system will power off in 10 seconds." if ok else "Failed to initiate shutdown."
        logging.info(message)
        self._add_to_history(message)
        return message

    def cancel_shutdown(self) -> str:
        self._shutdown_pending = False
        ok = platform_utils.cancel_shutdown()
        message = "Shutdown cancelled." if ok else "No shutdown was in progress."
        self._add_to_history(message)
        return message

    # ------------------------------------------------------------------ #
    # Voice typing
    # ------------------------------------------------------------------ #
    def start_voice_typing(self) -> str:
        if self.voice_typing_active:
            return "Voice typing is already active."
        self.voice_typing_active = True
        thread = threading.Thread(target=self._voice_typing_loop, daemon=True)
        thread.start()
        message = (
            "Voice typing started. Say punctuation words like 'comma', 'period', "
            "or 'new line' to insert them, and 'stop voice typing' to stop."
        )
        logging.info(message)
        self._add_to_history(message)
        return message

    def _voice_typing_loop(self):
        try:
            self.open_application("notepad")
            pyautogui.sleep(1)
            pyautogui.hotkey('win', 'up')
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                while self.voice_typing_active:
                    logging.info("Listening for voice typing...")
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        text = self.recognizer.recognize_google(audio, language="en-US")
                        if "stop voice typing" in text.lower():
                            self.stop_voice_typing()
                            break
                        typed_text = apply_dictation_punctuation(text)
                        pyautogui.write(typed_text + " ")
                        logging.info(f"Typed: {typed_text}")
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        logging.warning("Could not understand audio.")
                    except sr.RequestError:
                        logging.error("Speech recognition request failed.")
        except Exception as e:
            logging.error(f"Voice typing thread failed: {e}")
            self.voice_typing_active = False

    def stop_voice_typing(self) -> str:
        self.voice_typing_active = False
        message = "Voice typing stopped."
        logging.info(message)
        self._add_to_history(message)
        return message

    # ------------------------------------------------------------------ #
    # Media
    # ------------------------------------------------------------------ #
    def skip_shorts(self) -> str:
        try:
            pyautogui.press("down")
            message = "Skipped a Short."
            logging.info(message)
            self._add_to_history(message)
            return message
        except Exception as e:
            logging.error(f"Failed to skip Short: {e}")
            return f"Error skipping Short: {str(e)}"

    def skip_next(self) -> str:
        try:
            browser_names = ["chrome", "msedge", "firefox"]
            for proc in psutil.process_iter(['name']):
                name = (proc.info.get('name') or "").lower()
                if any(browser in name for browser in browser_names):
                    pyautogui.hotkey("alt", "tab")
                    time.sleep(0.5)
                    break
            pyautogui.press("right")
            time.sleep(0.5)
            message = "Skipped to the next content."
            logging.info(message)
            self._add_to_history(message)
            return message
        except Exception as e:
            logging.error(f"Failed to skip to next content: {e}")
            return f"Error skipping to next content: {str(e)}"

    # ------------------------------------------------------------------ #
    # Misc
    # ------------------------------------------------------------------ #
    def exit_application(self) -> str:
        message = "Exiting application..."
        logging.info(message)
        self._add_to_history(message)
        return message

    def _add_to_history(self, action: str):
        self.history.append(action)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self) -> List[str]:
        return self.history.copy()
