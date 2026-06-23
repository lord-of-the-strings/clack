import subprocess
import threading
import signal
import sys
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

from .injector import KeystrokeInjector
from .state import ClackState
from .focus_watcher import FocusWatcher

class ClackRunner:
    """
    Manages the `clack` CLI subprocess and background reader threads.
    """
    def __init__(self):
        self.process = None
        self.injector = KeystrokeInjector()
        self.state = None
        self._stop_event = None
        self.stdout_thread = None
        self.stderr_thread = None
        self.focus_watcher = FocusWatcher()
        
    def build_command(self, state: ClackState) -> list[str]:
        cmd = ["clack", "--state-output"]
        cmd.extend(["--wpm", str(state.wpm)])
        
        if state.correct_all_mistakes:
            cmd.extend(["--correction-rate", "1.0"])
        else:
            cmd.extend(["--correction-rate", str(state.correction_rate)])
            
        cmd.extend(["--error-rate", str(state.error_rate)])
        cmd.extend(["--jitter", str(state.jitter)])
        if state.no_fatigue:
            cmd.append("--no-fatigue")
            
        session_len = max(500, state.session_length)
        cmd.extend(["--session-length", str(session_len)])
        cmd.extend(["--thinking-pause-prob", str(state.thinking_pause_prob)])
        cmd.extend(["--max-pause", str(state.max_pause)])
        

        if state.seed is not None:
            cmd.extend(["--seed", str(state.seed)])
            
        return cmd

    def start(self, text: str, state: ClackState):
        self.state = state
        self.state.is_typing = True
        self.state.is_paused = False
        self._stop_event = threading.Event()
        
        cmd = self.build_command(state)
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.stdout_thread = threading.Thread(target=self._stdout_reader_thread, args=(self.process, self._stop_event), daemon=True)
        self.stderr_thread = threading.Thread(target=self._stderr_reader_thread, args=(self.process, self._stop_event), daemon=True)
        self.stdout_thread.start()
        
        # BUG-10: Start focus watcher AFTER subprocess exists
        self.focus_watcher.start(self._on_auto_paused)
        self.stderr_thread.start()
        
        # Write text to stdin and close it
        self.process.stdin.write(text.encode('utf-8'))
        self.process.stdin.close()
        
    def _on_auto_paused(self):
        self.pause()
        GLib.idle_add(self._ui_auto_paused)

    def pause(self):
        self.focus_watcher.stop()
        self._stop_event.set()
        self.state.is_typing = False
        self.state.is_paused = True
        if not self.process:
            return
            
        self.process.terminate()
        
        # Reap in background to avoid blocking GUI and avoid GLib child_watch warning
        def _reap(p):
            p.wait()
        threading.Thread(target=_reap, args=(self.process,), daemon=True).start()
        self.process = None

    def resume(self):
        if not self.state or not self.state.is_paused: return
        # Restart with remaining text
        remaining_text = self.state.original_text[self.state.pause_position:]
        self.start(remaining_text, self.state)
        
    def _ui_update_progress(self, progress: float):
        pass
        
    def _ui_update_state(self, state_str: str):
        pass
        
    def _ui_complete(self):
        pass
        
    def _ui_auto_paused(self):
        pass

    def _ui_correction(self):
        pass

    def _ui_error(self, message: str):
        pass

    def _stdout_reader_thread(self, process, stop_event):
        """Background thread to read characters and backspaces."""
        if not process or not process.stdout:
            return
            
        while not stop_event.is_set():
            byte = process.stdout.read(1)
            if not byte:
                break
                
            if byte == b'\x08':
                self.state.decrement_position()
                self.injector.inject_backspace()
                if self.state.total_chars > 0:
                    prog = min(1.0, max(0.0, self.state.pause_position / self.state.total_chars))
                    GLib.idle_add(self._ui_update_progress, prog)
                GLib.idle_add(self._ui_correction)
            else:
                char = byte.decode('utf-8', 'ignore')
                self.state.increment_position()
                self.injector.inject_char(char)
                if self.state.total_chars > 0:
                    prog = min(1.0, max(0.0, self.state.pause_position / self.state.total_chars))
                    GLib.idle_add(self._ui_update_progress, prog)

        if not stop_event.is_set():
            ret = process.poll()
            if ret is not None and ret != 0:
                GLib.idle_add(self._ui_error, f"Clack process failed (exit code {ret})")
                
            self.state.is_typing = False
            self.state.is_paused = False
            self.state.current_behavioral_state = "IDLE"
            GLib.idle_add(self._ui_complete)
            
    def _stderr_reader_thread(self, process, stop_event):
        """Background thread to parse behavioral state transitions."""
        if not process or not process.stderr:
            return
            
        for line in iter(process.stderr.readline, b''):
            if stop_event.is_set():
                break
            
            line_str = line.decode('utf-8', 'ignore').strip()
            
            if line_str.startswith("STATE:"):
                parts = line_str.split()
                if len(parts) >= 1:
                    state_part = parts[0]
                    state_name = state_part.replace("STATE:", "")
                    if state_name == "FATIGUED" and self.state.no_fatigue:
                        continue # Ignore false fatigue states from backend
                    self.state.current_behavioral_state = state_name
                    GLib.idle_add(self._ui_update_state, state_name)
            else:
                print(f"[clack stderr] {line_str}", file=sys.stderr)
