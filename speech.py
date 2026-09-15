import os
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler

import speech_recognition as sr

from automation import Automation
from config_manager import ConfigManager

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

handler = RotatingFileHandler('logs/cerp.log', maxBytes=5 * 1024 * 1024, backupCount=2)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class SpeechProcessor:
    """Captures voice input and delegates parsing/execution to Automation.

    Automation.execute_task now owns all command-matching logic (see its
    COMMAND_PATTERNS), so this class no longer duplicates a second,
    inconsistent dispatch table — it just listens and hands the raw text
    straight through.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config.get("energy_threshold", default=300)
        self.auto = Automation(self.config)
        logging.info("Speech processor initialized")

    def listen(self) -> str:
        """Capture voice command with robust error handling. Always returns a string."""
        timeout = self.config.get("listen_timeout", default=5)
        phrase_limit = self.config.get("phrase_time_limit", default=5)
        try:
            with sr.Microphone() as source:
                logging.info("Listening for command...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            command = self.recognizer.recognize_google(audio, language="en-US").lower()
            logging.info(f"Recognized command: {command}")
            return command
        except sr.WaitTimeoutError:
            logging.warning("Listening timed out")
            return "Sorry, timed out waiting for command."
        except sr.UnknownValueError:
            logging.warning("Could not understand audio")
            return "Sorry, I couldn't understand."
        except sr.RequestError:
            logging.error("Speech recognition request failed")
            return "Could not request results, check internet."
        except OSError:
            logging.error("Microphone not found")
            return "Error: Microphone not found, check audio settings."
        except Exception as e:
            logging.error(f"Speech recognition failed: {e}")
            return f"Error: {str(e)}"

    def process_command(self, command: str) -> str:
        """Execute a recognized command via Automation."""
        if command.lower().startswith("error") or command.lower().startswith("sorry"):
            return command
        logging.info(f"Processing command: {command}")
        try:
            return self.auto.execute_task(command)
        except Exception as e:
            logging.error(f"Command processing failed: {command}, Error: {e}")
            return f"Error processing command: {str(e)}"


if __name__ == "__main__":
    processor = SpeechProcessor()
    heard = processor.listen()
    print(processor.process_command(heard))
