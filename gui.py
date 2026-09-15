import sys
import os
import logging
import argparse
from logging.handlers import RotatingFileHandler

from PyQt6.QtWidgets import (
    QPushButton, QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QTextEdit, QScrollArea
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from speech import SpeechProcessor
from automation import Automation
from config_manager import ConfigManager
from wake_word import WakeWordThread
from tts_feedback import TTSFeedback
from settings_dialog import SettingsDialog

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

handler = RotatingFileHandler('logs/cerp.log', maxBytes=5 * 1024 * 1024, backupCount=2)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

HIGH_CONTRAST_STYLE = """
    QMainWindow { background-color: #000000; }
    QLabel { color: #FFFFFF; }
    QTextEdit { background-color: #000000; color: #00FF00; border: 2px solid #FFFFFF; }
"""
NORMAL_STYLE = ""


class SpeechThread(QThread):
    """Runs one speech-recognition + execution cycle without freezing the UI."""
    result_signal = pyqtSignal(str, str)  # (heard_command, result)

    def __init__(self, speech_processor: SpeechProcessor):
        super().__init__()
        self.speech = speech_processor

    def run(self):
        try:
            logging.info("Speech recognition thread started.")
            heard = self.speech.listen()
            if heard.lower().startswith("error") or heard.lower().startswith("sorry"):
                self.result_signal.emit(heard, "")
            else:
                result = self.speech.process_command(heard)
                self.result_signal.emit(heard, result)
        except Exception as e:
            logging.error(f"Speech thread failed: {e}")
            self.result_signal.emit(f"Error: {str(e)}", "")


class CERPApp(QMainWindow):
    """Main GUI for CERP Voice Automation with accessibility settings."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CERP - Voice & Automation")
        self.setGeometry(100, 100, 820, 640)

        self.config = ConfigManager()
        self.auto = Automation(self.config)
        self.speech = SpeechProcessor(self.config)
        self.tts = TTSFeedback(enabled=self.config.get("ui", "tts_feedback", default=True))

        self._init_ui()
        self._apply_accessibility_settings()
        self._start_wake_word_listener()
        logging.info("CERP GUI initialized.")

    # ------------------------------------------------------------------ #
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        self.label = QLabel("CERP Voice Automation", self)
        self.label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        wake_word = self.config.get("wake_word", default="hey cerp")
        self.status_label = QLabel(f"Status: Waiting for command... Say '{wake_word}' to start.", self)
        self.status_label.setFont(QFont("Arial", 16))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.history_text = QTextEdit(self)
        self.history_text.setFont(QFont("Arial", 14))
        self.history_text.setReadOnly(True)
        self.history_text.setFixedHeight(220)
        self.history_text.setAccessibleName("Command history")
        layout.addWidget(self.history_text)

        history_button_row = QHBoxLayout()
        self.clear_history_btn = QPushButton("&Clear History", self)
        self.clear_history_btn.setStyleSheet(self._button_style("#7F8C8D", "#606B6C"))
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_button_row.addWidget(self.clear_history_btn)

        self.export_history_btn = QPushButton("&Export History", self)
        self.export_history_btn.setStyleSheet(self._button_style("#7F8C8D", "#606B6C"))
        self.export_history_btn.clicked.connect(self.export_history)
        history_button_row.addWidget(self.export_history_btn)
        layout.addLayout(history_button_row)

        button_row = QHBoxLayout()

        # Mnemonics (the '&' underlines a letter) and shortcuts below give
        # keyboard-only users a way to drive the whole app without a mouse.
        self.voice_btn = QPushButton("Use &Voice Control", self)
        self.voice_btn.setStyleSheet(self._button_style("#3498DB", "#2980B9"))
        self.voice_btn.setToolTip(f"Press to start voice control (or say '{wake_word}'). Shortcut: Ctrl+Space")
        self.voice_btn.clicked.connect(self.run_speech_recognition)
        self.voice_btn.setDefault(True)
        button_row.addWidget(self.voice_btn)

        self.settings_btn = QPushButton("&Settings", self)
        self.settings_btn.setStyleSheet(self._button_style("#8E44AD", "#71368A"))
        self.settings_btn.setToolTip("Open Settings. Shortcut: Ctrl+,")
        self.settings_btn.clicked.connect(self.open_settings)
        button_row.addWidget(self.settings_btn)

        self.quit_btn = QPushButton("&Quit", self)
        self.quit_btn.setStyleSheet(self._button_style("#E74C3C", "#C0392B"))
        self.quit_btn.setToolTip("Press to quit the application. Shortcut: Ctrl+Q")
        self.quit_btn.clicked.connect(self.close)
        button_row.addWidget(self.quit_btn)

        layout.addLayout(button_row)
        layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(scroll)

        # Tab order follows the natural top-to-bottom flow for keyboard users.
        self.setTabOrder(self.voice_btn, self.settings_btn)
        self.setTabOrder(self.settings_btn, self.quit_btn)
        self.setTabOrder(self.quit_btn, self.clear_history_btn)
        self.setTabOrder(self.clear_history_btn, self.export_history_btn)

        self._init_shortcuts()

    def _init_shortcuts(self):
        from PyQt6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Ctrl+Space"), self, activated=self.run_speech_recognition)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)

    @staticmethod
    def _button_style(color: str, hover_color: str) -> str:
        return (
            f"QPushButton {{ background-color: {color}; color: white; font-size: 18px; "
            f"padding: 15px; border-radius: 15px; }}"
            f"QPushButton:hover {{ background-color: {hover_color}; }}"
        )

    def _apply_accessibility_settings(self):
        high_contrast = self.config.get("ui", "high_contrast", default=False)
        self.setStyleSheet(HIGH_CONTRAST_STYLE if high_contrast else NORMAL_STYLE)

        scale = 1.5 if self.config.get("ui", "large_text", default=False) else 1.0
        self.label.setFont(QFont("Arial", int(24 * scale), QFont.Weight.Bold))
        self.status_label.setFont(QFont("Arial", int(16 * scale)))
        self.history_text.setFont(QFont("Arial", int(14 * scale)))

        self.tts.set_enabled(self.config.get("ui", "tts_feedback", default=True))

    # ------------------------------------------------------------------ #
    def _start_wake_word_listener(self):
        self.wake_thread = WakeWordThread(self.config)
        self.wake_thread.wake_detected.connect(self.run_speech_recognition)
        self.wake_thread.status_message.connect(lambda msg: logging.info(msg))
        self.wake_thread.start()

    def _restart_wake_word_listener(self):
        if hasattr(self, "wake_thread"):
            self.wake_thread.stop()
            self.wake_thread.wait()
        self._start_wake_word_listener()

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        self._apply_accessibility_settings()
        wake_word = self.config.get("wake_word", default="hey cerp")
        self.status_label.setText(f"Status: Waiting for command... Say '{wake_word}' to start.")
        self.voice_btn.setToolTip(f"Press to start voice control (or say '{wake_word}')")
        self._restart_wake_word_listener()

    # ------------------------------------------------------------------ #
    def run_speech_recognition(self):
        if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
            return
        self.voice_btn.setEnabled(False)
        self.voice_btn.setText("Listening...")
        self.status_label.setText("Status: Listening...")
        self.speech_thread = SpeechThread(self.speech)
        self.speech_thread.result_signal.connect(self._handle_result)
        self.speech_thread.finished.connect(lambda: self.voice_btn.setEnabled(True))
        self.speech_thread.finished.connect(lambda: self.voice_btn.setText("Use Voice Control"))
        self.speech_thread.start()

    def _handle_result(self, heard: str, result: str):
        if not result:
            # heard itself is an error/sorry message from listen()
            self.label.setText(heard)
            self.status_label.setText("Status: Error occurred.")
            self._append_history(heard, "Error occurred")
            self.tts.speak(heard)
            return

        self.label.setText(f"Heard: {heard}")
        self._append_history(heard, result)
        self.tts.speak(result)

        if "exiting application" in result.lower():
            self.status_label.setText("Status: Exiting application...")
            QApplication.quit()
            return

        self.status_label.setText("Status: Command executed.")

    def clear_history(self):
        self.history_text.clear()
        self.auto.history.clear()
        self.status_label.setText("Status: History cleared.")

    def export_history(self):
        from PyQt6.QtWidgets import QFileDialog
        default_name = f"cerp_history_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export History", default_name, "Text Files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.history_text.toPlainText())
            self.status_label.setText(f"Status: History exported to {path}")
        except Exception as e:
            logging.error(f"Failed to export history: {e}")
            self.status_label.setText("Status: Failed to export history.")

    def _append_history(self, command: str, result: str):
        self.history_text.append(f"> {command}\nResult: {result}\n")
        cursor = self.history_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.history_text.setTextCursor(cursor)

    def closeEvent(self, event):
        if hasattr(self, 'wake_thread'):
            self.wake_thread.stop()
            self.wake_thread.wait()
        if hasattr(self, 'tts'):
            self.tts.shutdown()
        event.accept()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CERP Voice Automation")
    parser.add_argument('--minimized', action='store_true', help="Start the application minimized")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = CERPApp()
    if args.minimized:
        window.showMinimized()
    else:
        window.show()
    sys.exit(app.exec())
