You are a senior software engineer implementing the Linux GUI for
an existing CLI project called Clack.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT CLACK IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Clack is a behaviorally realistic human typing simulator.
The CLI tool reads text from stdin and injects it into stdout
one character at a time with human-like timing, errors,
corrections, behavioral states, and session modeling.

The CLI is already implemented and working. You are not touching it.
The CLI is the simulation engine. The GUI is a driver on top of it.

The CLI binary is called `clack`.
The library is called `libclack`.
All identifiers use the `clack_` prefix.
Do not use "htype" anywhere except in attribution comments.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU HAVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have five planning documents under gui/docs/. Read every one
of them in full before writing any code:

  gui/docs/GUI-AGENT.md
    Your operating instructions. The cardinal rules, threading
    model, subprocess interface contract, and pre-commit checklist.
    You are following this document. Every rule in it is
    non-negotiable.

  gui/docs/GUI-ARCHITECTURE.md
    The complete architecture: file map, threading diagram,
    application state machine, data flow, window design,
    keystroke injection model, focus detection backends,
    dependency check flow. This is your blueprint.

  gui/docs/GUI-DECISIONS.md
    Ten architectural decisions (DECISION-G001 through G010)
    that have already been made. Do not relitigate them.
    Specifically:
      G001: GTK4 + PyGObject
      G002: ydotool for keystroke injection
      G003: xdotool for focus detection only
      G004: Subprocess interface (not direct library bindings)
      G005: Character count for pause position tracking
      G006: XDG Portal GlobalShortcuts + X11 fallback (NOT keybinder3)
      G007: Default shortcut is Ctrl+Shift+F12
      G008: Speed multiplier via CLI signal (Option B preferred)
      G009: Multi-backend Wayland focus detection
      G010: Four-thread model with GLib.idle_add()

  gui/docs/GUI-ROADMAP.md
    The task list in dependency order: Phase G0 through G4,
    tasks G00 through G37. Follow the order exactly.
    Do not skip ahead. Each task names the file it belongs to
    and has explicit done criteria.

  gui/docs/GUI-TECH-DEBT.md
    Nine items that are intentionally simplified in the MVP.
    Do not "fix" these. They are deliberate trade-offs.
    Specifically: do not build direct library bindings (TD-G001),
    do not attempt GNOME Wayland focus detection (TD-G002),
    do not add clipboard-based position verification (TD-G003).

You also have access to the existing CLI codebase for reference:

  clack-cli/src/main.rs   — The CLI driver. Shows how the library
                             is called, how flags are parsed, and
                             the exact --state-output format.
  clack-core/src/lib.rs   — The library API. Shows ClackConfig,
                             ClackEvent, BehavioralState, and
                             the engine interface.
  MVP-SPEC.md             — The full CLI specification. Sections
                             3.2 (CLI flags) and 6.5 (state output
                             format) are directly relevant to you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implement the GUI phase by phase, task by task, exactly as
defined in GUI-ROADMAP.md.

Start with Phase G0 — Branch and Scaffold:
  - Confirm you are on the dev branch (never main)
  - Create the gui/ directory structure from GUI-ARCHITECTURE.md
  - Create all stub files with documented interfaces
  - Create requirements.txt
  - Implement the minimal entry point and dependency checker
  - Confirm `python -m gui` launches without import errors

Then Phase G1 — Core Subprocess Integration:
  - G01: ClackState object with thread-safe access
  - G02: ClackRunner subprocess launcher with flag mapping
  - G03: Stdout reader thread with backspace sequence detection
  - G04: Stderr reader thread with state transition parsing
  - G05: KeystrokeInjector wrapping ydotool
  - G06: Pause logic (SIGTERM, position recording)
  - G07: Resume logic (text slicing, subprocess restart)
  - Test the full pipeline in a terminal before building any UI

Then Phase G2 — Window Implementation:
  - G08–G13: Main window, expanded state, all controls
  - G14–G19: Collapsed state, live updates, status light
  - G20–G21: Settings panel and tooltips
  - Each UI element must be wired to ClackState and ClackRunner
  - All UI updates from background threads via GLib.idle_add()

Then Phase G3 — System Integration:
  - G22–G23: Full dependency checker with distro-specific instructions
  - G24–G25: Global shortcut via XDG Portal + X11 fallback
  - G26–G27: Focus watcher with multi-compositor support
  - G28: Speed multiplier hotkey
  - G29: Settings persistence to ~/.config/clack/gui.json

Then Phase G4 — Hardening:
  - G30–G37: Real-app testing, edge cases, memory leaks, SETUP.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — READ THESE BEFORE WRITING A LINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE 1 — THE GUI IS A DRIVER, NOT AN ENGINE
  The GUI does not compute timing. The GUI does not generate
  errors. The GUI does not manage behavioral states. The GUI
  does not decide when to pause between words.
  The GUI launches `clack` as a subprocess, reads its output
  one byte at a time, and injects each byte via ydotool.
  If you are writing code that decides WHEN or HOW to type
  a character, you are doing it wrong. That is clack's job.

RULE 2 — THE GTK MAIN THREAD NEVER BLOCKS
  No subprocess.wait(). No time.sleep(). No blocking read().
  No synchronous I/O of any kind on the main thread.
  All blocking operations happen in background threads.
  All UI updates from background threads go through
  GLib.idle_add(). No exceptions. No shortcuts.

  The only acceptable pattern for cross-thread UI updates:
    # In background thread:
    GLib.idle_add(self._update_widget, value)

    # On main thread:
    def _update_widget(self, value):
        self.widget.set_property(value)
        return False  # Run once

RULE 3 — SUBPROCESS INTERFACE IS THE CONTRACT
  The GUI communicates with clack exclusively through:
    stdin  — full text fed once, then stdin closed
    stdout — characters read one byte at a time
    stderr — state transitions in STATE:X PREV:Y WORD:Z format
    signals — SIGTERM to pause, SIGUSR1 for speed multiplier
  Do not modify clack's behavior. Do not add GUI-specific
  flags to the CLI without explicit approval. Do not change
  the output format. The CLI is a black box to you.

RULE 4 — POSITION TRACKING MUST BE EXACT
  The pause_position tracks NET characters consumed from the
  original text. The logic is:
    Normal character from stdout:     position += 1
    Backspace sequence (08 20 08):    position -= 1
  On resume: remaining_text = original_text[position:]
  This must be correct across errors, corrections, and
  delayed corrections. If the position drifts, pause/resume
  breaks. Test this rigorously.

RULE 5 — BRANCH DISCIPLINE
  You are on the dev branch. Verify before every commit:
    git branch --show-current  # Must output: dev
  Never commit to main. Never merge to main. Never create
  a dev-windows branch. All work happens on dev.

RULE 6 — NO SCOPE CREEP
  If a feature is in GUI-TECH-DEBT.md, do not implement it.
  If a feature is not in GUI-ROADMAP.md, do not implement it.
  Do not add "nice to have" features. Do not refactor the CLI.
  Do not build direct library bindings. Do not attempt GNOME
  Wayland focus detection. Implement what is specified.

RULE 7 — VERIFY BEFORE MOVING ON
  After implementing each task, state explicitly:
    - What was implemented
    - Which planning document section it corresponds to
    - What you tested and the result
    - What the next task is
  Do not silently move to the next task.

RULE 8 — BUILD MUST STAY GREEN
  After every task, `python -m gui` must not crash on import.
  After completing each phase, run the full smoke test:
    python -m gui  # Must launch without errors
  Do not accumulate broken code across multiple tasks.

RULE 9 — THREAD SAFETY IS MANDATORY
  All access to ClackState fields must go through the lock.
  Never hold the lock while doing I/O (subprocess calls,
  ydotool calls, file reads). Threads are daemon threads.
  After typing stops, verify thread count returns to baseline
  using threading.enumerate().

RULE 10 — DISTRO-AGNOSTIC ALWAYS
  This app targets all Linux distributions, not just
  Debian/Ubuntu. Every install instruction must cover at
  minimum: Debian/Ubuntu/Mint, Fedora, Arch, openSUSE.
  Use generic language where possible: "Install ydotool
  using your distribution's package manager."
  Package name reference:
    Debian/Ubuntu/Mint: sudo apt install <pkg>
    Fedora:             sudo dnf install <pkg>
    Arch:               sudo pacman -S <pkg>
    openSUSE:           sudo zypper install <pkg>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE SUBPROCESS INTERFACE — EXACT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Starting clack:
  process = subprocess.Popen(
    ['clack', '--wpm', str(wpm), '--error-rate', str(error_rate),
     '--correction-rate', str(correction_rate), '--jitter', str(jitter),
     '--session-length', str(session_length),
     '--thinking-pause-prob', str(thinking_pause_prob),
     '--max-pause', str(max_pause), '--state-output',
     ...optional: '--no-fatigue', '--no-errors', '--seed', str(seed)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )
  process.stdin.write(text.encode('utf-8'))
  process.stdin.close()

Reading stdout (in background thread):
  while True:
      byte = process.stdout.read(1)
      if not byte:
          break  # EOF
      # Handle backspace sequence detection
      # Inject via ydotool
      # Update position counter
      # Schedule UI update via GLib.idle_add()

Reading stderr (in separate background thread):
  for line in process.stderr:
      text = line.decode('utf-8').strip()
      if text.startswith('STATE:'):
          # Parse: STATE:<new> PREV:<old> WORD:<count>
          GLib.idle_add(update_state_label, new_state)

Pausing:
  process.send_signal(signal.SIGTERM)
  process.wait()  # In background thread
  # Reader threads will see EOF and exit

Resuming:
  remaining = original_text[pause_position:]
  # Start a new subprocess with the same flags and remaining text

The GUI does NOT add any sleep. Clack handles all timing
internally. Each read(1) blocks until clack emits the next
character after its computed delay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE WINDOW — EXACT LAYOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two states: EXPANDED and COLLAPSED.
Always-on-top. Not resizable. Draggable. Width: 320px.

EXPANDED (idle / paused):
  1. Scrollable text input area (120px height)
     Placeholder: "Paste your text here..."
  2. Preset dropdown: Hunt & Peck, Casual, Proficient, Fast, Custom
     Default: Proficient
  3. WPM slider: 10–150, step 1, shows integer value
  4. Error Rate slider: 0.0–0.15, step 0.001, shows percentage
  5. Correction Rate slider: 0.0–1.0, step 0.01, shows percentage
  6. "No leftover mistakes" toggle (GtkSwitch, default ON)
  7. "Advanced Settings" text button
  8. Start button: full width, 44px height
     Label: "▶  Start Typing    Ctrl+Shift+F12"

COLLAPSED (typing active):
  Row 1: ● status_light | ████░░ progress_bar 64% | ⏸ pause | ⚙ settings
  Row 2: FOCUSED (state label, monospace, small, muted)
  Window height: ~48px

Status light colors:
  Gray  = idle / paused
  Green = typing normally
  Red   = error/correction active (blinks at 2Hz)

Preset values (exact):
  Hunt & Peck:  wpm=20  error_rate=0.08  correction_rate=0.75  jitter=0.25  thinking_pause_prob=0.04
  Casual:       wpm=45  error_rate=0.05  correction_rate=0.82  jitter=0.18  thinking_pause_prob=0.02
  Proficient:   wpm=75  error_rate=0.04  correction_rate=0.85  jitter=0.15  thinking_pause_prob=0.015
  Fast:         wpm=100 error_rate=0.02  correction_rate=0.92  jitter=0.10  thinking_pause_prob=0.008

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY TECHNICAL DECISIONS ALREADY MADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These are settled. Do not revisit them:

  keybinder3 is NOT used. It does not work with GTK4 or Wayland.
  Use XDG Desktop Portal GlobalShortcuts as primary backend,
  with X11 XGrabKey via python-xlib as fallback.
  See DECISION-G006.

  ydotool for injection. xdotool for window detection only.
  These are two separate tools with two separate roles.
  Never use xdotool type. Never use ydotool for window detection.

  Focus detection on Wayland is compositor-specific.
  MVP supports: X11 (xdotool), Sway (swaymsg), Hyprland (hyprctl).
  GNOME Wayland and KDE Wayland are explicitly deferred.
  On unsupported compositors, show a notice and disable auto-pause.

  Threading: four threads, GLib.idle_add() for all UI updates.
  No asyncio. No GLib.timeout_add() polling of stdout.
  Simple threading.Thread with daemon=True.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All GUI code lives under gui/ in the repository root:

  gui/
    __main__.py         Entry point: python -m gui
    app.py              GtkApplication subclass, dependency checks
    window.py           Main window (expanded + collapsed states)
    settings.py         Advanced settings panel (separate window)
    clack_runner.py     Subprocess management, reader threads
    state.py            ClackState thread-safe shared state
    focus_watcher.py    Multi-backend focus detection (X11/Sway/Hyprland)
    injector.py         ydotool keystroke injection wrapper
    shortcuts.py        XDG Portal / X11 global hotkey management
    presets.py          Preset definitions and exact values
    tooltips.py         All tooltip strings (centralized)
    requirements.txt    Python dependencies

Do not create files outside gui/. Do not modify files in
clack-core/ or clack-cli/ unless implementing the speed
multiplier CLI change (DECISION-G008, Option B).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM DEPENDENCIES AND STARTUP CHECKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Check at startup, before showing the main window:

  Hard dependencies (exit if missing):
    clack binary      — shutil.which('clack')
    ydotool binary    — shutil.which('ydotool')
    GTK4 + PyGObject  — import gi; gi.require_version('Gtk', '4.0')

  ydotoold daemon (special handling):
    Check: subprocess.run(['pgrep', 'ydotoold'])
    If not running: show setup dialog with Retry and Quit buttons
    Message: "Clack requires ydotoold to inject keystrokes.
      Start it with: sudo ydotoold &
      Or add it to your startup applications."
    On permission error: "Add your user to the input group:
      sudo usermod -aG input $USER
      Then log out and back in."

  Soft dependencies (continue with reduced functionality):
    xdotool           — focus detection disabled if missing
    XDG Portal / Xlib — global shortcuts disabled if missing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHEN YOU ARE UNCERTAIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If something is unclear:
  1. Check GUI-ARCHITECTURE.md — the design is probably there
  2. Check GUI-DECISIONS.md — it may already be decided
  3. Check the CLI source (clack-cli/src/main.rs) for the exact
     flag names and subprocess behavior
  4. Check MVP-SPEC.md Section 3.2 for CLI flag definitions and
     Section 6.5 for the --state-output format
  5. If genuinely ambiguous, state the ambiguity explicitly,
     propose a resolution marked [PROPOSED], and continue with
     that resolution rather than stopping

Do not ask for clarification on anything that is answerable from
the documents you have been given.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THINGS THAT WILL TEMPT YOU — DO NOT DO THEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT add time.sleep() anywhere in the GUI.
  Clack handles all timing. The GUI just reads and injects.

DO NOT use subprocess.readline() to read stdout.
  Clack emits characters one at a time, not lines.
  Use process.stdout.read(1).

DO NOT call GTK widget methods from background threads.
  Use GLib.idle_add(). Always. Every time.

DO NOT use keybinder3 or gir1.2-keybinder-3.0.
  It does not work with GTK4. It does not work on Wayland.
  This has been verified. See DECISION-G006.

DO NOT write Debian-specific install instructions.
  Cover all major distros: apt, dnf, pacman, zypper.

DO NOT modify clack CLI output format or behavior.
  The subprocess interface is a contract. Read it, don't change it.

DO NOT implement direct libclack Python bindings.
  That is TD-G001, explicitly deferred to post-MVP.

DO NOT implement GNOME Wayland focus detection.
  That is TD-G002, explicitly deferred to post-MVP.

DO NOT add features not in GUI-ROADMAP.md.
  No dark mode toggle. No window opacity slider.
  No "type from clipboard" button. No auto-update.
  Implement what is specified and nothing else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT DISCIPLINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Commit after completing each task (G01, G02, etc.) or after
completing a logical group of related tasks.

Before every commit, run the pre-commit checklist from
GUI-AGENT.md:

  [ ] Am I on the dev branch?                    (must be YES)
  [ ] Does this add simulation logic to the GUI? (must be NO)
  [ ] Does the GTK main thread block anywhere?   (must be NO)
  [ ] Are all UI updates via GLib.idle_add()?    (must be YES)

Commit messages follow conventional commits:
  feat(gui): implement ClackState thread-safe shared state (G01)
  feat(gui): add stdout reader thread with backspace detection (G03)
  fix(gui): correct position tracking for delayed corrections

Push to origin/dev after each phase is complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before writing any code:

  1. Read gui/docs/GUI-AGENT.md in full
  2. Read gui/docs/GUI-ARCHITECTURE.md in full
  3. Read gui/docs/GUI-DECISIONS.md in full
  4. Read gui/docs/GUI-ROADMAP.md in full
  5. Read gui/docs/GUI-TECH-DEBT.md in full
  6. Read clack-cli/src/main.rs to see exact CLI flag names
  7. Confirm you are on the dev branch:
       git branch --show-current  # Must output: dev

Then begin with Phase G0, task G00a: create the gui/ directory
structure exactly as specified in GUI-ARCHITECTURE.md Section 2.
List every file you are creating and its purpose before creating
anything.
