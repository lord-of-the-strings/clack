# Clack

Clack is an extremely realistic typing simulator that translates static text or standard input into a dynamic, human-like keystroke stream. 

*Clack is heavily inspired by and credits its core idea to **htype** (https://github.com/lord-of-the-strings/htype), originally created by **Aadity Setu**.* 

If you are generating screencasts, terminal recordings, or automated UI demonstrations, regular typing automation tools like `xdotool` or basic sleep scripts look robotic and fake. Clack utilizes probabilistic models to simulate how a real human types, complete with motor-control panics, realistic typing speeds, error rates, and layout-aware key travel distances.

---

## 🌟 How it Works

Clack doesn't just add a random delay between keypresses. It simulates an entire virtual typist sitting at a keyboard. It employs several advanced mechanics to achieve this:

- **Bimodal Timing Distrubutions**: Human typing has two distinct rhythms. We type adjacent letters in a word quickly, but pause longer at word boundaries, punctuation, and capital letters. Clack models this using Gaussian distributions.
- **Euclidean Key Distances**: Clack understands the physical layout of your keyboard (QWERTY, Dvorak, Colemak, AZERTY). Moving your finger from 'a' to 'z' is faster than moving from 'a' to 'p'. Clack dynamically calculates the physical travel distance between consecutive keys to adjust the inter-key timing.
- **Probabilistic Errors & Corrections**: Humans make mistakes! Clack can simulate typos (hitting an adjacent key), transpositions (swapping two letters), and omissions. It then realistically realizes the mistake, pauses, backspaces, and re-types the correct characters.
- **Panic Events**: Sometimes, a typist's brain glitches. Clack simulates rare "Panic Events" where the virtual typist accidentally holds down a key for too long (a stuck-key burst) or gets confused and re-types the prefix of the current word before backspacing to fix it.
- **Code-Aware Typing Mode**: Typing source code requires more cognitive load than typing prose. When enabled, Clack tracks the depth of nested brackets `{} [] ()` and slows down the typing speed for deeper scopes. It also detects complex identifiers (`snake_case`, `camelCase`) and types them more carefully to reflect real programming behavior.

---

## 🚀 Installation

Clack is built in Rust for maximum performance and cross-platform compatibility. You can install Clack by downloading a pre-compiled binary for your operating system, or by compiling it from source.

### Option 1: Debian/Ubuntu Linux (.deb)
If you are using a Debian-based Linux distribution (Ubuntu, Mint, Pop!_OS, etc.), the easiest way to install Clack is using the `.deb` package. This automatically installs the `clack` command to your system path.

1. Download the `clack_1.0.0_amd64.deb` file from the Releases page.
2. Open your terminal in the download folder and run:
   ```bash
   sudo dpkg -i clack_1.0.0_amd64.deb
   ```
3. You can now use `clack` anywhere!

### Option 2: All Other Linux Distributions (.tar.gz)
If you are using Arch, Fedora, Alpine, or simply prefer standalone portable executables, use the `.tar.gz` archive.

1. Download the `clack-1.0.0-x86_64-linux-gnu.tar.gz` file from the Releases page.
2. Extract the archive:
   ```bash
   tar -xzf clack-1.0.0-x86_64-linux-gnu.tar.gz
   ```
3. Make it executable and move it to your system bin folder:
   ```bash
   chmod +x clack
   sudo mv clack /usr/local/bin/
   ```

### Option 3: Compile from Source (Any OS / macOS / Windows)
If you have Rust and Cargo installed, you can compile Clack natively on any operating system.

```bash
git clone https://github.com/ThisWasAryan/clack.git
cd clack
cargo install --path clack-cli
```

---

## 💻 Usage

Clack accepts input from standard input (stdin) and outputs the simulated keystroke timing stream to standard output (stdout) or directly to another program.

### Basic Usage

Pipe a file or string into `clack`:

```bash
echo "Hello, world! I am a simulated human." | clack
```

```bash
cat my_script.sh | clack
```

### Configuration Flags

You can completely customize the simulated typist's behavior using CLI arguments.

**Typing Mechanics**
- `--wpm <FLOAT>`: Set the target Words Per Minute. The engine natively scales key travel timing off of this (default: `60.0`).
- `--layout <STRING>`: The physical keyboard layout to simulate. This fundamentally alters finger-travel distance calculations. Options: `qwerty`, `dvorak`, `colemak`, `azerty` (default: `qwerty`).
- `--jitter <FLOAT>`: Variance in the typing speed. Higher values lead to more erratic, unpredictable typing bursts (default: `0.15`).

**Errors and Mistakes**
- `--error-rate <FLOAT>`: Probability of making a mistake per character. Supports Typos, Transpositions, and Omissions (default: `0.04`, i.e., 4%).
- `--correction-rate <FLOAT>`: Probability of realizing and correcting a mistake. Set to `1.0` to guarantee the output perfectly matches the input text (default: `0.85`).
- `--no-errors`: Completely disable all mistake generation, forcing 100% typing accuracy.

**Behavioral State Machine**
- `--session-length <INT>`: The expected character length of the typing session. Used to calculate when the typist experiences "Fatigue" burnout (default: `500`).
- `--no-fatigue`: Disable the Fatigue mechanic, preventing the typist from slowing down or making more errors over long files.
- `--max-pause <INT>`: The absolute maximum time (in milliseconds) the typist is allowed to pause between actions (default: `5000`).
- `--thinking-pause-prob <FLOAT>`: The probability that encountering a long, difficult word triggers a "Thinking" hesitation state (default: `0.015`).
- `--code-mode`: Enable scope-depth tracking and identifier slowdowns. Specifically designed to make writing Rust/C/Python source code look realistic by slowing down on nested brackets and `CamelCase` identifiers.
- `--state-output`: Debug flag. Prints the internal cognitive state transitions (e.g., `Flow`, `Distracted`, `Fatigued`) to `stderr` as they occur.

**System**
- `--seed <INT>`: Provide a specific RNG seed to make the entire typing simulation 100% deterministic and reproducible.

**Simulate a very fast, erratic typist who makes lots of mistakes:**
```bash
echo "I'm typing really fast but making so many typos!" | clack --wpm 140 --jitter 0.3 --error-rate 0.1
```

**Simulate a slow, careful programmer typing Dvorak:**
```bash
cat main.rs | clack --wpm 45 --layout dvorak --code-mode --error-rate 0.01
```

---

## 🏗️ Technical Architecture

Clack is split into two components to enforce a strict boundary between the simulation logic and the command-line interface.

- **`clack-core`**: The engine library. It maintains a deterministic internal event queue, processes characters via probabilistic distributions (`rand`), manages layout coordinate mapping, and handles the correction state machine. It guarantees reproducibility given the same seed.
- **`clack-cli`**: The user-facing binary. It parses command-line arguments (using `clap`), initializes the `ClackEngine`, and streams the generated `ClackEvent` timings to stdout or coordinates real-time delays.

Clack ensures *O(1)* per-character processing overhead, meaning it can generate timing events infinitely without memory scaling issues.
