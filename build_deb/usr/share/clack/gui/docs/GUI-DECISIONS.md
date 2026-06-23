# GUI-DECISIONS.md — Architectural Decision Log for the Clack GUI

> Every decision that shapes the GUI is recorded here with full reasoning.
> Future contributors and AI agents must read this before proposing changes.
> Each entry uses confidence markers: **[VERIFIED]** (confirmed from spec or testing),
> **[INFERRED]** (reasonable conclusion from evidence), **[PROPOSED]** (recommendation not yet confirmed).

---

## DECISION-G001: GTK4 + PyGObject as GUI Framework

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
The Clack GUI is a small floating utility window for Linux. Requirements: always-on-top, not resizable, minimal footprint, system theme integration, no Electron. The primary target is Linux Mint but the app must work across all major Linux distributions.

**Decision:** Use GTK4 with PyGObject (Python bindings via `gi.repository`).

**Evaluation:**

| Criterion | GTK4 + PyGObject | Qt6 + PySide6 | Electron | Tkinter |
|---|---|---|---|---|
| Native on Linux Mint (Cinnamon) | ✅ Yes, GTK is Cinnamon's toolkit | Requires Qt libs | Heavy, web stack | Limited widgets |
| Always-on-top support | ✅ `set_keep_above(True)` | ✅ Via window flags | ✅ Via Electron API | ⚠️ Platform-dependent |
| System theme integration | ✅ Automatic via GTK theming | ⚠️ Requires styling | ❌ Own rendering | ❌ 1990s appearance |
| Binary size / overhead | ~0 (system GTK) | ~100MB (bundled Qt) | ~200MB (Chromium) | ~0 (stdlib) |
| Python maturity | Mature, well-documented | Good, less Linux-native | N/A (JS) | Mature but limited |
| Accessibility | ✅ ATK/AT-SPI integration | ✅ Accessible | ⚠️ Web a11y | ❌ Minimal |
| Cross-distro packaging | ✅ GTK4 available on all major distros | ⚠️ Not always preinstalled | Heavy AppImage | ✅ Python stdlib |

**Consequences:**
- Python 3.10+ required (available on Linux Mint 21+, Fedora 36+, Ubuntu 22.04+, Arch rolling).
- `PyGObject` (`gi`) is the binding layer. Install via system package (`python3-gi`) or pip.
- GTK4 must be available as a system library. All modern Linux distros ship it.
- The GUI is a separate Python module (`gui/`), not compiled into the Rust binary.

**Alternatives considered:**
- **Qt6 + PySide6:** Viable but adds a large dependency not native to GNOME/Cinnamon desktops. GTK is the native choice for the primary target.
- **Electron:** Rejected. Fundamentally inappropriate for a 320px floating utility window. 200MB overhead is absurd.
- **Tkinter:** Rejected. Visually outdated, no system theme integration, limited widget set.

---

## DECISION-G002: ydotool for Keystroke Injection (not xdotool type)

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
The GUI must inject individual keystrokes into the target application. Two tools exist for this on Linux: `xdotool` (X11 only) and `ydotool` (kernel uinput, works on both X11 and Wayland).

**Decision:** Use `ydotool` for all keystroke injection. Do NOT use `xdotool type`.

**Rationale:**
- `ydotool` uses the Linux kernel's uinput subsystem. It bypasses the display server entirely, meaning it works on both X11 and Wayland without modification.
- `xdotool type` uses the X11 `XTEST` extension. It only works on X11 and fails on Wayland (even under XWayland for non-X11 windows).
- Since Wayland adoption is accelerating (GNOME defaults to Wayland, Fedora defaults to Wayland, Ubuntu defaults to Wayland since 22.04), using ydotool future-proofs the keystroke injection.

**System dependency:**
- `ydotool` binary must be installed.
- `ydotoold` daemon must be running with uinput permissions.
- User must be in the `input` group, or udev rules must grant access to `/dev/uinput`.

**Package names across distros:** [VERIFIED]

| Distro | Package |
|---|---|
| Debian/Ubuntu/Mint | `ydotool` |
| Fedora | `ydotool` |
| Arch Linux | `ydotool` |
| openSUSE | `ydotool` |

**Consequences:**
- Hard system dependency that requires daemon setup by the user.
- The GUI must check for `ydotoold` at startup and show clear setup instructions if missing.
- The `injector.py` module wraps all `ydotool` calls.

**Alternatives considered:**
- **`xdotool type`:** Rejected. X11 only. Does not work on Wayland.
- **`wtype`:** Wayland-only keyboard input tool. Does not work on X11. Would require two separate injection backends, adding complexity.
- **Direct uinput from Python:** Possible via `python-evdev` but requires reimplementing key mapping and modifier handling. `ydotool` already handles this correctly.

---

## DECISION-G003: xdotool for Window Focus Detection Only

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
Focus loss detection (auto-pause when user clicks away) requires knowing the currently active window. On X11, `xdotool getactivewindow` provides this reliably.

**Decision:** Use `xdotool` exclusively for active window detection on X11. Use compositor-specific tools as best-effort on Wayland. `xdotool` is used for **detection only**, never for keystroke injection.

**X11 implementation:**
```python
# Record target window when typing starts
result = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
target_window_id = result.stdout.strip()

# Poll every 200ms during typing
result = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
if result.stdout.strip() != target_window_id:
    trigger_pause()
```

**Wayland detection:** See DECISION-G009.

**Package names across distros:** [VERIFIED]

| Distro | Package |
|---|---|
| Debian/Ubuntu/Mint | `xdotool` |
| Fedora | `xdotool` |
| Arch Linux | `xdotool` |
| openSUSE | `xdotool` |

**Consequences:**
- `xdotool` is a soft dependency. If missing, focus detection is disabled (not a fatal error).
- Focus detection is reliable on X11, unreliable on Wayland (see DECISION-G009).
- The `focus_watcher.py` module encapsulates all xdotool interaction.

**Important clarification:**
- `xdotool getactivewindow` does **not** work under XWayland. It relies on `_NET_ACTIVE_WINDOW` which Wayland does not implement. [VERIFIED]
- On pure Wayland, xdotool is useless for window detection. [VERIFIED]

**Alternatives considered:**
- **`wmctrl`:** Provides similar functionality but less widely installed. No advantage over xdotool.
- **`xprop`:** Lower-level, harder to use. xdotool provides the simpler API.

---

## DECISION-G004: Subprocess Interface (not Direct libclack Bindings)

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
The GUI could either call `clack` as a subprocess (piping stdin/stdout) or link directly to `libclack` (the Rust library) via Python FFI bindings.

**Decision:** Use the subprocess interface for the MVP. The GUI spawns `clack` as a child process, feeds text via stdin, and reads character-by-character output from stdout.

**Rationale:**
1. **Zero coupling.** The GUI and CLI are completely independent. A bug in the GUI cannot corrupt the simulation engine. A CLI update does not require GUI recompilation.
2. **Simplicity.** subprocess.Popen is trivial compared to setting up `ctypes` or `PyO3` bindings for a Rust library.
3. **Testing.** The CLI can be tested independently. The GUI can be tested with a mock `clack` binary.
4. **The CLI already handles timing.** The `clack` binary sleeps internally between character emissions. The GUI simply reads and injects. No timing logic needed in Python.

**Trade-offs:**
- One extra process running (minimal overhead for a utility this small).
- Inter-process communication overhead (negligible — one byte at a time, ~120ms between emissions at 100 WPM).
- Cannot send signals mid-stream to change parameters (e.g., speed multiplier). Requires subprocess restart.

**Consequences:**
- The subprocess interface is the integration contract. Do not modify clack CLI's stdout format.
- Pause = SIGTERM + record position. Resume = new subprocess with sliced text.
- Speed multiplier requires either subprocess restart (Option A) or a new CLI flag (Option B). See DECISION-G008.

**Alternatives considered:**
- **Direct Python bindings (PyO3):** Would eliminate process overhead and allow mid-stream parameter changes. Deferred to post-MVP as it requires building and distributing a compiled Python extension for each platform.

---

## DECISION-G005: Character Count for Pause Position Tracking

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
When the user pauses and resumes, the GUI must know exactly where in the original text to resume from. The position is tracked by counting characters received from clack's stdout.

**Decision:** Track net character position by incrementing on each normal character and decrementing on each backspace sequence.

**Logic:**

```
Normal character from stdout:     position += 1
Backspace sequence (08 20 08):    position -= 1
```

On resume: `remaining_text = original_text[position:]`

**Edge cases:**
- If clack emits a correction sequence (error + backspace + retype), the position correctly reflects the net text consumed because decrements and increments cancel out for the corrected character.
- If clack emits a delayed correction (backspace N chars, retype N chars), the position returns to the pre-error point and then advances past it correctly.

**Risks:**
- If the target application performs autocorrect, autocomplete, or text transformation, the GUI has no way to detect this. The injected text and the actual text in the target app may diverge.
- This is an inherent limitation of the subprocess approach (clack doesn't know what the target app does with its input).

**Consequences:**
- The `ClackState` object maintains `pause_position` as a thread-safe integer.
- The stdout reader thread is the only writer to this field.
- On resume, the main thread reads the position to slice the remaining text.

**Alternatives considered:**
- **Clipboard diff approach:** After pausing, read the target app's text field via clipboard, diff against expected, and compute the true position. This would handle autocorrect but is complex and invasive. Deferred to post-MVP.

---

## DECISION-G006: Global Shortcut Library Choice

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
A global hotkey must work system-wide even when the Clack window is not focused. The original spec suggested `keybinder3` (`gir1.2-keybinder-3.0`). Research revealed critical compatibility issues.

**Research findings:** [VERIFIED]
- **keybinder3 does NOT work with GTK4.** It was designed exclusively for GTK3. There is no GTK4 support and none is planned. [VERIFIED]
- **keybinder3 does NOT work on Wayland.** It relies on X11 protocols to intercept key events globally. [VERIFIED]
- **keybinder3 is a dead end** for any modern GTK4/Wayland application. [VERIFIED]

**Decision:** Use a layered approach for global shortcuts:

1. **Primary (modern Linux):** XDG Desktop Portal `GlobalShortcuts` API (`org.freedesktop.portal.GlobalShortcuts`) via D-Bus calls.
   - Supported in GNOME 48+ (February 2025) and KDE Plasma. [VERIFIED]
   - Works on both X11 and Wayland. [VERIFIED]
   - The correct, standards-based approach for modern Linux desktops. [VERIFIED]

2. **Fallback (older X11 systems):** Direct X11 key grab via `python-xlib` or the Xlib `XGrabKey` API.
   - Works only on X11 (including XWayland).
   - Well-tested, reliable.

3. **Final fallback:** No global shortcut. User must click the Start/Pause button in the Clack window.
   - Always available regardless of platform or compositor.

**Implementation in `shortcuts.py`:**
```python
class ShortcutManager:
    def __init__(self):
        self._backend = self._detect_backend()
    
    def _detect_backend(self):
        # Try XDG Portal first
        if self._portal_available():
            return PortalShortcutBackend()
        # Fall back to X11 grab
        if self._x11_available():
            return X11ShortcutBackend()
        # No global shortcuts
        return NullShortcutBackend()
```

**Consequences:**
- keybinder3 is NOT a dependency. Remove from all dependency lists.
- `shortcuts.py` must implement the backend detection and fallback logic.
- XDG Portal GlobalShortcuts requires `xdg-desktop-portal` v1.14+ and a portal backend (`xdg-desktop-portal-gnome` or `xdg-desktop-portal-kde`).
- The global shortcut is a soft dependency — the app works without it, just without the hotkey.

**Alternatives considered:**
- **keybinder3:** Rejected. Does not work with GTK4 or Wayland. [VERIFIED]
- **Compositor-specific protocols:** Each compositor has its own shortcut API. Too fragmented to support in the MVP.
- **System-level tools (keyd, input-remapper):** Not suitable for app-integrated hotkeys; require separate system configuration.

---

## DECISION-G007: Default Global Shortcut

**Status:** NEW
**Confidence:** [PROPOSED]

**Context:**
The default shortcut must not conflict with common Linux desktop environment shortcuts, VS Code shortcuts, browser shortcuts, or terminal emulator shortcuts.

**Research findings:** [VERIFIED]

| Candidate | Conflicts |
|---|---|
| `Super+Space` | ❌ GNOME input source switcher (critical conflict) |
| `Ctrl+Shift+Space` | ❌ VS Code parameter hints, LibreOffice non-breaking space, IBus |
| `Ctrl+`` | ❌ VS Code terminal toggle (critical conflict) |
| `Ctrl+Shift+Y` | ⚠️ VS Code Debug Console toggle (minor conflict) |
| `Ctrl+Shift+F12` | ✅ No conflicts found across any major app or DE |

**Decision:** Default global shortcut is **`Ctrl+Shift+F12`**. [PROPOSED]

**Rationale:**
- ✅ Not reserved by GNOME Shell, KDE Plasma, or Cinnamon [VERIFIED]
- ✅ Not used by VS Code (no default binding) [VERIFIED]
- ✅ Not used by Firefox or Chrome [VERIFIED]
- ✅ Not used by terminal emulators [VERIFIED]
- ✅ Not used by LibreOffice or other major applications [VERIFIED]
- ✅ F12 is rarely pressed accidentally [INFERRED]
- ✅ `Ctrl+Shift+F-key` is a recognized "power user" shortcut pattern [INFERRED]
- Note: `Ctrl+F12` (without Shift) is "Show Desktop" in KDE Plasma, but `Ctrl+Shift+F12` is free [VERIFIED]

**Ergonomic concern:** F12 is in the function key row, which requires more hand movement than letter keys. However, this shortcut is only used to start/pause/resume (infrequent), not for continuous use.

**The shortcut must be rebindable** in the Advanced Settings panel (see `settings.py`).

**Consequences:**
- The settings panel shows the current shortcut and allows rebinding by capturing the next key combination.
- The Start button label shows the shortcut hint: `▶  Start Typing    Ctrl+Shift+F12`
- Settings persistence stores the shortcut string in `~/.config/clack/gui.json`.

---

## DECISION-G008: Speed Multiplier Implementation

**Status:** NEW
**Confidence:** [PROPOSED]

**Context:**
While typing is active, the user can hold a key combination to temporarily speed up typing by 1.5×. Two approaches were considered:

**Option A — Restart with modified WPM:**
When speed hotkey is held, pause at current position, restart clack subprocess with `WPM × 1.5`, resume from `pause_position`. Release hotkey: pause again, restart with original WPM.
- **Pro:** No CLI changes needed.
- **Con:** Causes a brief gap in typing each time the hotkey is pressed/released. Two subprocess restarts per speed boost session.

**Option B — Speed multiplier signal in clack CLI:**
Add a `--speed-multiplier` flag to the clack CLI. The GUI sends SIGUSR1 to toggle the multiplier on/off. The CLI adjusts its internal timing dynamically.
- **Pro:** No typing gap. Seamless speed change.
- **Con:** Requires a CLI code change (adding signal handling to clack-cli).

**Decision:** Plan for **Option B** (CLI signal-based speed multiplier). [PROPOSED]

**Rationale:**
- Option A causes noticeable gaps in typing when the hotkey is pressed/released. This breaks the illusion of human typing.
- Option B requires a small CLI change but provides a significantly better user experience.
- The CLI change is additive (new flag `--speed-multiplier` with default 1.0) and does not break existing behavior.

**CLI change required (prerequisite for GUI Phase G3):**
1. Add `--speed-multiplier` flag to `clack-cli` (default: 1.0).
2. Register SIGUSR1 handler in `clack-cli` that toggles between `1.0` and the configured multiplier value.
3. The multiplier is applied to IKI calculation in `clack-core` (new `set_speed_multiplier()` method on `ClackEngine`).

**Consequences:**
- This is a prerequisite task that must be completed before GUI Phase G3 (task G28).
- The CLI change must be made on the `dev` branch.
- If Option B is not approved by the project owner, fall back to Option A.
- The speed multiplier hotkey default: **`Ctrl+Shift`** (held, not toggled). [PROPOSED]
  - Note: holding `Ctrl+Shift` alone does not trigger most shortcuts (shortcuts require a third key). This makes it usable as a "hold to boost" key combination. [INFERRED]

---

## DECISION-G009: Wayland Focus Detection Approach and Limitations

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
Wayland's security model explicitly prevents applications from monitoring other windows' focus state. There is no compositor-agnostic API for this. Each compositor has its own approach, and some have no approach at all.

**Research findings:** [VERIFIED]

| Compositor | Detection Method | Status |
|---|---|---|
| **Native X11** | `xdotool getactivewindow` | ✅ Reliable [VERIFIED] |
| **XWayland** | `xdotool getactivewindow` | ❌ Does not work (no `_NET_ACTIVE_WINDOW` on Wayland) [VERIFIED] |
| **Sway** (wlroots) | `swaymsg -t get_tree` + JSON parse, or event subscription | [PROPOSED] Best-effort |
| **Hyprland** (wlroots) | `hyprctl activewindow -j` or IPC socket | [PROPOSED] Best-effort |
| **GNOME (Mutter)** | D-Bus via "Focused Window D-Bus" GNOME Shell Extension, or `org.gnome.Shell.Eval` (restricted) | [PROPOSED] Unreliable — requires user to install extension |
| **KDE (KWin)** | KWin scripting via D-Bus, or `kdotool` | [PROPOSED] Untested |

**Decision:** Implement a multi-backend focus detection system in `focus_watcher.py`:

1. **Detect display server type** at startup using `$XDG_SESSION_TYPE` environment variable.
2. **X11:** Use `xdotool getactivewindow` (polling every 200ms). [VERIFIED]
3. **Wayland — Sway:** Use `swaymsg -t get_tree` to find the focused window. Detect via `$SWAYSOCK` environment variable. [PROPOSED]
4. **Wayland — Hyprland:** Use `hyprctl activewindow -j`. Detect via `$HYPRLAND_INSTANCE_SIGNATURE` environment variable. [PROPOSED]
5. **Wayland — Other compositors:** Focus detection is disabled. Show a one-time notice to the user. [VERIFIED]

**Consequences:**
- Focus detection is reliable on X11 and Sway/Hyprland. Unreliable or absent on GNOME Wayland and KDE Wayland in the MVP.
- Users on unsupported Wayland compositors must use the manual pause button or shortcut.
- The `focus_watcher.py` module handles backend detection and provides a uniform interface to the rest of the GUI.
- GNOME Wayland and KDE Wayland focus detection are deferred to post-MVP (requires extension installation or complex D-Bus scripting).

**Documentation requirement:**
- The SETUP.md file must clearly document which compositors support focus detection and which do not.
- The GUI must show a clear, non-cryptic message when focus detection is unavailable.

---

## DECISION-G010: Threading Model (Four Threads, GLib.idle_add)

**Status:** NEW
**Confidence:** [VERIFIED]

**Context:**
GTK4 requires all UI updates to happen on the main thread. The GUI must read from two subprocess pipes (stdout, stderr) and poll for focus changes concurrently. These operations are blocking and cannot run on the main thread.

**Decision:** Use four threads as specified in GUI-ARCHITECTURE.md §3.

| Thread | Purpose | Blocking Operation | UI Update Method |
|---|---|---|---|
| Main | GTK event loop | None (never blocks) | Direct GTK calls |
| Stdout Reader | Read clack stdout, inject via ydotool | `process.stdout.read(1)` | `GLib.idle_add()` |
| Stderr Reader | Read clack stderr, parse state | `for line in process.stderr` | `GLib.idle_add()` |
| Focus Watcher | Poll active window | `subprocess.run(['xdotool', ...])` | `GLib.idle_add()` |

**Thread safety:**
- All shared state lives in the `ClackState` object in `state.py`.
- All access to `ClackState` is protected by `threading.Lock()`.
- Threads must never hold the lock while performing I/O.
- Threads are created as daemon threads (`daemon=True`) so they do not prevent process exit.

**Thread lifecycle:**
- Background threads are created when typing starts.
- They are stopped (via `threading.Event`) when typing is paused or complete.
- On pause: subprocess is SIGTERM'd, reader threads detect EOF and exit, focus watcher is stopped.
- On resume: new threads are created for the new subprocess.

**Consequences:**
- Thread creation/destruction happens on every pause/resume cycle. This is acceptable because Python threads are lightweight and the pause/resume frequency is low (human-initiated).
- No thread pool or executor is used. Simple `threading.Thread` with daemon=True.
- `GLib.idle_add()` is the only cross-thread communication mechanism. No `queue.Queue`, no `Event` for UI updates.

**Alternatives considered:**
- **`asyncio`:** GTK4 supports integration with `asyncio` via `GLib` event loop. However, subprocess pipe reads are fundamentally blocking in Python (even with `asyncio.subprocess`, reading one byte at a time with the required blocking semantics is awkward). Threads are simpler for this use case.
- **`GLib.timeout_add()` polling:** Polling stdout from the main thread using `GLib.timeout_add()` would require non-blocking reads. Python's `subprocess.Popen` with `os.read()` and `os.set_blocking(False)` is unreliable on all platforms. Threads are more robust.

---

*End of GUI-DECISIONS.md*
*Document version: 1.0*
