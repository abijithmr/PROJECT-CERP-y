from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSlider,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from config_manager import ConfigManager


class SettingsDialog(QDialog):
    """Accessibility & behavior settings: contrast, text size, TTS,
    listening sensitivity/timeout, and custom voice commands.
    """

    settings_changed = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("CERP Settings")
        self.setMinimumWidth(420)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Accessibility group ---
        access_group = QGroupBox("Accessibility")
        access_layout = QVBoxLayout()
        self.high_contrast_cb = QCheckBox("High-contrast mode")
        self.large_text_cb = QCheckBox("Large text")
        self.tts_cb = QCheckBox("Speak command results out loud (TTS)")
        access_layout.addWidget(self.high_contrast_cb)
        access_layout.addWidget(self.large_text_cb)
        access_layout.addWidget(self.tts_cb)
        access_group.setLayout(access_layout)
        layout.addWidget(access_group)

        # --- Listening group ---
        listen_group = QGroupBox("Voice Listening")
        listen_form = QFormLayout()

        self.wake_word_edit = QLineEdit()
        listen_form.addRow("Wake word:", self.wake_word_edit)

        self.timeout_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeout_slider.setRange(2, 15)
        self.timeout_value_label = QLabel()
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(self.timeout_slider)
        timeout_row.addWidget(self.timeout_value_label)
        listen_form.addRow("Listen timeout (s):", timeout_row)
        self.timeout_slider.valueChanged.connect(
            lambda v: self.timeout_value_label.setText(f"{v}s")
        )

        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(50, 1000)
        self.sensitivity_value_label = QLabel()
        sens_row = QHBoxLayout()
        sens_row.addWidget(self.sensitivity_slider)
        sens_row.addWidget(self.sensitivity_value_label)
        listen_form.addRow("Mic sensitivity:", sens_row)
        self.sensitivity_slider.valueChanged.connect(
            lambda v: self.sensitivity_value_label.setText(str(v))
        )

        listen_group.setLayout(listen_form)
        layout.addWidget(listen_group)

        # --- Custom commands group ---
        custom_group = QGroupBox("Custom Voice Commands")
        custom_layout = QVBoxLayout()
        self.custom_list = QListWidget()
        custom_layout.addWidget(self.custom_list)

        add_row = QHBoxLayout()
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("Command name (e.g. 'spotify')")
        self.custom_target_edit = QLineEdit()
        self.custom_target_edit.setPlaceholderText("Path or URL")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_custom_command)
        add_row.addWidget(self.custom_name_edit)
        add_row.addWidget(self.custom_target_edit)
        add_row.addWidget(add_btn)
        custom_layout.addLayout(add_row)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected_custom_command)
        custom_layout.addWidget(remove_btn)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # --- Buttons ---
        button_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

    def _load_values(self):
        self.high_contrast_cb.setChecked(bool(self.config.get("ui", "high_contrast", default=False)))
        self.large_text_cb.setChecked(bool(self.config.get("ui", "large_text", default=False)))
        self.tts_cb.setChecked(bool(self.config.get("ui", "tts_feedback", default=True)))
        self.wake_word_edit.setText(str(self.config.get("wake_word", default="hey cerp")))
        self.timeout_slider.setValue(int(self.config.get("listen_timeout", default=5)))
        self.sensitivity_slider.setValue(int(self.config.get("energy_threshold", default=300)))

        self.custom_list.clear()
        for name, target in self.config.custom_commands.items():
            self.custom_list.addItem(QListWidgetItem(f"{name} -> {target}"))

    def _add_custom_command(self):
        name = self.custom_name_edit.text().strip()
        target = self.custom_target_edit.text().strip()
        if not name or not target:
            QMessageBox.warning(self, "Missing info", "Enter both a command name and a path/URL.")
            return
        self.config.add_custom_command(name, target)
        self.custom_list.addItem(QListWidgetItem(f"{name.lower()} -> {target}"))
        self.custom_name_edit.clear()
        self.custom_target_edit.clear()

    def _remove_selected_custom_command(self):
        item = self.custom_list.currentItem()
        if not item:
            return
        name = item.text().split(" -> ")[0]
        self.config.remove_custom_command(name)
        self.custom_list.takeItem(self.custom_list.row(item))

    def _save_and_close(self):
        self.config.set(self.high_contrast_cb.isChecked(), "ui", "high_contrast")
        self.config.set(self.large_text_cb.isChecked(), "ui", "large_text")
        self.config.set(self.tts_cb.isChecked(), "ui", "tts_feedback")
        self.config.set(self.wake_word_edit.text().strip().lower() or "hey cerp", "wake_word")
        self.config.set(self.timeout_slider.value(), "listen_timeout")
        self.config.set(self.sensitivity_slider.value(), "energy_threshold")
        self.config.save()
        self.settings_changed.emit()
        self.accept()
