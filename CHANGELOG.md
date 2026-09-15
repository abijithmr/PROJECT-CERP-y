# Changelog

## Unreleased — Improvement Pass 2

### Added
- Brightness control restored/implemented as actual commands: `set brightness to N`, `increase brightness`, `decrease brightness` (README previously claimed this but no code existed for it)
- Dictation punctuation: `apply_dictation_punctuation()` converts spoken words ("comma", "period", "question mark", "new line", "new paragraph", etc.) into literal punctuation during voice typing
- GUI: Clear History and Export History (to `.txt`) buttons
- GUI keyboard navigation: mnemonics (Alt+underlined-letter) on all buttons, explicit tab order, and global shortcuts (Ctrl+Space = voice control, Ctrl+, = settings, Ctrl+Q = quit)
- 9 new unit tests covering brightness commands and dictation punctuation (word-boundary safety, case-insensitivity, no-op on plain text)

## Unreleased — Improvement Pass 1

### Added
- `config.json` + `config_manager.py`: externalized, validated, self-healing configuration (corrupt/missing file falls back to defaults instead of crashing)
- `platform_utils.py`: cross-platform system control (Windows/macOS/Linux) for volume, brightness, lock, sleep, shutdown, screenshot
- `wake_word.py`: real offline wake-word detection via Vosk, with automatic fallback to online recognition
- `tts_feedback.py`: non-blocking spoken confirmation of command results
- `settings_dialog.py`: in-app Settings panel (high-contrast, large text, TTS toggle, wake word, listen timeout, mic sensitivity, custom commands)
- New voice commands: `scroll up/down`, `take a screenshot`, `lock screen`, `sleep`, `shutdown` / `confirm shutdown` / `cancel shutdown` (two-step confirmation), `repeat`, `set volume to N`
- Custom commands: map any voice phrase to a local path or URL from Settings
- `requirements.txt`, `.gitignore`
- `tests/test_automation.py`, `tests/test_config_manager.py` (27 unit tests)

### Changed
- `automation.py`: command parsing rewritten from fragile `str.startswith` prefix matching to ordered regex patterns (`COMMAND_PATTERNS`); app/web app lists now sourced from `config_manager` instead of hardcoded dicts
- `gui.py`: wake-word listening now uses `WakeWordThread` (Vosk/online) instead of the old ad-hoc "say hello" Google-only listener; added Settings button and TTS wiring; accessibility styling applied on load and on settings change
- `speech.py`: removed the redundant/inconsistent second command-dispatch table — `SpeechProcessor` now just captures audio and hands text straight to `Automation.execute_task`
- `README.md`: rewritten to describe what's actually implemented (previous version described unimplemented Whisper/Porcupine wake-word support)

### Fixed
- Regex capturing groups that were incorrectly forwarded as positional args to no-arg handlers (e.g. `repeat`, `exit`, `screenshot`, `lock screen`, `sleep`, `volume up/down`), which previously raised `TypeError`
- `close`/`quit <app>` no longer collides with `quit application` (exit) due to pattern ordering
- TTS worker now fails gracefully (disables itself) if no TTS engine/driver is available on the host instead of crashing its thread

### Removed
- `tempCodeRunnerFile.py` (stale scratch copy of an old `gui.py`)
- Committed `logs/cerp.log` (kept the `logs/` directory via `.gitkeep`; log file is now gitignored)
