# GUI-AGENT.md — Instructions for the GUI Implementation Agent

> **Audience:** Any AI agent or human developer implementing the Clack Linux GUI.
> Read this document in its entirety before writing any code.
> Every rule here is non-negotiable unless overridden by the project owner.

---

## The One Rule

**The GUI is a driver. The simulation engine is `clack` (the CLI binary).**

The GUI calls `clack` as a subprocess. It feeds text via stdin, reads character-by-character output from stdout, and injects each character into the target window using `ydotool`.

The GUI does **not**:
- Compute inter-key intervals
- Generate typing errors
- Decide correction strategies
- Manage behavioral states
- Perform any simulation logic whatsoever

If you find yourself writing code that decides *when* or *how* to type a character, you are doing it wrong. That is `clack`'s job. The GUI's job is:
1. Collect user settings (WPM, error rate, etc.)
2. Launch `clack` with those settings as CLI flags
3. Read `clack`'s stdout one character at a time
4. Inject each character into the target window via `ydotool`
5. Read `clack`'s stderr for state transitions (to update the UI)
6. Handle pause, resume, and focus loss

---

## Branch Rules

All GUI work happens on the `dev` branch. **Never commit to `main`.**

Before making any changes, verify your branch:
```bash
git branch --show-current
# Must output: dev
```

If you are not on `dev`, switch immediately:
```bash
git checkout dev
```

Do not create feature branches off `main`. Do not merge to `main`. The project owner handles `main` merges.

---

## Threading Rule

**The GTK main thread must never block. Ever.**

GTK4 runs an event loop on the main thread. If you block it (with `subprocess.wait()`, `time.sleep()`, a blocking `read()`, or any synchronous I/O), the entire UI freezes.

### Required Threading Model

Four threads are used:

| Thread | Purpose | Lifetime |
|---|---|---|
| **Main Thread** | GTK event loop. UI rendering. Event handling. | App lifetime |
| **Stdout Reader** | Reads clack stdout char-by-char, injects via ydotool, updates position counter | While typing is active |
| **Stderr Reader** | Reads clack stderr line-by-line, parses state transitions | While typing is active |
| **Focus Watcher** | Polls active window via xdotool every 200ms, triggers pause on focus loss | While typing is active (X11 only) |

### UI Update Rule

**All UI updates must go through `GLib.idle_add()`.**

Background threads must never call GTK widget methods directly. Instead:

```python
# WRONG — will crash or corrupt state
def stdout_reader_thread(self):
    char = self.process.stdout.read(1)
    self.progress_bar.set_fraction(0.5)  # ← NEVER do this

# CORRECT — schedule UI update on main thread
def stdout_reader_thread(self):
    char = self.process.stdout.read(1)
    GLib.idle_add(self._update_progress, 0.5)

def _update_progress(self, fraction):
    self.progress_bar.set_fraction(fraction)
    return False  # Return False to run only once
```

`GLib.idle_add()` schedules a callback to run on the main thread during the next idle cycle. The callback must return `False` (run once) or `True` (repeat).

---

## Subprocess Interface Contract

The GUI communicates with `clack` exclusively through the subprocess interface. Do not modify `clack` CLI behavior unless explicitly approved.

### Starting a Subprocess

```python
import subprocess

process = subprocess.Popen(
    ['clack',
     '--wpm', str(wpm),
     '--error-rate', str(error_rate),
     '--correction-rate', str(correction_rate),
     '--jitter', str(jitter),
     '--session-length', str(session_length),
     '--thinking-pause-prob', str(thinking_pause_prob),
     '--max-pause', str(max_pause),
     '--state-output',              # always on for GUI state display
     # Optional flags:
     # '--no-fatigue',              # if no-fatigue toggle is on
     # '--no-errors',               # if error rate is 0.0
     # '--seed', str(seed),         # if user specified a seed
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
```

### Feeding Text

```python
process.stdin.write(text_to_type.encode('utf-8'))
process.stdin.close()
```

Text is fed **all at once**, then stdin is closed. `clack` processes it and emits characters with timing already applied.

### Reading Output

Read stdout **one byte at a time**:

```python
while True:
    byte = process.stdout.read(1)
    if not byte:
        break  # EOF — clack finished
    # Inject this byte via ydotool
    # Update position counter
```

**Important:** The GUI does NOT add sleep. `clack` handles all timing internally. The `read(1)` call blocks until `clack` emits the next character (after its internal sleep).

### Reading State Transitions

Read stderr **line by line** in a separate thread:

```python
for line in process.stderr:
    line = line.decode('utf-8').strip()
    if line.startswith('STATE:'):
        # Parse: STATE:<new_state> PREV:<old_state> WORD:<word_count>
        parts = line.split()
        new_state = parts[0].split(':')[1]
        prev_state = parts[1].split(':')[1]
        word_count = int(parts[2].split(':')[1])
        GLib.idle_add(self._update_state_label, new_state)
```

### Stopping (Pause)

```python
import signal
process.send_signal(signal.SIGTERM)
process.wait()  # In the background thread, not main thread
```

### Backspace Sequence Detection

`clack` emits backspace as the 3-byte sequence `\x08\x20\x08`. The GUI must detect this to correctly track the net position in the original text:

```python
# When reading stdout:
if byte == b'\x08':
    # Start of potential backspace sequence
    # Read next two bytes to confirm \x20 \x08
    # If confirmed: position -= 1 (net character erased)
    # Inject the backspace sequence via ydotool
```

---

## Shared State Thread Safety

The `ClackState` object in `state.py` holds all shared state between threads. Access must be protected:

```python
import threading

class ClackState:
    def __init__(self):
        self._lock = threading.Lock()
        self.original_text: str = ""
        self.pause_position: int = 0
        self.is_typing: bool = False
        self.is_paused: bool = False
        self.current_state: str = "FOCUSED"
        # ... other fields

    def get_pause_position(self) -> int:
        with self._lock:
            return self.pause_position

    def increment_position(self):
        with self._lock:
            self.pause_position += 1

    def decrement_position(self):
        with self._lock:
            self.pause_position -= 1
```

**Never** access shared state without the lock. **Never** hold the lock while doing I/O.

---

## File Organization

All GUI source code lives under `gui/` in the repository root:

```
gui/
├── __main__.py         # Entry point: python -m gui
├── app.py              # GtkApplication subclass
├── window.py           # Main window (expanded/collapsed states)
├── settings.py         # Advanced settings panel
├── clack_runner.py     # Subprocess management, threading
├── state.py            # ClackState shared state object
├── focus_watcher.py    # xdotool polling thread
├── injector.py         # ydotool keystroke injection wrapper
├── shortcuts.py        # Global hotkey management
├── presets.py          # Preset definitions and values
├── tooltips.py         # All tooltip strings (centralized)
├── requirements.txt    # Python dependencies
├── SETUP.md            # System dependency setup instructions
└── docs/               # Planning documents (gitignored)
    ├── GUI-AGENT.md
    ├── GUI-ARCHITECTURE.md
    ├── GUI-DECISIONS.md
    ├── GUI-ROADMAP.md
    └── GUI-TECH-DEBT.md
```

Do not create files outside of `gui/`. Do not modify files in `clack-core/` or `clack-cli/`.

---

## Naming Conventions

- Project name: **Clack** (capital C in prose)
- Binary name: `clack` (lowercase in code/commands)
- Library name: `libclack` (when referring to the Rust library)
- Identifier prefix: `clack_` (in code identifiers)
- **Never** use "htype" anywhere except in attribution comments
- GUI module names: lowercase with underscores (Python convention)
- GTK widget IDs: lowercase with hyphens (GTK convention)

---

## Pre-Commit Checklist

Before every commit, verify all of the following:

```
[ ] Am I on the dev branch?                              (must be YES)
[ ] Does this add simulation logic to the GUI?           (must be NO)
[ ] Does the GTK main thread block anywhere?             (must be NO)
[ ] Are all UI updates via GLib.idle_add()?              (must be YES)
[ ] Did I test with ydotoold running?                    (must be YES)
[ ] Did I test focus loss detection?                     (must be YES)
[ ] Did I test pause and resume?                         (must be YES)
[ ] Did I check for thread safety (lock usage)?          (must be YES)
[ ] Did I test with an empty text input?                 (must be YES)
[ ] Does the window stay always-on-top?                  (must be YES)
```

Run the checklist mentally or paste it into your commit message as verification.

---

## Common Mistakes to Avoid

1. **Sleeping in the main thread.** No `time.sleep()`, no `process.wait()`, no blocking reads.
2. **Adding timing logic.** If you write `time.sleep(delay)` anywhere in the GUI, you are wrong. `clack` handles timing.
3. **Buffering stdout.** Read one byte at a time. Do not use `readline()` or read in chunks.
4. **Forgetting `GLib.idle_add()`.** Every GTK call from a background thread must go through it.
5. **Ignoring ydotoold.** The GUI must check that `ydotoold` is running before attempting keystroke injection.
6. **Modifying clack's output.** The GUI passes characters through unchanged. It does not filter, transform, or reinterpret them.
7. **Using `xdotool type` for injection.** `xdotool` is for **window detection only**. `ydotool` is for **keystroke injection only**. These are separate tools with separate roles.

---

## Testing Your Changes

### Minimal Smoke Test
```bash
# 1. Ensure ydotoold is running
pgrep ydotoold || echo "Start ydotoold first!"

# 2. Launch the GUI
cd /path/to/clack
python -m gui

# 3. Paste text, click Start
# 4. Verify characters appear in target window
# 5. Click away to test focus loss → should auto-pause
# 6. Click resume → should continue from where it stopped
# 7. Try with empty text → should show error/do nothing gracefully
```

### Testing Pause/Resume Accuracy
```bash
# Use a known text, pause at a specific point, resume
# Verify the remaining text starts from the correct position
# Verify no duplicate characters or missing characters
```

---

*End of GUI-AGENT.md*
*This document is version 1.0 and applies to all GUI development on the dev branch.*
