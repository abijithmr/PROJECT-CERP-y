"""Text-to-speech feedback for command results.

Speaks results on a dedicated background thread with its own pyttsx3
engine instance (pyttsx3 engines are not safe to share across threads),
so the GUI never blocks while CERP talks back — important for users who
rely on audio confirmation rather than reading the screen.
"""
import logging
import queue
import threading

try:
    import pyttsx3
    _PYTTSX3_OK = True
except ImportError:
    _PYTTSX3_OK = False


class TTSFeedback:
    def __init__(self, enabled: bool = True, rate: int = 175):
        self.enabled = enabled and _PYTTSX3_OK
        if not _PYTTSX3_OK:
            logging.warning("pyttsx3 not installed; TTS feedback disabled.")
        self.rate = rate
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        if self.enabled:
            self._thread.start()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled and _PYTTSX3_OK

    def speak(self, text: str):
        if not self.enabled or not text:
            return
        self._queue.put(text)

    def _worker(self):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
        except Exception as e:
            logging.error(f"TTS engine failed to initialize ({e}); disabling TTS feedback.")
            self.enabled = False
            return
        while not self._stop.is_set():
            try:
                text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logging.error(f"TTS speak failed: {e}")

    def shutdown(self):
        self._stop.set()
