"""Cross-platform system-control helpers.

automation.py delegates OS-specific work here so that Windows-only
dependencies (pycaw/comtypes) are only imported/used on Windows, and
macOS/Linux get functional (if reduced) equivalents instead of a crash.
"""
import platform
import subprocess
import shutil
import webbrowser
import logging
import os

SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"


def open_target(target: str) -> None:
    """Open a local executable path via subprocess.Popen (caller tracks the process)."""
    if SYSTEM == "Windows":
        subprocess.Popen(target)
    elif SYSTEM == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen([target] if os.path.isabs(target) else ["xdg-open", target])


def open_url(url: str) -> None:
    webbrowser.open(url)


def adjust_volume(change_percent: float) -> float:
    """Adjust system volume by change_percent (-100..100). Returns new volume 0..1, or -1 if unsupported."""
    try:
        if SYSTEM == "Windows":
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current = volume.GetMasterVolumeLevelScalar()
            new_volume = max(0.0, min(1.0, current + (change_percent / 100)))
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            return new_volume
        elif SYSTEM == "Darwin":
            # AppleScript operates on 0-100 scale directly; approximate a relative change.
            get = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True, text=True, check=True
            )
            current = int(get.stdout.strip())
            new_volume = max(0, min(100, current + int(change_percent)))
            subprocess.run(["osascript", "-e", f"set volume output volume {new_volume}"], check=True)
            return new_volume / 100
        else:  # Linux
            if shutil.which("amixer"):
                direction = "+" if change_percent >= 0 else "-"
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", f"{abs(int(change_percent))}%{direction}"],
                    check=True, capture_output=True
                )
                return -1  # amixer doesn't cleanly return scalar volume here
            logging.warning("amixer not found; cannot adjust volume on this Linux system.")
            return -1
    except Exception as e:
        logging.error(f"adjust_volume failed on {SYSTEM}: {e}")
        return -1


def set_brightness(level_percent: int) -> bool:
    """Set screen brightness 0-100. Best-effort; not all platforms/hardware supported."""
    try:
        if SYSTEM == "Windows":
            import wmi  # optional dependency, only needed for this feature
            c = wmi.WMI(namespace="wmi")
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(level_percent, 0)
            return True
        elif SYSTEM == "Linux" and shutil.which("brightnessctl"):
            subprocess.run(["brightnessctl", "set", f"{level_percent}%"], check=True, capture_output=True)
            return True
        else:
            logging.warning(f"Brightness control not supported on {SYSTEM} without extra tooling.")
            return False
    except Exception as e:
        logging.error(f"set_brightness failed: {e}")
        return False


def lock_screen() -> bool:
    try:
        if SYSTEM == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
        elif SYSTEM == "Darwin":
            subprocess.run(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"],
                check=True
            )
        else:
            if shutil.which("loginctl"):
                subprocess.run(["loginctl", "lock-session"], check=True)
            elif shutil.which("xdg-screensaver"):
                subprocess.run(["xdg-screensaver", "lock"], check=True)
            else:
                return False
        return True
    except Exception as e:
        logging.error(f"lock_screen failed: {e}")
        return False


def sleep_system() -> bool:
    try:
        if SYSTEM == "Windows":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
        elif SYSTEM == "Darwin":
            subprocess.run(["pmset", "sleepnow"], check=True)
        else:
            if shutil.which("systemctl"):
                subprocess.run(["systemctl", "suspend"], check=True)
            else:
                return False
        return True
    except Exception as e:
        logging.error(f"sleep_system failed: {e}")
        return False


def shutdown_system(delay_seconds: int = 5) -> bool:
    """Shut down the machine after delay_seconds (gives the user a window to cancel)."""
    try:
        if SYSTEM == "Windows":
            subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)], check=True)
        elif SYSTEM == "Darwin":
            subprocess.run(["sudo", "shutdown", "-h", f"+{max(1, delay_seconds // 60)}"], check=True)
        else:
            subprocess.run(["shutdown", "-h", f"+{max(1, delay_seconds // 60)}"], check=True)
        return True
    except Exception as e:
        logging.error(f"shutdown_system failed: {e}")
        return False


def cancel_shutdown() -> bool:
    try:
        if SYSTEM == "Windows":
            subprocess.run(["shutdown", "/a"], check=True)
        else:
            subprocess.run(["shutdown", "-c"], check=True)
        return True
    except Exception as e:
        logging.error(f"cancel_shutdown failed: {e}")
        return False


def take_screenshot(save_path: str) -> bool:
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(save_path)
        return True
    except Exception as e:
        logging.error(f"take_screenshot failed: {e}")
        return False
