"""Wake-word detection.

Uses Vosk (offline) when a model is available at config['vosk_model_path'];
otherwise falls back to online Google recognition via SpeechRecognition,
listening for the configured wake phrase. This replaces the old ad-hoc
"say hello" listener in gui.py and makes the README's offline-recognition
claim actually true when a Vosk model is present.

Download a small English model (e.g. vosk-model-small-en-us-0.15) and
point config.json's "vosk_model_path" at the extracted folder to enable
the offline backend.
"""
import os
import json
import logging
import queue

import speech_recognition as sr

try:
    import vosk
    import pyaudio
    _VOSK_IMPORT_OK = True
except ImportError:
    _VOSK_IMPORT_OK = False

from PyQt6.QtCore import QThread, pyqtSignal

from config_manager import ConfigManager


def vosk_backend_available(model_path: str) -> bool:
    return _VOSK_IMPORT_OK and bool(model_path) and os.path.isdir(model_path)


class WakeWordThread(QThread):
    """Continuously listens for the configured wake word and emits wake_detected()."""

    wake_detected = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.running = True
        self.wake_word = (config.get("wake_word", default="hey cerp") or "hey cerp").lower()
        self.model_path = config.get("vosk_model_path", default="model")
        self.use_vosk = vosk_backend_available(self.model_path)
        self._sr_recognizer = sr.Recognizer()
        self._sr_recognizer.energy_threshold = config.get("energy_threshold", default=300)

    def stop(self):
        self.running = False

    def run(self):
        if self.use_vosk:
            self.status_message.emit(f"Wake word listening (offline): '{self.wake_word}'")
            self._run_vosk()
        else:
            self.status_message.emit(
                f"Wake word listening (online fallback): '{self.wake_word}' "
                f"— add a Vosk model for offline detection."
            )
            self._run_google_fallback()

    # ------------------------------------------------------------------ #
    def _run_vosk(self):
        try:
            model = vosk.Model(self.model_path)
            recognizer = vosk.KaldiRecognizer(model, 16000)
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                              input=True, frames_per_buffer=8000)
            stream.start_stream()
            logging.info("Vosk wake-word listener started.")
            while self.running:
                data = stream.read(4000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower()
                    if text and self.wake_word in text:
                        logging.info(f"Wake word detected (vosk): {text}")
                        self.wake_detected.emit()
            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception as e:
            logging.error(f"Vosk wake-word listener failed, falling back to online: {e}")
            self._run_google_fallback()

    # ------------------------------------------------------------------ #
    def _run_google_fallback(self):
        try:
            with sr.Microphone() as source:
                self._sr_recognizer.adjust_for_ambient_noise(source)
                while self.running:
                    try:
                        audio = self._sr_recognizer.listen(source, timeout=5, phrase_time_limit=3)
                        text = self._sr_recognizer.recognize_google(audio, language="en-US").lower()
                        if self.wake_word in text:
                            logging.info(f"Wake word detected (google): {text}")
                            self.wake_detected.emit()
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        logging.error(f"Speech recognition request failed: {e}")
                    except Exception as e:
                        if self.running:
                            logging.error(f"Wake-word fallback loop error: {e}")
        except Exception as e:
            logging.error(f"Wake-word fallback listener failed to start: {e}")
            self.status_message.emit(f"Wake word listener error: {e}")
