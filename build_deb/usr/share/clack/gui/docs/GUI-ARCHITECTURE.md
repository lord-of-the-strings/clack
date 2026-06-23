# GUI-ARCHITECTURE.md — Complete Architecture Document

> **Audience:** Any AI agent or human developer working on the Clack Linux GUI.
> This document describes the complete technical architecture of the GUI application.
> All decisions referenced here are documented in GUI-DECISIONS.md.

---

## 1. System Overview

The Clack GUI is a floating utility window that drives the `clack` CLI binary to simulate human typing into any application on Linux.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER WORKFLOW                             │
│                                                                  │
│  1. User opens Clack GUI                                         │
│  2. User pastes text into the text input area                    │
│  3. User selects a preset or adjusts sliders                     │
│  4. User clicks into the target application (e.g., a browser)    │
│  5. User presses global shortcut or clicks Start                 │
│  6. Clack types the text into the target application             │
│  7. User can pause/resume at any time                            │
│  8. Clack finishes and the GUI returns to expanded state         │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Action (paste text, configure settings)
    │
    ▼
┌──────────────────────┐
│   Clack GUI (GTK4)   │  Constructs CLI command with flags
│   Python + PyGObject  │
└──────────┬───────────┘
           │ subprocess.Popen()
           ▼
┌──────────────────────┐
│   clack CLI binary   │  Reads stdin, computes timing, generates errors,
│   (Rust)             │  emits characters to stdout with built-in delays
└──────────┬───────────┘
           │ stdout: one char at a time (blocking reads, timing embedded)
           │ stderr: STATE:FLOW PREV:FOCUSED WORD:17
           ▼
┌──────────────────────┐
│   Stdout Reader      │  Reads each char from clack stdout
│   Thread             │  Passes to injector
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   ydotool            │  Injects keystroke into the active window
│   (via ydotoold)     │  via the Linux uinput subsystem
└──────────┬───────────┘
           │ uinput kernel event
           ▼
┌──────────────────────┐
│   Target Application │  Receives keystrokes as if typed by human
│   (browser, editor)  │
└──────────────────────┘
```

---

## 2. File Map

| File | Purpose | Key Classes/Functions |
|---|---|---|
| `gui/__main__.py` | Entry point: `python -m gui` | Imports and runs `ClackApp` |
| `gui/app.py` | GTK Application subclass | `ClackApp(Gtk.Application)` — lifecycle, activation |
| `gui/window.py` | Main window with expanded/collapsed states | `ClackWindow(Gtk.ApplicationWindow)` — all UI controls |
| `gui/settings.py` | Advanced settings panel (separate window) | `SettingsPanel(Gtk.Window)` — jitter, seed, shortcuts |
| `gui/clack_runner.py` | Subprocess management and threading | `ClackRunner` — start, pause, resume, threads |
| `gui/state.py` | Thread-safe shared state object | `ClackState` — position, text, typing status |
| `gui/focus_watcher.py` | Active window polling (X11 via xdotool) | `FocusWatcher(threading.Thread)` — poll loop |
| `gui/injector.py` | Keystroke injection via ydotool | `KeystrokeInjector` — inject char, inject key |
| `gui/shortcuts.py` | Global hotkey registration | `ShortcutManager` — register, unregister, rebind |
| `gui/presets.py` | Preset definitions with exact CLI flag values | `PRESETS` dict, `Preset` dataclass |
| `gui/tooltips.py` | All tooltip strings, centralized | `TOOLTIPS` dict keyed by control name |
| `gui/requirements.txt` | Python package dependencies | PyGObject, etc. |
| `gui/SETUP.md` | System dependency setup instructions | ydotoold, xdotool, ydotool setup |

---

## 3. Threading Model

### Thread Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN THREAD                               │
│                                                                  │
│  GTK4 Event Loop                                                 │
│  ┌──────────────────────────────────────────────┐               │
│  │ Handles: button clicks, slider changes,       │               │
│  │          window events, GLib.idle_add() cbs    │               │
│  │ NEVER: reads subprocess, sleeps, blocks        │               │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
│  Receives updates from background threads via GLib.idle_add():   │
│    - Progress bar fraction updates                               │
│    - State label text updates                                    │
│    - Status light color changes                                  │
│    - Pause/complete state transitions                            │
└──────┬────────────────┬────────────────┬────────────────────────┘
       │                │                │
       │ GLib.idle_add  │ GLib.idle_add  │ GLib.idle_add
       │                │                │
┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
│ STDOUT      │  │ STDERR      │  │ FOCUS       │
│ READER      │  │ READER      │  │ WATCHER     │
│ THREAD      │  │ THREAD      │  │ THREAD      │
│             │  │             │  │             │
│ Reads clack │  │ Reads clack │  │ Polls       │
│ stdout      │  │ stderr      │  │ xdotool     │
│ byte-by-    │  │ line-by-    │  │ every 200ms │
│ byte        │  │ line        │  │             │
│             │  │             │  │ Compares    │
│ Injects via │  │ Parses      │  │ active win  │
│ ydotool     │  │ STATE:...   │  │ vs target   │
│             │  │ lines       │  │             │
│ Updates     │  │             │  │ Triggers    │
│ position    │  │ Updates     │  │ pause on    │
│ counter     │  │ state label │  │ mismatch    │
└─────────────┘  └─────────────┘  └─────────────┘
       │                │                │
       ▼                ▼                ▼
┌─────────────────────────────────────────────────┐
│              ClackState (state.py)                │
│              Protected by threading.Lock()        │
│                                                  │
│  Fields:                                         │
│    original_text: str                            │
│    pause_position: int                           │
│    is_typing: bool                               │
│    is_paused: bool                               │
│    current_behavioral_state: str                 │
│    total_chars: int                              │
│    target_window_id: str (X11 only)              │
│    wpm: float                                    │
│    error_rate: float                             │
│    correction_rate: float                        │
│    ... (all user-configured parameters)          │
└─────────────────────────────────────────────────┘
```

### Thread Lifecycle

1. **App start:** Only the main thread runs. Background threads are not created yet.
2. **User clicks Start:** 
   - Main thread records `target_window_id` (via xdotool on X11)
   - Main thread creates `ClackRunner`, which spawns:
     - Stdout reader thread
     - Stderr reader thread
     - Focus watcher thread (X11 only)
   - Main thread transitions window to collapsed state
3. **Typing in progress:** All four threads run concurrently.
4. **Pause triggered (button, shortcut, or focus loss):**
   - The triggering context calls `ClackRunner.pause()` via `GLib.idle_add()` if from a background thread
   - `pause()` sends SIGTERM to clack subprocess
   - All reader threads detect EOF/pipe close and exit
   - Focus watcher thread is stopped
   - Main thread transitions window to expanded state (paused)
5. **Resume:**
   - Main thread creates a new `ClackRunner` with `remaining_text = original_text[pause_position:]`
   - New threads are spawned (same as step 2)
   - Window transitions back to collapsed state
6. **Typing complete:**
   - Stdout reader thread detects EOF (clack exited normally)
   - Schedules completion callback via `GLib.idle_add()`
   - All threads exit
   - Window transitions to expanded state (idle)

---

## 4. Application State Machine

```
                    ┌───────────┐
                    │   IDLE    │ ◀──── App starts here
                    │           │       Window: expanded
                    └─────┬─────┘       Controls: editable
                          │
                    Start button / global shortcut
                          │
                          ▼
                    ┌───────────┐
              ┌────▶│  TYPING   │ ◀────┐
              │     │           │      │  Window: collapsed
              │     └─────┬─────┘      │  Controls: read-only
              │           │            │
              │     Pause button /     │
              │     shortcut /         │  Resume button /
              │     focus loss         │  shortcut
              │           │            │
              │           ▼            │
              │     ┌───────────┐      │
              │     │  PAUSED   │ ─────┘
              │     │           │       Window: expanded
              │     └─────┬─────┘       Controls: editable
              │           │
              │     (User can also
              │      edit text here
              │      and restart)
              │           │
              │     Start button
              │     (resets position)
              │           │
              │           ▼
              │     ┌───────────┐
              └─────│  TYPING   │
                    └─────┬─────┘
                          │
                    clack subprocess exits (EOF on stdout)
                          │
                          ▼
                    ┌───────────┐
                    │ COMPLETE  │       Window: expanded
                    │           │       Shows "Complete!" briefly
                    └─────┬─────┘       Then returns to IDLE
                          │
                          ▼
                    ┌───────────┐
                    │   IDLE    │
                    └───────────┘
```

### State Transitions

| From | To | Trigger | Action |
|---|---|---|---|
| IDLE | TYPING | Start button or global shortcut | Record target window, launch clack subprocess, collapse window |
| TYPING | PAUSED | Pause button, shortcut, or focus loss | SIGTERM clack, record pause_position, expand window |
| PAUSED | TYPING | Resume button or global shortcut | Slice remaining text, launch new clack subprocess, collapse window |
| PAUSED | IDLE | User clears text or clicks "Stop" | Reset state, expand window |
| TYPING | COMPLETE | clack stdout EOF | Stop all threads, expand window, show completion |
| COMPLETE | IDLE | Automatic (after 2s) or user interaction | Reset state |

---

## 5. Subprocess Interface

### CLI Flag Construction

The GUI builds the `clack` command from user-configured settings:

```python
def build_command(self, state: ClackState) -> list[str]:
    cmd = ['clack']
    cmd.extend(['--wpm', str(state.wpm)])
    cmd.extend(['--error-rate', str(state.error_rate)])
    
    # "No leftover mistakes" toggle overrides correction rate
    if state.correct_all_mistakes:
        cmd.extend(['--correction-rate', '1.0'])
    else:
        cmd.extend(['--correction-rate', str(state.correction_rate)])
    
    cmd.extend(['--jitter', str(state.jitter)])
    cmd.extend(['--session-length', str(state.session_length)])
    cmd.extend(['--thinking-pause-prob', str(state.thinking_pause_prob)])
    cmd.extend(['--max-pause', str(state.max_pause)])
    
    # Always enable state output for GUI state display
    cmd.append('--state-output')
    
    if state.no_fatigue:
        cmd.append('--no-fatigue')
    
    if state.error_rate == 0.0:
        cmd.append('--no-errors')
    
    if state.seed is not None:
        cmd.extend(['--seed', str(state.seed)])
    
    return cmd
```

### Backspace Sequence Handling

The stdout reader must detect the 3-byte backspace sequence `\x08\x20\x08` to track net position accurately:

```python
def read_stdout(self):
    """Read clack stdout byte-by-byte, handle backspace sequences."""
    while True:
        byte = self.process.stdout.read(1)
        if not byte:
            break  # EOF
        
        if byte == b'\x08':
            # Potential backspace sequence start
            next_byte = self.process.stdout.read(1)
            if next_byte == b'\x20':
                third_byte = self.process.stdout.read(1)
                if third_byte == b'\x08':
                    # Complete backspace sequence
                    self.state.decrement_position()
                    self.injector.inject_backspace()
                    GLib.idle_add(self._update_status_light, 'red')
                    continue
            # Not a complete backspace sequence — inject literally
            self.injector.inject_byte(byte)
            if next_byte:
                self.injector.inject_byte(next_byte)
        else:
            # Normal character
            self.state.increment_position()
            self.injector.inject_byte(byte)
            GLib.idle_add(self._update_status_light, 'green')
        
        # Update progress
        progress = self.state.get_progress()
        GLib.idle_add(self._update_progress, progress)
```

### Position Tracking Logic

Net position tracking for pause/resume accuracy:

```
Normal character emitted by clack:  position += 1
Backspace sequence (\x08\x20\x08): position -= 1
Corrected character re-emitted:     position += 1

Example: typing "hello" with error on 'l':
  h → position = 1
  e → position = 2
  k → position = 3  (error: 'k' instead of 'l')
  \x08\x20\x08 → position = 2  (backspace)
  l → position = 3  (correction)
  l → position = 4
  o → position = 5

If paused at position 3: remaining_text = original_text[3:] = "lo"
```

---

## 6. Window Design

### Expanded State (320×auto px)

```
┌──────────────────────────────────────┐
│                                      │
│  ┌──────────────────────────────┐    │
│  │ Paste your text here...      │    │  Text input area
│  │                              │    │  (scrollable, 120px height)
│  │                              │    │
│  └──────────────────────────────┘    │
│                                      │
│  Preset  [Proficient        ▼]       │  Dropdown
│                                      │
│  Speed (WPM)  [?]                    │
│  ├─────────────────●──────┤  75      │  Slider
│                                      │
│  Error Rate  [?]                     │
│  ├──────●─────────────────┤  4%      │  Slider
│                                      │
│  Correction Rate  [?]                │
│  ├───────────────●────────┤  85%     │  Slider
│                                      │
│  No leftover mistakes  [?]  [ON ]    │  Toggle
│                                      │
│  Advanced Settings                   │  Text button
│                                      │
│  ┌──────────────────────────────┐    │
│  │  ▶  Start Typing   Ctrl+...  │    │  Start button (44px height)
│  └──────────────────────────────┘    │
│                                      │
└──────────────────────────────────────┘
```

### Collapsed State (320×~48px)

```
┌──────────────────────────────────────┐
│  ●  ████████████░░░░░░  64%    ⏸  ⚙ │  Row 1
│            FOCUSED                   │  Row 2 (state label)
└──────────────────────────────────────┘
```

### Transition Behavior

- **IDLE → Start:** Window collapses (animated slide-up)
- **TYPING → Pause:** Window expands (animated slide-down)
- **PAUSED → Resume:** Window collapses again
- **TYPING → Complete:** Window expands

---

## 7. Keystroke Injection (ydotool)

### Architecture

```
GUI (Python)
    │
    │ subprocess.run(['ydotool', 'type', '--clearmodifiers', char])
    │   OR
    │ subprocess.run(['ydotool', 'key', keycode])
    │
    ▼
ydotoold (daemon)
    │
    │ uinput device write
    │
    ▼
Linux kernel (uinput subsystem)
    │
    │ input event
    │
    ▼
Display server (X11/Wayland)
    │
    │ key event to focused window
    │
    ▼
Target Application
```

### Why ydotool (not xdotool type)

- `xdotool type` only works on X11
- `ydotool` works on both X11 and Wayland because it uses the kernel uinput interface
- `ydotool` requires `ydotoold` daemon running with uinput permissions
- See DECISION-G002 in GUI-DECISIONS.md

### Injection Implementation

```python
class KeystrokeInjector:
    def inject_byte(self, byte: bytes):
        """Inject a single byte as a keystroke via ydotool."""
        char = byte.decode('utf-8', errors='replace')
        subprocess.run(
            ['ydotool', 'type', '--clearmodifiers', '--', char],
            check=False,
            capture_output=True,
        )
    
    def inject_backspace(self):
        """Inject a backspace key via ydotool."""
        subprocess.run(
            ['ydotool', 'key', '14:1', '14:0'],  # KEY_BACKSPACE press+release
            check=False,
            capture_output=True,
        )
```

---

## 8. Focus Loss Detection

### X11 Implementation

```python
class FocusWatcher(threading.Thread):
    """Polls active window ID via xdotool, triggers pause on focus loss."""
    
    def __init__(self, target_window_id: str, on_focus_lost: callable):
        super().__init__(daemon=True)
        self.target_window_id = target_window_id
        self.on_focus_lost = on_focus_lost
        self._stop_event = threading.Event()
    
    def run(self):
        while not self._stop_event.is_set():
            try:
                result = subprocess.run(
                    ['xdotool', 'getactivewindow'],
                    capture_output=True, text=True, timeout=1
                )
                current_window = result.stdout.strip()
                if current_window != self.target_window_id:
                    GLib.idle_add(self.on_focus_lost)
                    break  # Stop watching after focus loss
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            self._stop_event.wait(0.2)  # Poll every 200ms
    
    def stop(self):
        self._stop_event.set()
```

### Recording Target Window

When the user triggers Start:
```python
result = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
target_window_id = result.stdout.strip()
```

**Important:** The target window is the window that was active *before* the user clicked into the Clack GUI. The user's workflow is:
1. Click into target app (e.g., browser text field)
2. Press global shortcut to start typing
3. The shortcut handler records the active window ID *at that moment*
4. Clack starts injecting into that window

If the user clicks the Start button instead, the active window is the Clack GUI itself. In this case, the GUI should show a brief message: "Click into the target window, then press the start shortcut."

### Wayland Limitations [PROPOSED]

Wayland compositors do not expose a standardized API for querying the focused window from external applications. The following fallback strategies are evaluated per compositor:

| Compositor | Approach | Status |
|---|---|---|
| wlroots-based (Sway, Hyprland) | `wlr-foreign-toplevel-management` protocol or compositor CLI tools (`swaymsg`, `hyprctl`) | [PROPOSED] Best-effort |
| GNOME (Mutter) | D-Bus interface via `org.gnome.Shell.Eval` (restricted in newer GNOME) | [PROPOSED] Unreliable |
| KDE (KWin) | D-Bus: `org.kde.KWin` scripting interface | [PROPOSED] Untested |
| Other | No detection; user must use manual pause button | [VERIFIED] Fallback |

For the MVP, focus detection on Wayland is marked as best-effort. If the compositor does not support any detection method, the GUI disables auto-pause and shows a one-time notice:
> "Focus detection is not available on your Wayland compositor. Use the pause button or shortcut to pause typing manually."

---

## 9. Global Shortcut System

### Implementation Approach

The global shortcut system must work even when the Clack window is not focused. On X11, this is achieved using the `keybinder3` library (if compatible with GTK4) or via direct X11 key grab through `python-xlib`. On Wayland, global shortcuts are compositor-dependent and may not be available.

See DECISION-G006 and DECISION-G007 in GUI-DECISIONS.md for the specific library choice and default shortcut.

### Shortcut Behavior

| Current State | Shortcut Action |
|---|---|
| IDLE (text present) | Start typing |
| IDLE (no text) | Do nothing (or show error) |
| TYPING | Pause |
| PAUSED | Resume |

One shortcut handles all three states.

### Speed Multiplier Hotkey

A separate hotkey is held (not toggled) to temporarily increase typing speed by 1.5×. See DECISION-G008 for implementation approach.

---

## 10. Settings Persistence

User settings are saved to `~/.config/clack/gui.json`:

```json
{
  "preset": "Proficient",
  "wpm": 75,
  "error_rate": 0.04,
  "correction_rate": 0.85,
  "correct_all_mistakes": true,
  "jitter": 0.15,
  "session_length": 500,
  "thinking_pause_prob": 0.015,
  "max_pause": 5000,
  "no_fatigue": false,
  "seed": null,
  "global_shortcut": "Ctrl+Shift+Y",
  "speed_boost_shortcut": "Ctrl+Shift"
}
```

Settings are loaded on startup and saved on every change (debounced to avoid excessive writes).

---

## 11. Dependency Check Flow

On startup, before the main window is shown:

```
┌───────────────┐
│  Check clack  │──── Missing ────▶ Error dialog + exit
│  binary       │
└───────┬───────┘
        │ Found
        ▼
┌───────────────┐
│ Check ydotool │──── Missing ────▶ Error dialog with install instructions + exit
│ binary        │
└───────┬───────┘
        │ Found
        ▼
┌───────────────┐
│ Check ydotoold│──── Not running ─▶ Setup dialog with retry button
│ daemon        │                    (do not exit, let user start it)
└───────┬───────┘
        │ Running
        ▼
┌───────────────┐
│ Check xdotool │──── Missing ────▶ Warning: "Focus detection disabled"
│ binary        │                    (continue without, soft dependency)
└───────┬───────┘
        │ Found (or warned)
        ▼
┌───────────────┐
│ Check GTK4 +  │──── Missing ────▶ Hard error (import fails, Python crashes)
│ PyGObject     │
└───────┬───────┘
        │ OK
        ▼
┌───────────────┐
│ Check global  │──── Missing ────▶ Warning: "Global shortcuts unavailable"
│ shortcut lib  │                    (continue without)
└───────┬───────┘
        │ OK
        ▼
┌───────────────┐
│  Show main    │
│  window       │
└───────────────┘
```

### Hard Dependencies (app exits if missing)
- `clack` binary
- `ydotool` binary
- GTK4 + PyGObject

### Soft Dependencies (app continues with reduced functionality)
- `ydotoold` daemon (error dialog with retry, but user can try to start it)
- `xdotool` binary (focus detection disabled)
- Global shortcut library (global shortcuts disabled, manual button only)

---

## 12. Known Wayland Limitations

| Feature | X11 | Wayland |
|---|---|---|
| Keystroke injection (ydotool) | ✅ Works | ✅ Works (via uinput, compositor-independent) |
| Active window detection | ✅ xdotool | ⚠️ Compositor-dependent, best-effort |
| Global shortcuts | ✅ keybinder3 / X11 grab | ⚠️ Compositor-dependent |
| Always-on-top | ✅ GTK4 window hint | ✅ GTK4 handles this |
| Window dragging | ✅ GTK4 | ✅ GTK4 |

**MVP target:** X11 is the minimum requirement. Wayland support is best-effort.

The `ydotool` keystroke injection works on both X11 and Wayland because it uses the kernel uinput subsystem, which bypasses the display server entirely. This is the primary reason ydotool was chosen over xdotool for injection (see DECISION-G002).

---

*End of GUI-ARCHITECTURE.md*
*Document version: 1.0*
