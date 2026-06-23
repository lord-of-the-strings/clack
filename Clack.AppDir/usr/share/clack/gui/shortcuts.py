import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
import re
import subprocess
import threading

class ShortcutManager:
    """
    Manages global shortcuts for start/pause and speed boost.
    Uses a background root evdev listener to bypass Wayland restrictions.
    """
    def __init__(self, start_callback, speed_callback_on, speed_callback_off):
        self.start_callback = start_callback
        self.speed_callback_on = speed_callback_on
        self.speed_callback_off = speed_callback_off
        self.listener_process = None
        self.listener_thread = None
        
    def register(self, shortcut_str: str, speed_str: str):
        # Global shortcuts are currently disabled (Work in Progress)
        return
        
        # try:
        #     if self.listener_process:
        #         self.listener_process.terminate()
        #         self.listener_process = None
        #         
        #     # Convert UI strings (e.g. "Ctrl+Shift+F12") to pynput format ("<ctrl>+<shift>+<f12>")
        #     pynput_shortcut = shortcut_str.lower().replace("ctrl", "<ctrl>").replace("shift", "<shift>").replace("alt", "<alt>")
        #     pynput_shortcut = re.sub(r'\b(f\d{1,2})\b', r'<\1>', pynput_shortcut)
        #     
        #     cmd = ["sudo", "-S", "python3", "-m", "gui.listener", pynput_shortcut]
        #     
        #     self.listener_process = subprocess.Popen(
        #         cmd,
        #         stdin=subprocess.PIPE,
        #         stdout=subprocess.PIPE,
        #         stderr=subprocess.PIPE,
        #         text=True,
        #         bufsize=1
        #     )
        #     
        #     # Write sudo password to stdin
        #     self.listener_process.stdin.write("741852963\n")
        #     self.listener_process.stdin.flush()
        #     
        #     def read_loop(proc):
        #         while True:
        #             line = proc.stdout.readline()
        #             if not line:
        #                 break
        #             if line.strip() == "START_PAUSE":
        #                 GLib.idle_add(self.start_callback)
        #                 
        #     self.listener_thread = threading.Thread(target=read_loop, args=(self.listener_process,), daemon=True)
        #     self.listener_thread.start()
        #     
        #     print(f"Registered global shortcut via root listener: {shortcut_str} -> {pynput_shortcut}")
        #     
        # except Exception as e:
        #     print(f"WARNING: Global shortcuts failed to bind: {e}")
            
    def _on_start_pause(self):
        GLib.idle_add(self.start_callback)


