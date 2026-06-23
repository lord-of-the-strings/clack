import sys
import time
import os

# Force pynput to use the udev (evdev) backend to bypass Wayland/X11 focus issues
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.pop("XDG_SESSION_TYPE", None)
os.environ["PYNPUT_BACKEND"] = "udev"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m gui.listener <start_pause_shortcut>")
        sys.exit(1)
        
    start_shortcut = sys.argv[1]
    
    try:
        from pynput import keyboard
    except ImportError:
        print("ERROR: pynput not installed")
        sys.exit(1)

    def on_start_pause():
        print("START_PAUSE", flush=True)

    hotkeys = {
        start_shortcut: on_start_pause
    }

    try:
        with keyboard.GlobalHotKeys(hotkeys) as h:
            h.join()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
