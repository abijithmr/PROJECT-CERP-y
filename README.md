<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&reversal=true&color=0:0B6E4F,55:14B8A6,100:84CC16&height=230&section=header&text=CERP-Y&fontSize=84&fontColor=ffffff&fontAlignY=36&animation=blinking&desc=Hands-free%20computer%20control%20for%20people%20with%20motor%20disabilities&descSize=18&descAlignY=58" width="100%" alt="CERP-Y"/>

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=20&duration=2200&pause=700&color=14B8A6&center=true&vCenter=true&width=560&height=45&lines=%3E+hey+cerp;%3E+open+notepad;%3E+set+volume+to+40;%3E+take+a+screenshot;%3E+start+voice+typing;%3E+shutdown...+confirm+shutdown" alt="Terminal-style animation of voice commands"/>

**Say "hey cerp", then say what you want. It does it and tells you out loud what happened.**

![Python](https://img.shields.io/badge/python-3.12+-0B6E4F?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-14B8A6?style=flat-square&logo=qt&logoColor=white)
![Vosk](https://img.shields.io/badge/wake_word-Vosk_offline-84CC16?style=flat-square)
![TTS](https://img.shields.io/badge/spoken_feedback-pyttsx3-0B6E4F?style=flat-square)
![Windows](https://img.shields.io/badge/best_on-Windows-14B8A6?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-64748B?style=flat-square)

[Cheat sheet](#voice-command-cheat-sheet) &nbsp;·&nbsp; [How it works](#how-it-fits-together) &nbsp;·&nbsp; [Get started](#getting-started) &nbsp;·&nbsp; [Configuration](#configuration)

</div>

Open an app, change the volume, take a screenshot, or dictate a whole document without touching a mouse or keyboard.

> [!NOTE]
> Volume, brightness and process tracking need **Windows**. Opening apps, screenshots, lock, sleep and shutdown also have best-effort macOS and Linux fallbacks.

---

## Contents

- [What it does](#what-it-does)
- [Voice command cheat sheet](#voice-command-cheat-sheet)
- [How it fits together](#how-it-fits-together)
- [Accessibility](#accessibility)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributors](#contributors)
- [License](#license)

---

## What it does

| Area | Highlights |
|:-----|:-----------|
| **Apps** | Open and close Notepad, Calculator, Chrome, Word, Excel, PowerPoint, plus web apps like Gmail, YouTube, Instagram and Google |
| **System** | Volume and brightness (relative or exact), scrolling, screenshots, lock, sleep, and a two-step shutdown |
| **Dictation** | Continuous voice typing into Notepad with spoken punctuation |
| **Status** | Battery, time, internet, CPU and memory on request |
| **Custom commands** | Map any phrase to a local file or URL from the Settings dialog |
| **Repeat** | Say "repeat" to run the last successful command again |
| **History** | View, clear or export your command history to a `.txt` file |

Commands are matched with ordered regular expressions, so phrasing is flexible ("increase", "raise" and "turn up" all work) instead of relying on exact prefixes.

---

## Voice command cheat sheet

<details open>
<summary><b>System controls</b></summary>

| Say | Result |
|:----|:-------|
| "set volume to 40" | Sets volume to 40% |
| "increase volume" / "turn down volume" | Nudges volume up or down |
| "set brightness to 70" | Sets brightness to 70% |
| "increase brightness" / "lower brightness" | Nudges brightness up or down |
| "scroll up" / "scroll down" | Scrolls the active window |
| "take a screenshot" | Captures the screen |
| "lock the screen" | Locks the computer |
| "sleep" | Puts the computer to sleep |
| "shutdown", then "confirm shutdown" or "cancel shutdown" | Shuts down only after you confirm |
| "system status" | Reads out battery, time, internet, CPU and memory |

</details>

<details open>
<summary><b>Apps and media</b></summary>

| Say | Result |
|:----|:-------|
| "open notepad" | Launches the app |
| "open youtube" | Opens the site in your browser |
| "close chrome" | Closes the app |
| "skip shorts" / "skip next" | Skips to the next short or item |
| "exit" / "quit application" | Closes CERP-y |

</details>

<details>
<summary><b>Voice typing</b></summary>

Say **"start voice typing"** and speak normally. Say **"stop voice typing"** to finish.

Spoken punctuation is converted as you go: "comma", "period", "question mark", "new line", "new paragraph" and more.

</details>

<details>
<summary><b>Meta commands</b></summary>

| Say | Result |
|:----|:-------|
| "repeat" / "repeat that" | Runs the last successful command again |
| Any phrase you added in Settings | Opens the file or URL you mapped to it |

</details>

---

## How it fits together

```mermaid
flowchart LR
    A[Wake word<br/>Vosk or Google] --> B[Speech capture<br/>speech.py]
    B --> C[Automation<br/>regex command router]
    C --> D[Platform utils<br/>volume, lock, apps]
    C --> E[TTS feedback<br/>spoken result]
    F[config.json] --> C
    G[PyQt6 GUI] --> A
    G --> H[Settings dialog]
    H --> F
```

1. The **wake word** listener waits for "hey cerp". It runs offline with Vosk when a model is available and falls back to online Google recognition otherwise.
2. **Speech capture** turns what you say into text.
3. **Automation** matches the text against its command patterns and runs the right handler.
4. **Platform utils** does the actual system work on Windows, macOS or Linux.
5. **TTS feedback** reads the result back to you without blocking the app.

---

## Accessibility

CERP-y is built around people who cannot rely on a mouse or keyboard, and it still works for those who can.

- **Spoken confirmation** of every command result (can be turned off)
- **High-contrast mode** and **large-text mode**
- **Adjustable listening timeout** and **microphone sensitivity**
- **Live Settings dialog**, so nothing requires editing files
- **Full keyboard navigation**: button mnemonics, a sensible tab order and global shortcuts

| Shortcut | Action |
|:---------|:-------|
| `Ctrl` + `Space` | Start voice control |
| `Ctrl` + `,` | Open Settings |
| `Ctrl` + `Q` | Quit |

---

## Getting started

**Requirements**

- Python 3.12 or newer
- A working microphone
- *(Optional)* a [Vosk model](https://alphacephei.com/vosk/models) such as `vosk-model-small-en-us-0.15` for offline wake-word detection

**Install and run**

```sh
git clone https://github.com/dgkingsway/PROJECT-CERP-y.git
cd PROJECT-CERP-y
pip install -r requirements.txt
python gui.py
```

**Turn on offline wake word (optional)**

1. Download and unzip a Vosk model.
2. Set `vosk_model_path` in `config.json` to the model folder.

Without a model, CERP-y still works and uses online recognition for the wake word.

---

## Configuration

Everything lives in `config.json`, which is created with defaults on first run. You can also change all of it from the in-app **Settings** dialog.

| Key | Purpose | Default |
|:----|:--------|:--------|
| `wake_word` | Phrase that starts listening | `"hey cerp"` |
| `listen_timeout` | Seconds to wait for speech | `5` |
| `phrase_time_limit` | Max seconds per phrase | `5` |
| `energy_threshold` | Microphone sensitivity | `300` |
| `vosk_model_path` | Folder of the offline model | `"model"` |
| `ui.high_contrast` | High-contrast theme | `false` |
| `ui.large_text` | Larger interface text | `false` |
| `ui.tts_feedback` | Spoken confirmations | `true` |
| `app_paths` | App name to executable path | Notepad, Calculator, Chrome, Office |
| `web_apps` | Name to URL | Gmail, YouTube, Instagram, Google |
| `custom_commands` | Your own phrase to path or URL | `{}` |

> [!TIP]
> A missing or corrupt `config.json` is not a problem. CERP-y falls back to built-in defaults instead of failing to start.

---

## Testing

```sh
python -m unittest discover -s tests -v
```

The suite covers command parsing, volume and brightness commands, dictation punctuation and configuration loading.

---

## Project layout

```text
PROJECT-CERP-y/
├── gui.py               PyQt6 main window and shortcuts
├── settings_dialog.py   In-app settings and accessibility options
├── automation.py        Command patterns and handlers
├── speech.py            Microphone capture, passes text to Automation
├── wake_word.py         Offline (Vosk) or online wake-word listener
├── tts_feedback.py      Non-blocking spoken feedback
├── platform_utils.py    Windows / macOS / Linux system helpers
├── config_manager.py    Load, validate and save config.json
├── config.json          User-editable settings
├── tests/               Unit tests
├── logs/                Runtime logs (git-ignored)
├── CHANGELOG.md
└── requirements.txt
```

---

## Known limitations

- Volume and brightness control require Windows (`pycaw`, `WMI`); other systems depend on tools such as `amixer`, `brightnessctl` and `loginctl` being installed.
- Voice typing targets Notepad.
- `PyAudio` can be tricky to install on some systems. If `pip` fails, install your platform's PortAudio package first.

See [`CHANGELOG.md`](CHANGELOG.md) for what has changed so far.

---

## Roadmap

- [ ] Auto-start on boot
- [ ] Gesture recognition and eye-tracking support
- [ ] Multiple named command profiles

---

## Contributors

| Name | GitHub |
|:-----|:-------|
| dgkingsway | [@dgkingsway](https://github.com/dgkingsway) |
| dark blind | |
| abijithmr | [@abijithmr](https://github.com/abijithmr) |
| alan kj | [@ala527](https://github.com/ala527) |
| AlwinJCOde667 | [@AlwinJCOde667](https://github.com/AlwinJCOde667) |

Questions or ideas? Open a [GitHub issue](https://github.com/dgkingsway/PROJECT-CERP-y/issues) or email [dgkingsway@gmail.com](mailto:dgkingsway@gmail.com).

---

## License

Released under the [MIT License](LICENSE).

> [!IMPORTANT]
> This project is not affiliated with any other "CERP" projects.

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&reversal=true&color=0:84CC16,55:14B8A6,100:0B6E4F&height=110&section=footer" width="100%" alt=""/>

</div>
