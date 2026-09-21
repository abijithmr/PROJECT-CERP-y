# CERP-y - Computer Automation for Disabled People Using Python

## Overview
CERP is a voice-activated automation tool for assisting individuals with motor disabilities in operating a computer more efficiently. Voice commands, automation, and accessibility settings work together to reduce reliance on a mouse/keyboard.

## Features

### Core Automation
- Open/close applications (Notepad, Calculator, Chrome, Word, Excel, PowerPoint) and web apps (Gmail, YouTube, Instagram, Google) — configurable in `config.json` or via Settings
- Custom voice commands: map any name to a local path or URL from the GUI's Settings dialog
- Volume control (relative up/down, or "set volume to N")
- Brightness control (relative up/down, or "set brightness to N")
- Scroll up/down, screenshot, lock screen, sleep, shutdown (two-step voice-confirmed), skip Shorts/next content
- System status (battery, time, internet, CPU, memory)
- Continuous voice typing into Notepad ("start/stop voice typing") with spoken punctuation ("comma", "period", "question mark", "new line", "new paragraph", ...)
- "Repeat" replays the last successfully executed command
- Command history: view, clear, or export to a `.txt` file from the GUI

### Voice Control & Wake Word
- Wake word (default "hey cerp", configurable) triggers listening
- **Offline** detection via Vosk when a model is configured (`vosk_model_path` in `config.json`); automatically falls back to online Google Speech Recognition if no Vosk model is present
- Command parsing is pattern-based (`automation.py: COMMAND_PATTERNS`) rather than fragile prefix matching

### Accessibility
- Spoken (TTS) confirmation of every command result, toggleable
- High-contrast mode and large-text mode
- Adjustable listening timeout and microphone sensitivity
- All settings editable live from the in-app Settings dialog (no file editing required)
- Keyboard-only navigation: mnemonics on every button, explicit tab order, and shortcuts (Ctrl+Space voice control, Ctrl+, settings, Ctrl+Q quit)

### GUI
- PyQt6 interface with scrollable layout, live history log, and a Settings panel

## Installation

### Prerequisites
- Python 3.12+
- `pip install -r requirements.txt`
- (Optional, for offline wake-word) Download a Vosk model, e.g. `vosk-model-small-en-us-0.15`, unzip it, and set `"vosk_model_path"` in `config.json` to its folder path. Without this, CERP still works using online recognition for the wake word.
- Windows is required for volume, brightness (needs `pywin32`/`wmi`), and process-tracking features; app-opening, screenshot, lock/sleep/shutdown have macOS/Linux fallbacks in `platform_utils.py` (best-effort, depends on installed system tools like `amixer`/`brightnessctl`/`loginctl`).

### Setup
```sh
git clone https://github.com/dgkingsway/PROJECT-CERP-y.git
cd PROJECT-CERP-y
pip install -r requirements.txt
python gui.py
```

## Usage
- Say the configured wake word (default **"hey cerp"**) or click "Use Voice Control".
- Example commands: "open notepad", "increase volume", "set volume to 40", "system status", "scroll down", "take a screenshot", "lock the screen", "shutdown" then "confirm shutdown" or "cancel shutdown".
- Open **Settings** to add custom commands, change the wake word, toggle high-contrast/large-text/TTS, and tune listening sensitivity/timeout.

## Configuration
All behavior-affecting settings live in `config.json` (created with sane defaults on first run) and can also be edited from the GUI:
```json
{
  "wake_word": "hey cerp",
  "listen_timeout": 5,
  "energy_threshold": 300,
  "vosk_model_path": "model",
  "ui": { "high_contrast": false, "large_text": false, "tts_feedback": true },
  "app_paths": { "...": "..." },
  "web_apps": { "...": "..." },
  "custom_commands": {}
}
```
A missing or corrupt `config.json` automatically falls back to built-in defaults — the app never fails to start because of it.

## Testing
```sh
python -m unittest discover -s tests -v
```

## Project Structure
```
PROJECT-CERP-y/
├── automation.py        # Command parsing + execution
├── config_manager.py    # Load/save/validate config.json
├── config.json           # User-editable settings
├── gui.py                # PyQt6 main window
├── settings_dialog.py    # Accessibility & config UI
├── speech.py             # Mic capture -> Automation
├── platform_utils.py     # Cross-platform system-control helpers
├── wake_word.py          # Offline (Vosk) / online wake-word listener
├── tts_feedback.py       # Spoken result confirmation
├── requirements.txt
├── tests/
│   ├── test_automation.py
│   └── test_config_manager.py
└── logs/
```

## Future Enhancements
- Auto-start on boot
- Gesture recognition / eye-tracking support
- Multiple named command profiles

## Contributors
- **[abijithmr](https://github.com/abijithmr)**
- **[alankj](https://github.com/alan-kj)**
- **[AlwinJCOde667](https://github.com/AlwinJCOde667)**

Want to contribute? Check out our [Contributing Guidelines](CONTRIBUTING.md).

## License
This project is licensed under the [MIT License](LICENSE).

## Contact
For questions or suggestions, reach out via GitHub Issues or email [dgkingsway@gmail.com](mailto:dgkingsway@gmail.com).

> ⚠️ **Disclaimer:** This project is not affiliated with any other "CERP" projects.
