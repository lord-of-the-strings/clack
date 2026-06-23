# Clack

Clack is an extremely realistic typing simulator that translates static text or standard input into a dynamic, human-like keystroke stream. 

*Clack is heavily inspired by and credits its core idea to **htype** (https://github.com/lord-of-the-strings/htype), originally created by **Aadity Setu**.* 

If you are generating screencasts, terminal recordings, or automated UI demonstrations, regular typing automation tools like `xdotool` or basic sleep scripts look robotic and fake. Clack utilizes probabilistic models to simulate how a real human types, complete with motor-control panics, realistic typing speeds, error rates, and layout-aware key travel distances.

---

## ✨ New in V2: Graphical User Interface!

Clack 2.0 introduces a brand new, fully-featured **GTK4 Graphical Interface** for Linux! You no longer need to rely purely on the command line to configure your virtual typist.

- **Live Tuning:** Adjust WPM, Error Rates, and Correction probability via sliders and instantly see the results.
- **Typing Presets:** Switch between pre-configured typing styles like *Casual*, *Hunt & Peck*, *Proficient*, and *Fast* on the fly.
- **No Leftover Mistakes:** A highly-requested toggle that ensures your final text is 100% correct, while still authentically simulating the process of making and fixing mistakes as it types.
- **Global Shortcuts (WIP):** Pause, resume, or trigger speed-boosts globally using keyboard shortcuts without needing to focus the application window.
- **Cross-Window Compatibility:** Type directly into any target application window using secure `/dev/uinput` injection.

---

## 🌟 Features

Clack doesn't just add a random delay between keypresses. It simulates an entire virtual typist sitting at a keyboard. It employs several advanced mechanics to achieve this:

- **Bimodal Timing Distributions**: Human typing has two distinct rhythms. We type adjacent letters in a word quickly, but pause longer at word boundaries, punctuation, and capital letters. Clack models this using Gaussian distributions.
- **Euclidean Key Distances**: Clack understands the physical layout of your keyboard (QWERTY, Dvorak, Colemak, AZERTY). Moving your finger from 'a' to 'z' is faster than moving from 'a' to 'p'. Clack dynamically calculates the physical travel distance between consecutive keys to adjust the inter-key timing.
- **Probabilistic Errors & Corrections**: Humans make mistakes! Clack can simulate typos (hitting an adjacent key), transpositions (swapping two letters), and omissions. It then realistically realizes the mistake, pauses, backspaces, and re-types the correct characters.
- **Panic Events**: Sometimes, a typist's brain glitches. Clack simulates rare "Panic Events" where the virtual typist accidentally holds down a key for too long (a stuck-key burst) or gets confused and re-types the prefix of the current word before backspacing to fix it.
- **Code-Aware Typing Mode**: Typing source code requires more cognitive load than typing prose. When enabled, Clack tracks the depth of nested brackets `{} [] ()` and slows down the typing speed for deeper scopes. It also detects complex identifiers (`snake_case`, `camelCase`) and types them more carefully to reflect real programming behavior.

---

## 🚀 Setup and Running

Clack is built in Rust for maximum performance, with a modern GTK4 Python frontend. 

### Option 1: Debian/Ubuntu Linux (.deb)
If you are using a Debian-based Linux distribution (Ubuntu, Mint, Pop!_OS, etc.), the easiest way to install Clack is using the `.deb` package. This installs the `clack` CLI tool and the `clack-gui` Desktop Application.

1. Download the `clack_v2_amd64.deb` file from the Releases page.
2. Install the package via terminal:
   ```bash
   sudo dpkg -i clack_v2_amd64.deb
   sudo apt-get install -f # To resolve any missing dependencies automatically
   ```
3. Open "Clack" from your desktop application launcher, or run `clack-gui` in the terminal!

### Option 2: Pre-compiled Tarball (.tar.gz)
If you are using Arch, Fedora, Alpine, or prefer portable executables, use the `.tar.gz` archive.

1. Download `clack-2.0.0-x86_64-linux-gnu.tar.gz`.
2. Extract the archive and ensure you have `ydotool` and `python3-gi` installed on your system.
3. Run the CLI directly or execute the `gui` python module.

### Option 3: Compile from Source

If you have Rust and Cargo installed, you can compile Clack natively:

```bash
git clone https://github.com/ThisWasAryan/clack.git
cd clack
cargo build --release
```

To run the GUI from source:
```bash
sudo apt install ydotool python3-gi python3-gi-cairo gir1.2-gtk-4.0
python3 -m gui
```

---

## 💻 CLI Usage

If you prefer the command line, Clack still supports its powerful CLI backend. It accepts input from standard input (stdin) and outputs the simulated keystroke timing stream to standard output (stdout).

**Pipe a string into clack:**
```bash
echo "Hello, world! I am a simulated human." | clack
```

**Simulate a very fast, erratic typist who makes lots of mistakes:**
```bash
echo "I'm typing really fast but making so many typos!" | clack --wpm 140 --jitter 0.3 --error-rate 0.1
```

**Simulate a slow, careful programmer typing Dvorak:**
```bash
cat main.rs | clack --wpm 45 --layout dvorak --code-mode --error-rate 0.01
```

---

## 🏗️ How it Works

Clack is split into two components to enforce a strict boundary between the simulation logic and the interfaces.

- **`clack-core`**: The highly optimized Rust engine library. It maintains a deterministic internal event queue, processes characters via probabilistic distributions (`rand`), manages layout coordinate mapping, and handles the correction state machine. It guarantees reproducibility given the same seed.
- **`clack-cli`**: The user-facing Rust binary. It parses command-line arguments, initializes the `ClackEngine`, and coordinates real-time delays.
- **`gui`**: The GTK4 application (Python). It provides a graphical wrapper over the `clack-core` execution, orchestrating window-focus tracking and uinput daemon integration (`ydotool`) securely to simulate system-wide keystrokes across applications, regardless of Wayland or X11 limitations.

---

<div align="center">
  <b>Made with ♥ by <a href="https://github.com/ThisWasAryan" style="text-decoration:none;">ThisWasAryan</a> | <a href="https://github.com/ThisWasAryan/clack" style="text-decoration:none;">Repository</a></b>
</div>
