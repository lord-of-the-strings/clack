import subprocess
import threading
import shutil
import time
import os
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

class FocusWatcher:
    """
    Detects when the target application loses focus, triggering auto-pause.
    Supports X11 (xdotool), Sway, and Hyprland.
    """
    def __init__(self):
        self.target_window_id = None
        self._stop_event = threading.Event()
        self._thread = None
        self._callback = None
        self._backend = "none"
        
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session == "x11" and shutil.which("xdotool"):
            self._backend = "xdotool"
        elif session == "wayland":
            if os.environ.get("SWAYSOCK") and shutil.which("swaymsg"):
                self._backend = "sway"
            elif os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
                self._backend = "hyprland"
                
        if self._backend == "none" and shutil.which("xdotool"):
            self._backend = "xdotool" # fallback

    def _get_active_window(self):
        if self._backend == "xdotool":
            try:
                res = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
                if res.returncode == 0: return res.stdout.strip()
            except Exception: pass
        elif self._backend == "sway":
            try:
                import json
                res = subprocess.run(['swaymsg', '-t', 'get_tree'], capture_output=True, text=True)
                if res.returncode == 0:
                    tree = json.loads(res.stdout)
                    def find_focused(node):
                        if node.get("focused"): return str(node.get("id"))
                        for c in node.get("nodes", []) + node.get("floating_nodes", []):
                            f = find_focused(c)
                            if f: return f
                        return None
                    return find_focused(tree)
            except Exception: pass
        elif self._backend == "hyprland":
            try:
                import json
                res = subprocess.run(['hyprctl', 'activewindow', '-j'], capture_output=True, text=True)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    return data.get("address")
            except Exception: pass
        return None

    def record_target_window(self) -> str:
        self.target_window_id = self._get_active_window()
        return self.target_window_id

    def wait_for_switch(self, on_switched_callback):
        if self._backend == "none":
            GLib.idle_add(on_switched_callback)
            return

        self.record_target_window()
        initial_window = self.target_window_id
        
        self.stop()
        self._stop_event.clear()
        
        def _poll_switch():
            while not self._stop_event.is_set():
                current = self._get_active_window()
                if current and current != initial_window:
                    self.target_window_id = current
                    GLib.idle_add(on_switched_callback)
                    break
                time.sleep(0.1)

        self._thread = threading.Thread(target=_poll_switch, daemon=True)
        self._thread.start()

    def start(self, on_focus_lost) -> bool:
        if self._backend == "none": return False
        
        self.stop()
        self._callback = on_focus_lost
        self._stop_event.clear()
        
        if self.target_window_id is None:
            return False
            
        self._thread = threading.Thread(target=self._poll_focus_loss, daemon=True)
        self._thread.start()
        return True
        
    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            if self._thread != threading.current_thread():
                self._thread.join(timeout=1.0)
            
    def _poll_focus_loss(self):
        while not self._stop_event.is_set():
            current = self._get_active_window()
            if current and current != self.target_window_id:
                if self._callback:
                    GLib.idle_add(self._callback)
                break
            time.sleep(0.2)
