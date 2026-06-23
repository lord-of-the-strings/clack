"""
Keystroke injection via ydotool.

Provides the `KeystrokeInjector` class for sending synthesized
key events to the Linux uinput subsystem.
"""

import subprocess
import shutil
import os

class KeystrokeInjector:
    """
    Wraps calls to the `ydotool` command-line utility for character
    and key sequence injection.
    """
    
    def __init__(self):
        self.env = os.environ.copy()
        # If running as root, ydotoold usually places its socket in /tmp
        if "YDOTOOL_SOCKET" not in self.env:
            if os.path.exists("/tmp/.ydotool_socket"):
                self.env["YDOTOOL_SOCKET"] = "/tmp/.ydotool_socket"
    
    def inject_char(self, char: str):
        """Inject a single character as a keystroke via ydotool."""
        try:
            subprocess.run(['ydotool', 'type', '--', char], env=self.env, check=False)
        except Exception as e:
            print(f"Error injecting char: {e}")
        
    def inject_backspace(self):
        """Inject a backspace key sequence via ydotool."""
        try:
            subprocess.run(['ydotool', 'key', '14:1', '14:0'], env=self.env, check=False)
        except Exception as e:
            print(f"Error injecting backspace: {e}")
        
    def inject_key(self, keycode: int):
        """Inject a specific keycode via ydotool."""
        try:
            subprocess.run(['ydotool', 'key', f'{keycode}:1', f'{keycode}:0'], env=self.env, check=False)
        except Exception as e:
            print(f"Error injecting key: {e}")
        
    def check_available(self) -> bool:
        """Checks if ydotool and ydotoold are properly set up."""
        if not shutil.which('ydotool'):
            return False
        result = subprocess.run(['pgrep', 'ydotoold'], capture_output=True)
        return result.returncode == 0

