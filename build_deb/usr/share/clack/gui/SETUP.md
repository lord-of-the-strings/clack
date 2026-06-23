# Clack GUI Setup Guide

This guide covers installing and configuring the Clack graphical interface on Linux. Clack relies on specific system tools to inject keystrokes securely and detect active windows.

## Prerequisites

- **Python 3.10+**
- **GTK4**
- **PyGObject**
- **ydotool** (mandatory for keystroke injection)
- **xdotool** (optional, enables auto-pause on focus loss for X11)

---

## 1. Install System Dependencies

Select the command for your Linux distribution family.

### Debian / Ubuntu / Linux Mint
```bash
sudo apt install ydotool xdotool python3-gi python3-gi-cairo gir1.2-gtk-4.0
```

### Fedora
```bash
sudo dnf install ydotool xdotool python3-gobject gtk4
```

### Arch Linux / Manjaro
```bash
sudo pacman -S ydotool xdotool python-gobject gtk4
```

### openSUSE
```bash
sudo zypper install ydotool xdotool python3-gobject typelib-1_0-Gtk-4_0
```

---

## 2. Configure ydotool (Important)

`ydotool` requires a background daemon (`ydotoold`) and special permissions to access `/dev/uinput` to simulate keystrokes.

**Option A: Temporary / Manual Setup**
Simply run the daemon as root before using Clack:
```bash
sudo ydotoold &
```

**Option B: Persistent / Rootless Setup (Recommended)**
1. Add your user to the `input` group:
   ```bash
   sudo usermod -aG input $USER
   ```
2. Create a udev rule to allow the `input` group to write to `/dev/uinput`:
   ```bash
   echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-uinput.rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```
3. Enable the `ydotoold` service (if your distro packages it), or add `ydotoold &` to your desktop environment's startup applications.
4. **Log out and log back in** for the group changes to take effect.

---

## 3. Running Clack

From the root directory of the Clack project:
```bash
python -m gui
```

---

## 4. Troubleshooting

**"Missing ydotoold" dialog appears, even though I ran it.**
If you started `ydotoold` with `sudo`, try restarting Clack. The GUI checks for `pgrep ydotoold`. Ensure the process is actually running in the background.

**"Permission denied" or "uinput" error when typing starts.**
This means `ydotool` cannot access `/dev/uinput`. Follow Option B in step 2 above to configure the udev rules and add yourself to the `input` group. Don't forget to log out and back in!

**Clack never auto-pauses when I switch windows.**
Auto-pause relies on `xdotool`. Ensure it is installed. Note that on pure Wayland environments (like modern Sway or Hyprland without Xwayland bridges), `xdotool` cannot detect the active window. You will need to manually use the Pause button or the global shortcut to pause typing.

**Global Shortcuts aren't working.**
On Wayland, global shortcuts require the XDG Desktop Portal to be fully configured by your desktop environment. If you are on an unsupported compositor, rely on the on-screen Start/Pause button instead.
