# GUI-ROADMAP.md — Implementation Roadmap for the Clack Linux GUI

> **Audience:** Any AI agent or human developer implementing the Clack GUI.
> Tasks are ordered by dependency. Each task is specific, testable, and assigned to a file.
> Confidence markers: **[VERIFIED]**, **[INFERRED]**, **[PROPOSED]**.

---

## Phase G0 — Branch and Scaffold

**Goal:** Create the project structure, verify all imports work, and establish that the GUI can launch and exit cleanly.

### G00: Create dev branch (local + remote)
- **File:** N/A (git operations)
- **Action:** `git checkout -b dev && git push -u origin dev`
- **Done:** Local and remote `dev` branch exist. `git branch -a` shows both. [VERIFIED] ✅ COMPLETE

### G00a: Create gui/ directory structure
- **File:** All files under `gui/`
- **Action:** Create the following stub files with documented interfaces:
  ```
  gui/__main__.py
  gui/app.py
  gui/window.py
  gui/settings.py
  gui/clack_runner.py
  gui/state.py
  gui/focus_watcher.py
  gui/injector.py
  gui/shortcuts.py
  gui/presets.py
  gui/tooltips.py
  gui/requirements.txt
  gui/SETUP.md
  ```
- **Each stub file must contain:**
  - Module docstring explaining its purpose
  - Import statements for its dependencies
  - Class/function signatures with docstrings (no implementation body yet)
  - `pass` as placeholder for method bodies
- **Done:** `python -c "import gui"` succeeds without errors.

### G00b: Create requirements.txt
- **File:** `gui/requirements.txt`
- **Action:** List all Python dependencies:
  ```
  PyGObject>=3.42.0
  ```
  Note: `PyGObject` is the only pip-installable dependency. GTK4, ydotool, xdotool, and other tools are system packages installed via the system package manager, not pip.
- **Done:** File exists with correct contents.

### G00c: Verify imports work
- **File:** `gui/__main__.py`
- **Action:** Implement minimal entry point:
  ```python
  import gi
  gi.require_version('Gtk', '4.0')
  from gi.repository import Gtk, GLib
  print("GTK4 import OK")
  ```
- **Tests:**
  - `python -m gui` prints "GTK4 import OK" and exits cleanly.
  - If GTK4 is not installed, prints a clear error message with installation instructions.
- **Done:** `python -m gui` launches without import errors, shows dependency check dialog, exits cleanly. [VERIFIED]

### G00d: Startup dependency checker (basic)
- **File:** `gui/app.py`
- **Action:** Implement `check_dependencies()` function that checks:
  1. `clack` binary exists (`shutil.which('clack')`)
  2. `ydotool` binary exists (`shutil.which('ydotool')`)
  3. `ydotoold` daemon is running (`subprocess.run(['pgrep', 'ydotoold'])`)
  4. `xdotool` binary exists (`shutil.which('xdotool')`) — soft dependency
  5. GTK4 import succeeded (already verified by this point)
- **Error handling:**
  - Missing hard dependency → error dialog with install instructions → exit
  - Missing soft dependency → warning logged → continue
  - ydotoold not running → setup dialog with retry button → wait for user
- **Done:** App starts with all dependencies present. Shows correct error for each missing dependency.

**Phase G0 Done Criteria:**
- `python -m gui` launches without import errors
- Shows dependency check results
- Exits cleanly if dependencies are met (no window shown yet) or shows error dialog if not

---

## Phase G1 — Core Subprocess Integration

**Goal:** The GUI can launch clack, read its output, inject keystrokes, and handle pause/resume — all tested in terminal before any window is built.

### G01: ClackState object definition
- **File:** `gui/state.py`
- **Action:** Implement the `ClackState` class with all fields, types, thread-safe access methods:
  ```python
  class ClackState:
      original_text: str       # Full text to type
      pause_position: int      # Net characters consumed from original_text
      is_typing: bool          # True while clack subprocess is running
      is_paused: bool          # True when paused (subprocess terminated)
      current_behavioral_state: str  # FOCUSED, FLOW, etc.
      total_chars: int         # len(original_text)
      target_window_id: str    # X11 window ID of target app
      # User settings (read-only during typing):
      wpm: float
      error_rate: float
      correction_rate: float
      correct_all_mistakes: bool
      jitter: float
      session_length: int
      thinking_pause_prob: float
      max_pause: int
      no_fatigue: bool
      seed: int | None
  ```
- **Thread safety:** All public methods use `threading.Lock()`. No direct field access from outside.
- **Done:** Unit test creates `ClackState`, calls all methods from two threads without deadlock or race.

### G02: clack_runner.py — Start subprocess with flags
- **File:** `gui/clack_runner.py`
- **Action:** Implement `ClackRunner` class with:
  - `build_command(state: ClackState) -> list[str]` — constructs CLI command from state
  - `start(text: str, state: ClackState)` — launches subprocess, starts reader threads
  - `_create_process(cmd: list[str], text: str) -> subprocess.Popen` — creates the Popen object
- **Flag mapping:** Map every ClackState field to the correct `clack` CLI flag name:
  - `wpm` → `--wpm`
  - `error_rate` → `--error-rate`
  - `correction_rate` → `--correction-rate` (or `1.0` if `correct_all_mistakes` is True)
  - `jitter` → `--jitter`
  - `session_length` → `--session-length`
  - `thinking_pause_prob` → `--thinking-pause-prob`
  - `max_pause` → `--max-pause`
  - `no_fatigue` → `--no-fatigue` (flag, only if True)
  - `seed` → `--seed` (only if not None)
  - Always include `--state-output`
- **Done:** `build_command()` returns correct command list for each preset. `start()` launches clack subprocess that begins emitting characters.

### G03: Stdout reader thread — Read chars, update position counter
- **File:** `gui/clack_runner.py`
- **Action:** Implement `_stdout_reader_thread(self)` method:
  - Reads `self.process.stdout.read(1)` in a loop until EOF
  - Detects 3-byte backspace sequence `\x08\x20\x08`:
    - On `\x08`: read next byte. If `\x20`, read next. If `\x08`, it's a backspace sequence → `state.decrement_position()` + inject backspace via ydotool
    - Otherwise: inject literal bytes
  - On normal character: `state.increment_position()` + inject via ydotool
  - After each character/sequence: schedule UI update via `GLib.idle_add()` (no-op for now, wired in Phase G2)
  - On EOF: schedule completion callback via `GLib.idle_add()`
- **Done:** Position counter accurately tracks net position for text with errors and corrections. Verified by running clack with `--seed` and known input, checking final position matches expected.

### G04: Stderr reader thread — Parse state transitions
- **File:** `gui/clack_runner.py`
- **Action:** Implement `_stderr_reader_thread(self)` method:
  - Reads `self.process.stderr` line by line
  - For lines matching `STATE:<state> PREV:<prev> WORD:<count>`:
    - Parse state name, previous state, word count
    - Update `state.current_behavioral_state`
    - Schedule UI update via `GLib.idle_add()` (no-op for now)
  - For other stderr lines: log as potential error messages
- **Done:** State transitions are parsed correctly. Verified with `clack --state-output` and known input.

### G05: Basic injection via ydotool (one char at a time)
- **File:** `gui/injector.py`
- **Action:** Implement `KeystrokeInjector` class:
  - `inject_char(char: str)` — runs `ydotool type --clearmodifiers -- <char>`
  - `inject_backspace()` — runs `ydotool key 14:1 14:0` (KEY_BACKSPACE press+release)
  - `inject_key(keycode: int)` — runs `ydotool key <keycode>:1 <keycode>:0`
  - `check_available() -> bool` — checks if ydotool and ydotoold are available
  - Error handling: if ydotool fails, log the error and continue (do not crash)
- **Done:** Characters injected by ydotool appear in a focused text editor. Backspace correctly erases.

### G06: Subprocess termination on pause (SIGTERM)
- **File:** `gui/clack_runner.py`
- **Action:** Implement `pause()` method:
  - Sends `signal.SIGTERM` to the clack subprocess
  - Calls `process.wait()` (in the calling thread, which is a background thread or main thread with no blocking concern since SIGTERM is fast)
  - Sets `state.is_typing = False`, `state.is_paused = True`
  - Stops the focus watcher thread
  - The stdout/stderr reader threads will exit on their own when the pipe closes (EOF)
- **Done:** Pause terminates the subprocess cleanly. No zombie processes. Reader threads exit.

### G07: Resume logic — Slice text, restart subprocess
- **File:** `gui/clack_runner.py`
- **Action:** Implement `resume()` method:
  - Reads `pause_position` from state
  - Computes `remaining_text = state.original_text[state.pause_position:]`
  - Calls `start(remaining_text, state)` with the same user settings
  - Sets `state.is_paused = False`, `state.is_typing = True`
- **Important:** Resume does NOT change any settings. Same WPM, same error rate, same everything.
- **Important:** The state machine in the new clack subprocess starts fresh from FOCUSED (default start state). This is expected and acceptable.
- **Done:** After pausing mid-text and resuming, the complete text is typed correctly with no duplicate or missing characters. Verified with `--seed` and deterministic text.

**Phase G1 Done Criteria:**
- Text typed in terminal (not GUI window) with correct clack behavior
- Position tracking accurate across errors and corrections
- Pause/resume works correctly with accurate position tracking
- All verified by running clack with known input and checking injected output

---

## Phase G2 — Window Implementation

**Goal:** The full GTK4 window with expanded and collapsed states, all controls, and live updates during typing.

### G08: Main GTK window, always-on-top, draggable
- **File:** `gui/window.py`
- **Action:** Create `ClackWindow(Gtk.ApplicationWindow)`:
  - `set_keep_above(True)` — always on top
  - `set_resizable(False)` — fixed size
  - `set_decorated(True)` but with minimal decoration (title bar optional, consider CSD)
  - Default position: top-right corner of screen, 16px from edges
    - Use `Gdk.Display.get_default().get_monitors()` to find screen size
    - Position via `set_default_size()` and manual placement
  - Draggable: implement drag via `GtkGestureDrag` on the window surface
    - Only drag when click target is not an interactive control (slider, button, etc.)
  - Width: 320px in both expanded and collapsed states
- **Done:** Window appears in top-right corner, stays on top of all other windows, can be dragged, is not resizable.

### G09: Expanded state layout — All controls per spec
- **File:** `gui/window.py`
- **Action:** Build the expanded state layout using GTK4 containers:
  - `Gtk.Box(orientation=VERTICAL)` as main container
  - Text input area: `Gtk.ScrolledWindow` containing `Gtk.TextView`
    - Placeholder text: "Paste your text here..."
    - Height: 120px (fixed via `set_size_request`)
    - Editable when idle or paused, read-only when typing
  - Preset selector: `Gtk.DropDown` (GTK4) or `Gtk.ComboBoxText`
    - Options: Hunt & Peck, Casual, Proficient, Fast, Custom
    - Default: Proficient
  - Three sliders (WPM, Error Rate, Correction Rate) with labels and [?] icons
  - "No leftover mistakes" toggle
  - Advanced Settings button
  - Start button (full width, 44px height)
- **Done:** All controls render correctly, match the spec layout, and are interactive.

### G10: Preset selector with exact values
- **File:** `gui/presets.py` + `gui/window.py`
- **Action:** Implement preset data and selector behavior:
  ```python
  PRESETS = {
      "Hunt & Peck": Preset(wpm=20, error_rate=0.08, correction_rate=0.75, jitter=0.25, thinking_pause_prob=0.04),
      "Casual":      Preset(wpm=45, error_rate=0.05, correction_rate=0.82, jitter=0.18, thinking_pause_prob=0.02),
      "Proficient":  Preset(wpm=75, error_rate=0.04, correction_rate=0.85, jitter=0.15, thinking_pause_prob=0.015),
      "Fast":        Preset(wpm=100, error_rate=0.02, correction_rate=0.92, jitter=0.10, thinking_pause_prob=0.008),
  }
  ```
  - Selecting a preset updates all sliders immediately
  - Adjusting any slider switches preset dropdown to "Custom"
  - "Custom" preset uses whatever values are currently set in the sliders
- **Done:** Selecting "Casual" sets WPM slider to 45, error rate to 5%, etc. Changing WPM slider switches preset to "Custom".

### G11: Slider controls with live value display
- **File:** `gui/window.py`
- **Action:** Implement three slider rows:
  - **WPM Slider:**
    - `Gtk.Scale(orientation=HORIZONTAL)`, range 10–150, step 1
    - Value label showing integer (e.g., "75")
    - Connected to `state.wpm`
  - **Error Rate Slider:**
    - `Gtk.Scale`, range 0.0–0.15, step 0.001
    - Value label showing percentage (e.g., "4%")
    - Connected to `state.error_rate`
  - **Correction Rate Slider:**
    - `Gtk.Scale`, range 0.0–1.0, step 0.01
    - Value label showing percentage (e.g., "85%")
    - Connected to `state.correction_rate`
  - Each slider has a `[?]` button with a tooltip (text from `tooltips.py`)
  - Each slider's `value-changed` signal switches preset to "Custom" if current values don't match any preset
- **Done:** Sliders render, show live values, and switch preset to Custom on manual adjustment.

### G12: No leftover mistakes toggle with CLI flag mapping
- **File:** `gui/window.py`
- **Action:** Implement the toggle:
  - `Gtk.Switch`, default ON
  - When ON: `correction_rate` sent to clack CLI is forced to `1.0` regardless of slider value
  - When OFF: slider value is used as-is
  - The correction rate slider is visually disabled (insensitive) when toggle is ON [PROPOSED]
  - Tooltip from `tooltips.py`
- **Done:** Toggle ON → clack receives `--correction-rate 1.0`. Toggle OFF → clack receives slider value.

### G13: Start button with shortcut hint label
- **File:** `gui/window.py`
- **Action:** Implement the start/resume button:
  - Full width minus padding
  - Height: 44px minimum (`set_size_request(-1, 44)`)
  - Label when idle: `"▶  Start Typing    Ctrl+Shift+F12"`
  - Label when paused: `"▶  Resume    Ctrl+Shift+F12"`
  - Shortcut hint text in a muted color (use Pango markup or separate label)
  - Connected to `self._on_start_clicked()` handler
  - Validates: text area is not empty, ydotoold is running
- **Done:** Button shows correct label in each state, triggers start/resume on click.

### G14: Collapsed state layout
- **File:** `gui/window.py`
- **Action:** Implement the collapsed view as a separate layout within the same window:
  - Row 1: Status light (●) + Progress bar + Pause button (⏸) + Settings icon (⚙)
  - Row 2: State label (FOCUSED / FLOW / THINKING / etc.)
  - Layout using `Gtk.Box(orientation=HORIZONTAL)` for row 1 and `Gtk.Label` for row 2
  - Window height collapses to ~48px (two rows)
  - The expanded layout is hidden (`.set_visible(False)`) and the collapsed layout is shown
- **Status light implementation:**
  - Use `Gtk.DrawingArea` with 10px diameter circle
  - Colors: gray (idle/paused), green (typing normally), red (error in progress)
  - Red blinks at 2Hz (use `GLib.timeout_add(500, toggle_red)`)
- **Progress bar:**
  - `Gtk.ProgressBar` with text overlay showing percentage
  - Width: fills remaining space (use `set_hexpand(True)`)
- **Pause button:**
  - `Gtk.Button` with icon, 32×32px minimum
  - Shows ⏸ while typing, ▶ while paused
- **Settings icon:**
  - `Gtk.Button` with ⚙ icon, opens settings panel
- **Done:** Collapsed state shows all elements, progress bar updates, status light changes color.

### G15: State transition animation (expand ↔ collapse on start)
- **File:** `gui/window.py`
- **Action:** Implement smooth transition between expanded and collapsed states:
  - When typing starts: expanded layout fades out, collapsed layout fades in, window height animates
  - When typing pauses/completes: reverse
  - Use `Gtk.Revealer` for smooth show/hide transitions, or manual CSS animation
  - If animation is complex, a simple instant swap (`.set_visible()`) is acceptable for MVP [PROPOSED]
- **Done:** Window transitions between expanded and collapsed states without visual glitches.

### G16: Progress bar updating via GLib.idle_add()
- **File:** `gui/window.py` + `gui/clack_runner.py`
- **Action:** Wire the stdout reader thread to update the progress bar:
  - In `_stdout_reader_thread()`: after each character, compute `progress = state.pause_position / state.total_chars`
  - Schedule `GLib.idle_add(self._update_progress, progress)`
  - In `_update_progress()`: set `self.progress_bar.set_fraction(progress)` and update text label
  - Throttle updates to avoid flooding the main thread: only update every 5 characters or 100ms, whichever comes first [PROPOSED]
- **Done:** Progress bar fills left-to-right during typing, shows correct percentage.

### G17: Status light — Gray/green/red, blinking at 2Hz on red
- **File:** `gui/window.py`
- **Action:** Implement status light behavior:
  - **Gray:** IDLE or PAUSED state
  - **Green:** TYPING state, no error active
  - **Red:** Error being generated or correction in progress
    - Blinks at 2Hz (250ms on, 250ms off) using `GLib.timeout_add(250, toggle_blink)`
    - Returns to green when correction is complete
  - Detection of error state: when the stdout reader detects a backspace sequence, the status goes red. When the next normal character is emitted (after correction), it goes green.
- **Done:** Status light correctly reflects typing state. Red blinks during error/correction sequences.

### G18: State label updating from stderr thread
- **File:** `gui/window.py`
- **Action:** Wire the stderr reader thread to update the state label:
  - In `_stderr_reader_thread()`: parse `STATE:<state>` and schedule `GLib.idle_add(self._update_state_label, state_name)`
  - In `_update_state_label()`: set label text to state name
  - Font: monospace, small (9–10px equivalent), muted color
  - Use CSS styling: `label { font-family: monospace; font-size: 9pt; opacity: 0.6; }`
- **Done:** State label shows "FOCUSED", "FLOW", "THINKING", etc. in real time during typing.

### G19: Pause/resume button state management
- **File:** `gui/window.py`
- **Action:** Implement button state changes:
  - While typing: button shows ⏸ (pause icon), clicking triggers `clack_runner.pause()`
  - While paused: button shows ▶ (play icon), clicking triggers `clack_runner.resume()`
  - While idle: button is hidden or shows a different state
  - Button click handler checks current state and dispatches accordingly
- **Done:** Button icon and behavior change correctly between typing and paused states.

### G20: Advanced Settings panel
- **File:** `gui/settings.py`
- **Action:** Create `SettingsPanel(Gtk.Window)`:
  - Separate non-modal window, always-on-top
  - Contains controls for all remaining clack CLI flags:
    - Jitter: `Gtk.Scale` 0.0–1.0, default 0.15
    - Session Length: `Gtk.SpinButton` 100–5000, default 500
    - Thinking Pause Prob: `Gtk.Scale` 0.0–0.1, default 0.015
    - Max Pause (ms): `Gtk.SpinButton` 500–10000, default 5000
    - No Fatigue: `Gtk.Switch`, default OFF
    - State Output: `Gtk.Switch`, default ON (required for GUI, shown as info only)
    - RNG Seed: `Gtk.Entry`, integer, blank = random
  - Global Shortcut:
    - Label: "Start/Pause Shortcut"
    - `Gtk.Entry` showing current shortcut (e.g., "Ctrl+Shift+F12")
    - Click to rebind: entry captures next key combo
  - Speed Multiplier Hotkey:
    - Label: "Speed Boost (hold)"
    - `Gtk.Entry` showing current hotkey combo
  - Each control has a `[?]` icon with tooltip from `tooltips.py`
  - "Reset to Defaults" button at the bottom resets all values
- **Done:** Settings panel opens, shows all controls with correct defaults, changes persist to ClackState.

### G21: All tooltip strings from tooltips.py
- **File:** `gui/tooltips.py`
- **Action:** Define all tooltip strings in a centralized dictionary:
  ```python
  TOOLTIPS = {
      "wpm": "Words per minute. Higher = faster typing. Average human typist is 40-60 WPM.",
      "error_rate": "How often typos occur. 4% is realistic for a proficient typist. 0% disables errors entirely.",
      "correction_rate": "How often typos get corrected. 85% is realistic. Uncorrected typos remain in the final text.",
      "correct_all_mistakes": "When on, all errors are corrected before the text is complete. The typing process still looks human with mistakes happening and being fixed, but the final output will be clean.",
      "jitter": "Randomness in typing rhythm. Higher values create more variable timing between keystrokes. 0.15 is realistic.",
      "session_length": "Expected total character count. Used to compute warmup and fatigue curves. Set to approximate length of your text.",
      "thinking_pause_prob": "Probability of a thinking pause between words. 1.5% is realistic. Higher values add more pauses.",
      "max_pause": "Maximum duration of any single pause in milliseconds. Prevents unrealistically long pauses.",
      "no_fatigue": "When on, disables warmup slowdown at the start and fatigue effects at the end of long typing sessions.",
      "seed": "Random number generator seed. Set a specific number for reproducible behavior. Leave blank for random.",
      "global_shortcut": "Global keyboard shortcut to start, pause, or resume typing from any application.",
      "speed_boost": "Hold this key combination while typing to temporarily increase speed by 1.5×.",
  }
  ```
- **Done:** Every `[?]` icon in the UI shows the correct tooltip text on hover.

**Phase G2 Done Criteria:**
- Complete window renders correctly in both expanded and collapsed states
- All controls are functional and connected to ClackState
- Presets load correct values into sliders
- Progress bar, status light, and state label update in real time during typing
- Settings panel opens and all controls work
- All tooltips display correct text

---

## Phase G3 — System Integration

**Goal:** Global shortcuts, focus detection, speed multiplier, and settings persistence.

### G22: Full startup dependency checker
- **File:** `gui/app.py`
- **Action:** Complete the dependency checker from G00d with full error dialogs:
  - Use `Gtk.MessageDialog` (or `Gtk.AlertDialog` in GTK4 4.10+) for error/warning messages
  - Each missing dependency shows a specific, actionable error message (not a generic crash)
  - Hard deps (clack, ydotool, GTK4): error dialog → exit
  - Soft deps (xdotool, global shortcuts): warning dialog → continue with reduced functionality
  - ydotoold not running: setup dialog with "Retry" and "Quit" buttons
  - Install instructions must be distro-agnostic where possible:
    - Debian/Ubuntu/Mint: `sudo apt install ydotool`
    - Fedora: `sudo dnf install ydotool`
    - Arch: `sudo pacman -S ydotool`
    - openSUSE: `sudo zypper install ydotool`
    - Generic: "Install ydotool using your distribution's package manager"
- **Done:** Each dependency failure shows the correct dialog with actionable install instructions. ydotoold dialog has a working retry button.

### G23: ydotoold check with setup dialog
- **File:** `gui/app.py`
- **Action:** Implement the ydotoold-specific setup dialog:
  - Message: "Clack requires ydotoold to inject keystrokes."
  - Instructions: 
    ```
    Start the daemon:
      sudo ydotoold &
    Or add it to your startup applications.
    
    If you get a permission error, add your user to the input group:
      sudo usermod -aG input $USER
    Then log out and back in.
    ```
  - "Retry" button: re-runs `pgrep ydotoold` and dismisses dialog if found
  - "Quit" button: exits the application
  - Dialog is non-modal on the desktop (user can alt-tab to terminal to start ydotoold)
- **uinput permission error detection:**
  - If ydotool returns an error containing "permission" or "uinput", show the specific permission message
  - Test by running: `ydotool type -- test` and checking stderr for permission errors
- **Done:** Dialog appears when ydotoold is not running. Retry button works. Permission errors show specific instructions.

### G24: Global shortcut registration
- **File:** `gui/shortcuts.py`
- **Action:** Implement `ShortcutManager` with layered backend detection:
  1. **Try XDG Portal GlobalShortcuts:**
     - Check if `org.freedesktop.portal.GlobalShortcuts` is available via D-Bus
     - If available: create a session, bind the shortcut, listen for `Activated` signal
     - Use `Gio.DBusProxy` or raw `Gio.DBusConnection.call()` for D-Bus interaction
  2. **Fall back to X11 grab:**
     - Check if `$XDG_SESSION_TYPE == "x11"` or `$DISPLAY` is set
     - Use `Xlib` from `python-xlib` to call `XGrabKey` for global key capture
     - Run a listener thread that reads X events
  3. **Final fallback: no global shortcut**
     - Log a warning
     - User must use the Start/Pause button directly
  - The `ShortcutManager` exposes: `register(shortcut_str, callback)`, `unregister()`, `rebind(new_shortcut_str)`
- **Done:** Global shortcut works on X11 (via XDG Portal or X11 grab). On Wayland without portal support, falls back gracefully.

### G25: Shortcut rebinding in settings
- **File:** `gui/settings.py` + `gui/shortcuts.py`
- **Action:** Implement shortcut rebinding:
  - When user clicks the shortcut entry in settings, it enters "capture mode"
  - The next key combination pressed is captured and displayed in the entry
  - The old shortcut is unregistered and the new one is registered
  - If the new shortcut cannot be registered (conflict), show a warning and revert
  - The shortcut string is saved to settings persistence
- **Done:** User can change the global shortcut from the settings panel. New shortcut works immediately.

### G26: focus_watcher.py — xdotool polling thread
- **File:** `gui/focus_watcher.py`
- **Action:** Implement `FocusWatcher` with multi-backend support:
  - **Backend detection at startup:**
    1. Check `$XDG_SESSION_TYPE`:
       - `"x11"` → use `xdotool getactivewindow`
       - `"wayland"` → check compositor:
         - `$SWAYSOCK` set → use `swaymsg -t get_tree` to find focused window
         - `$HYPRLAND_INSTANCE_SIGNATURE` set → use `hyprctl activewindow -j`
         - Otherwise → disable focus detection, notify user
    2. Set `self._backend` to the appropriate implementation
  - **X11 polling implementation:**
    - Record target window ID: `subprocess.run(['xdotool', 'getactivewindow'])`
    - Poll every 200ms: compare current active window ID to target
    - If different: `GLib.idle_add(self._on_focus_lost)`
    - Thread stops after focus loss is detected (one-shot)
  - **Sway polling implementation:** [PROPOSED]
    - Record target window: parse focused window from `swaymsg -t get_tree`
    - Use `swaymsg -m -t subscribe '["window"]'` for event-based monitoring (no polling needed)
    - On `change == "focus"`: compare new window to target
  - **Hyprland polling implementation:** [PROPOSED]
    - Record target window: parse `hyprctl activewindow -j` for `address` or `class`
    - Poll every 200ms or use IPC socket event subscription
    - On focus change: compare to target
  - **FocusWatcher API:**
    ```python
    class FocusWatcher:
        def start(self, on_focus_lost: callable) -> bool  # Returns False if detection unavailable
        def stop(self)
        def record_target_window(self) -> str  # Returns window identifier
    ```
- **Done:** Focus loss is detected on X11 within 200ms of window change. Sway/Hyprland detection works if compositor is detected. Other compositors show a one-time warning.

### G27: Focus loss → Auto pause integration
- **File:** `gui/window.py` + `gui/clack_runner.py`
- **Action:** Wire focus loss detection to the pause mechanism:
  - When `FocusWatcher` calls `on_focus_lost()` (via `GLib.idle_add()`):
    1. Call `clack_runner.pause()`
    2. Expand the window
    3. Update UI to paused state (status light gray, button shows ▶)
    4. Stop the focus watcher thread
  - When typing resumes:
    1. Re-record the target window (user may have changed focus targets)
    2. Restart the focus watcher thread
- **Done:** Clicking away from the target window while typing auto-pauses within 200ms. Resuming restarts focus monitoring.

### G28: Speed multiplier hotkey (per chosen Option)
- **File:** `gui/shortcuts.py` + `gui/clack_runner.py`
- **Action:** Implement speed multiplier based on DECISION-G008:
  - **If Option B (CLI signal) is implemented:**
    - When speed boost hotkey is held: send SIGUSR1 to clack subprocess
    - When released: send SIGUSR1 again (toggle off)
    - No subprocess restart needed
  - **If Option B is not yet available (fall back to Option A):**
    - When speed boost hotkey is held:
      1. Call `clack_runner.pause()` (records position)
      2. Modify state temporarily: `state.wpm *= 1.5`
      3. Call `clack_runner.resume()` (restarts with higher WPM)
    - When released:
      1. Call `clack_runner.pause()`
      2. Restore original WPM: `state.wpm /= 1.5`
      3. Call `clack_runner.resume()`
  - **Speed multiplier value:** 1.5× (fixed, not user-configurable in MVP)
  - **Default hotkey:** Ctrl+Shift (held, not toggled) [PROPOSED]
- **Done:** Holding the speed boost hotkey visibly accelerates typing. Releasing returns to normal speed.

### G29: Settings persistence (save/load from ~/.config/clack/gui.json)
- **File:** `gui/settings.py` or new `gui/persistence.py`
- **Action:** Implement settings save/load:
  - Path: `~/.config/clack/gui.json` (XDG-compliant: `$XDG_CONFIG_HOME/clack/gui.json`)
  - Create directory if it doesn't exist
  - Save: serialize all user settings to JSON on every change (debounced, 500ms)
  - Load: read and deserialize on startup, falling back to defaults for missing keys
  - Schema migration: if a key is missing in the saved file, use the default value (additive schema)
  - No settings file yet: use all defaults
- **Done:** Settings persist across app restarts. Changing WPM, closing app, reopening: WPM is still changed value.

**Phase G3 Done Criteria:**
- Global shortcut starts/pauses/resumes typing from any application
- Focus loss auto-pauses on X11 and supported Wayland compositors
- Speed multiplier hotkey accelerates typing while held
- Settings persist across app restarts
- Dependency checker shows correct dialogs with distro-specific install instructions

---

## Phase G4 — Hardening

**Goal:** Test with real applications, handle edge cases, document everything, prepare for release.

### G30: Full pause/resume cycle testing with real apps
- **Applications to test with:**
  - Text editor: gedit, kate, or similar (GTK and Qt editors)
  - Browser: Firefox URL bar, Firefox text field, Chrome text field
  - Code editor: VS Code text editor pane
  - Terminal: GNOME Terminal, Konsole, Alacritty
  - Office: LibreOffice Writer
- **Test protocol for each app:**
  1. Type a known 200-character paragraph
  2. Pause at approximately character 50 (click away or press shortcut)
  3. Resume and verify remaining text is correct
  4. Verify no duplicate or missing characters
  5. Verify special characters (punctuation, numbers) are injected correctly
- **Done:** Pause/resume works correctly in all tested applications.

### G31: Focus detection testing on X11
- **Test cases:**
  - Start typing in Firefox, switch to terminal → auto-pause
  - Start typing in VS Code, click on file browser sidebar → auto-pause
  - Start typing, click on Clack window itself → should NOT pause (Clack window is expected to lose focus to target, but clicking Clack is acceptable)
  - Start typing with two monitors, switch to other monitor → auto-pause
- **Done:** Focus detection correctly identifies when the target application loses focus.

### G32: Wayland fallback behavior documented and implemented
- **File:** `gui/focus_watcher.py` + `gui/SETUP.md`
- **Action:**
  - Verify focus detection works on Sway (if test environment available)
  - Verify focus detection works on Hyprland (if test environment available)
  - Document which compositors are tested vs. untested
  - Ensure the "focus detection unavailable" message is clear and actionable
  - Ensure manual pause button works correctly as the fallback
- **Done:** Wayland fallback path tested. Documentation updated.

### G33: Error state handling
- **Scenarios to handle:**
  - clack subprocess crashes (non-zero exit, unexpected termination):
    - Detect via `process.poll()` or `process.returncode`
    - Show error dialog: "Clack process exited unexpectedly. Error: <stderr output>"
    - Return to IDLE state
  - ydotool failure during typing (e.g., ydotoold dies):
    - Detect via ydotool subprocess return code
    - Pause typing, show error: "Keystroke injection failed. Check that ydotoold is running."
  - clack binary not found at start time (was available at startup but removed):
    - Detect via `FileNotFoundError` from `subprocess.Popen`
    - Show error dialog with install instructions
  - User pastes very long text (>100KB):
    - Warn the user about long typing duration
    - Allow them to proceed or cancel
- **Done:** Each error scenario is handled gracefully with a clear message. No crashes.

### G34: Edge cases
- **Test cases:**
  - Empty text input: Start button is disabled or shows "Enter text first" [PROPOSED]
  - Single character: types one character and completes
  - Text with only whitespace: types whitespace characters correctly
  - Very long text (10,000+ characters): memory usage stays reasonable, progress bar works
  - Text with Unicode/emoji: characters pass through via ydotool (may or may not render correctly depending on ydotool handling)
  - Text with newlines: newlines are injected as Enter key presses
  - Rapid pause/resume: no race conditions, no zombie processes, no thread leaks
  - Pausing at the very beginning (position 0): resume types the full text
  - Pausing at the very end (position = len(text)): resume does nothing, shows completion
- **Done:** All edge cases handled without crashes or incorrect behavior.

### G35: Memory leak check
- **Test protocol:**
  - Start/stop typing 20 times with the same text
  - Monitor memory usage via `resource.getrusage()` or external tool
  - Verify threads are properly cleaned up after each stop (no thread count growth)
  - Verify subprocess handles are properly closed (no file descriptor leaks)
  - Use `threading.enumerate()` to verify thread count returns to baseline after typing stops
- **Done:** No thread count growth after repeated start/stop cycles. Memory usage stable.

### G36: SETUP.md written
- **File:** `gui/SETUP.md`
- **Action:** Write comprehensive setup instructions covering:
  - System requirements (Python 3.10+, GTK4, PyGObject)
  - Installing system dependencies per distro family:
    - Debian/Ubuntu/Mint: `sudo apt install ydotool xdotool python3-gi python3-gi-cairo gir1.2-gtk-4.0`
    - Fedora: `sudo dnf install ydotool xdotool python3-gobject gtk4`
    - Arch: `sudo pacman -S ydotool xdotool python-gobject gtk4`
    - openSUSE: `sudo zypper install ydotool xdotool python3-gobject typelib-1_0-Gtk-4_0`
  - Setting up ydotoold:
    - Starting the daemon: `sudo ydotoold &`
    - Persistent setup via systemd service or startup applications
    - Adding user to input group: `sudo usermod -aG input $USER`
    - udev rule for /dev/uinput: `KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"`
  - Running the GUI: `python -m gui`
  - Troubleshooting common issues:
    - "ydotoold not found" → install ydotool
    - "Permission denied" → input group + logout
    - "Focus detection not working" → install xdotool (X11) or use manual pause (Wayland)
    - "Global shortcut not working" → install xdg-desktop-portal
- **Done:** A new user can follow SETUP.md to install and run Clack GUI from scratch on any major Linux distro.

### G37: First tagged GUI release
- **Action:**
  - Verify all Phase G0–G4 tasks are complete
  - Run the full test protocol from G30 one final time
  - Tag the release: `git tag v1.1.0-gui` (or `v1.0.0-gui` depending on CLI version)
  - Push tag: `git push origin v1.1.0-gui`
  - Create a GitHub release with release notes
- **Done:** Tagged release exists on GitHub with release notes.

**Phase G4 Done Criteria:**
- Pause/resume tested with 5+ real applications
- Focus detection tested on X11 (and optionally Sway/Hyprland)
- All error states handled gracefully
- All edge cases tested
- No memory leaks or thread leaks
- SETUP.md provides complete installation instructions for 4+ distro families
- Tagged release on GitHub

---

*End of GUI-ROADMAP.md*
*Document version: 1.0*
