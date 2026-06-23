# GUI-TECH-DEBT.md — Technical Debt Register for the Clack GUI

> **Audience:** Any developer or AI agent working on the Clack GUI post-MVP.
> Each item documents a known limitation, its impact, and the planned resolution.
> Items are prioritized: **P0** (blocks users), **P1** (degrades experience), **P2** (acceptable for now).

---

## TD-G001: Subprocess Interface Instead of Direct Library Bindings

**Priority:** P2
**Introduced in:** Phase G1 (DECISION-G004)

**Current state:**
The GUI calls the `clack` CLI binary as a subprocess. Text is fed via stdin, output is read from stdout character-by-character. All communication is through Unix pipes.

**Impact:**
- One extra OS process running during typing (minimal CPU/memory overhead).
- Cannot change parameters mid-stream (e.g., speed multiplier) without restarting the subprocess. This causes a brief gap in typing.
- Inter-process communication adds ~1ms latency per character (negligible at typing speeds).
- Error handling is limited to exit codes and stderr messages. No structured error reporting.

**Resolution (post-MVP):**
Build Python bindings to `libclack` (clack-core) using PyO3. This would allow:
- Direct function calls instead of process spawning
- Mid-stream parameter changes (speed multiplier, error rate adjustments)
- Structured error handling via Python exceptions
- Elimination of pipe overhead

**Effort estimate:** Medium. Requires:
1. Adding PyO3 dependency to `clack-core` Cargo.toml
2. Exposing `ClackEngine` API as Python-callable functions
3. Building platform-specific `.so` files
4. Updating `clack_runner.py` to use the bindings instead of subprocess
5. Maintaining both subprocess and direct binding modes for fallback

**Risk:** The `ClackEvent.bytes` field contains raw terminal byte sequences (`\x08\x20\x08` for backspace). The Python bindings would need to expose semantic events (Insert, Delete, etc.) instead, which requires an API evolution in `clack-core`. See CLI DECISION-010 for the existing API stability contract.

---

## TD-G002: X11-Only Reliable Focus Detection in MVP

**Priority:** P1
**Introduced in:** Phase G3 (DECISION-G009)

**Current state:**
Focus loss detection (auto-pause when user clicks away) is fully reliable only on X11 via `xdotool getactivewindow`. On Wayland:
- Sway and Hyprland: best-effort support via compositor CLI tools (`swaymsg`, `hyprctl`) [PROPOSED]
- GNOME Wayland: no reliable method without a GNOME Shell extension installation
- KDE Wayland: untested, requires KWin scripting via D-Bus
- Other Wayland compositors: no detection, manual pause only

**Impact:**
- Users on GNOME Wayland (the most common Wayland setup) must use the manual pause button or global shortcut. Auto-pause does not work.
- This is the most significant UX gap on Wayland.
- As Wayland adoption grows, more users will be affected.

**Resolution (post-MVP):**
1. **Short-term:** Implement compositor-specific backends for GNOME (via `org.gnome.Shell.Eval` D-Bus with appropriate security handling) and KDE (via KWin scripting D-Bus API).
2. **Medium-term:** Monitor XDG Desktop Portal for a `WindowFocus` or `FocusMonitor` portal. If one is proposed and adopted, implement it as the primary backend.
3. **Long-term:** If `ext-foreign-toplevel-list` protocol gains a focus state extension and wide compositor support, use that as the compositor-agnostic solution.

**Effort estimate:** High. Each compositor backend requires:
- Protocol/API research and testing
- Separate implementation and error handling
- Testing on the specific compositor (requires test environments)
- Maintenance as compositor APIs evolve

---

## TD-G003: Character Count Position Tracking Drift

**Priority:** P2
**Introduced in:** Phase G1 (DECISION-G005)

**Current state:**
Pause position is tracked by counting characters received from clack's stdout and adjusting for backspace sequences. The GUI assumes a 1:1 correspondence between characters emitted by clack and characters appearing in the target application's text field.

**Impact:**
Position tracking can drift if the target application:
- **Autocorrects:** Changes "teh" to "the" without the GUI knowing. The GUI thinks it typed "teh" (3 chars) but the app shows "the" (3 chars) — in this case position is accidentally correct, but with other autocorrections the lengths may differ.
- **Autocompletes:** Inserts additional characters beyond what the GUI typed.
- **Transforms text:** Some rich text editors reformat input (e.g., smart quotes, em-dashes).
- **Has input filters:** Some fields reject certain characters (e.g., numeric-only fields).

In all these cases, the GUI's `pause_position` may not match the actual insertion point in the target application. Resuming from an incorrect position would cause duplicate or missing text.

**Mitigation in MVP:**
- Users are expected to type into plain text fields (text editors, browser text areas, terminals) where autocorrect/autocomplete is less common.
- If drift occurs, the user can manually adjust the text input in the GUI before resuming.

**Resolution (post-MVP):**
- **Clipboard diff approach:** After pausing, read the target field's content via clipboard (`Ctrl+A`, `Ctrl+C`), compare against the expected output, and compute the true position. This is invasive but accurate.
- **X11 clipboard monitoring:** On X11, monitor the clipboard for changes that indicate autocorrection.
- **Warning mode:** Add a "verify position" option that pauses and shows the user what's been typed vs. what was expected, allowing manual correction.

**Effort estimate:** Medium for clipboard diff, Low for warning mode.

---

## TD-G004: Speed Multiplier Implementation Gap

**Priority:** P1 (if Option A is used) / P2 (if Option B is implemented)
**Introduced in:** Phase G3 (DECISION-G008)

**Current state (if Option B CLI flag is not yet implemented):**
The speed multiplier requires restarting the clack subprocess each time the hotkey is pressed or released (Option A). This causes:
- A brief gap (~100-300ms) in typing when the speed changes
- Two subprocess start/stop cycles per speed boost session
- Potential position tracking issues if a correction sequence is interrupted by the restart

**Impact:**
- The brief typing gap is noticeable and may break the illusion of continuous human typing.
- In practice, users may avoid using the speed multiplier because of the jarring pause.

**Resolution:**
Implement Option B: add `--speed-multiplier` flag and SIGUSR1 handler to the clack CLI. This eliminates the subprocess restart entirely. The implementation requires:
1. Add `--speed-multiplier <float>` flag to `clack-cli` (default: 1.0)
2. Add `set_speed_multiplier(f64)` method to `ClackEngine` in `clack-core`
3. Register SIGUSR1 handler in `clack-cli/src/main.rs` that toggles the multiplier
4. The GUI sends `os.kill(process.pid, signal.SIGUSR1)` instead of restarting

**Effort estimate:** Low (small CLI change) + Low (GUI change to use signal instead of restart).

---

## TD-G005: keybinder3 Removal and XDG Portal Maturity

**Priority:** P1
**Introduced in:** Phase G3 (DECISION-G006)

**Current state:**
The original spec recommended `keybinder3` for global shortcuts. Research revealed it is incompatible with GTK4 and does not work on Wayland. The replacement is the XDG Desktop Portal `GlobalShortcuts` API.

**Impact:**
- XDG Portal `GlobalShortcuts` is relatively new (GNOME support landed in GNOME 48, February 2025). Early bugs may exist.
- Users on older GNOME versions (before GNOME 48) or compositors that do not implement the portal will not have global shortcut support.
- The X11 fallback (direct `XGrabKey` via `python-xlib`) works but requires the `python-xlib` package.
- On systems without portal or X11 grab support, users must click the button manually.

**Resolution (post-MVP):**
1. Monitor XDG Portal `GlobalShortcuts` maturity. As GNOME 48+ and KDE updates roll out, portal support will become widespread.
2. Consider packaging `python-xlib` as a bundled dependency in the AppImage for X11 fallback.
3. If portal bugs are reported, add workarounds or version-specific behavior.

**Effort estimate:** Low (monitoring and minor updates over time).

---

## TD-G006: No AppImage / Flatpak Distribution in MVP

**Priority:** P2
**Introduced in:** Phase G0

**Current state:**
The GUI is distributed as a Python module (`python -m gui`). Users must install system dependencies manually using their package manager. There is no single-file distributable.

**Impact:**
- Installation requires multiple steps (install Python deps, install system packages, clone repo).
- System dependency versions may vary across distros.
- No automatic updates.

**Resolution (post-MVP):**
1. **AppImage:** Bundle Python + PyGObject + GUI code into a single executable. System dependencies (ydotool, xdotool, GTK4 runtime) would still need to be installed separately.
2. **Flatpak:** Package as a Flatpak with GTK4 runtime bundled. ydotool/xdotool would need portal or flatpak-spawn access.
3. **PyPI distribution:** `pip install clack-gui` with setuptools/poetry, auto-pulling PyGObject.

**Effort estimate:** Medium for AppImage, High for Flatpak (portal permissions are complex).

---

## TD-G007: No Wayland Global Shortcuts on Older Compositors

**Priority:** P2
**Introduced in:** Phase G3 (DECISION-G006)

**Current state:**
Global shortcuts on Wayland require the XDG Desktop Portal `GlobalShortcuts` interface, which is supported in:
- GNOME 48+ (February 2025)
- KDE Plasma (via `xdg-desktop-portal-kde`)
- Some wlroots compositors (if they implement the portal backend)

Users on older compositor versions have no global shortcut support.

**Impact:**
- Significant UX degradation for users on older systems who must use Wayland (e.g., Fedora defaults to Wayland but may have older GNOME).
- The manual button fallback works but requires switching to the Clack window to pause/resume.

**Resolution (post-MVP):**
1. Time will resolve this as compositor updates roll out.
2. Document the minimum compositor versions required for full functionality in SETUP.md.
3. Consider adding compositor-specific shortcut registration as a fallback (e.g., Hyprland's `bind` config, Sway's `bindsym` config) — but this requires the user to edit compositor config files.

**Effort estimate:** Low (documentation) to Medium (compositor-specific fallbacks).

---

## TD-G008: No Multi-Monitor Awareness

**Priority:** P2
**Introduced in:** Phase G2

**Current state:**
The Clack window defaults to the top-right corner of the primary monitor. It does not detect or adapt to multi-monitor setups.

**Impact:**
- On multi-monitor setups, the window may appear on the wrong monitor (the primary, not the one with the target application).
- The window position is not saved per-monitor.

**Resolution (post-MVP):**
1. Detect which monitor the target application is on (using window geometry from xdotool/compositor).
2. Position the Clack window on the same monitor as the target.
3. Save the window position per-monitor in settings persistence.

**Effort estimate:** Low-Medium.

---

## TD-G009: Blocking ydotool Calls in Stdout Reader Thread

**Priority:** P2
**Introduced in:** Phase G1

**Current state:**
The stdout reader thread calls `subprocess.run(['ydotool', 'type', ...])` for each character. This is a blocking call that spawns a new process for every character.

**Impact:**
- At 100 WPM (IKI ~120ms), each character must complete ydotool injection within 120ms. The typical ydotool invocation takes ~5-15ms, well within this budget.
- However, at very high WPM (>120 WPM, IKI <100ms), ydotool latency could theoretically exceed the IKI, causing characters to queue up and the typing to lag behind clack's output.
- Spawning a new process for every character is wasteful. The overhead is ~5ms per invocation.

**Resolution (post-MVP):**
1. **Batch injection:** Accumulate several characters and inject them in a single `ydotool type` call. This reduces process spawn overhead but may affect timing accuracy.
2. **Direct uinput access:** Use `python-evdev` to write directly to the uinput device, bypassing ydotool entirely. This eliminates all process spawn overhead but requires reimplementing key mapping.
3. **ydotool library mode:** If ydotool exposes a library API (libydotool), use it via ctypes/cffi. Currently, ydotool only provides a CLI interface.

**Effort estimate:** Medium for python-evdev approach, Low for batch injection.

---

*End of GUI-TECH-DEBT.md*
*Document version: 1.0*
