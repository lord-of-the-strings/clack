import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from .tooltips import TOOLTIPS
from .persistence import schedule_save

class SettingsPanel(Gtk.Window):
    """
    Advanced settings panel for tuning Clack behavior.
    """
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.set_title("Advanced Settings")
        self.set_default_size(350, -1)
        self.set_modal(True)
        self.set_resizable(False)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        self.set_child(vbox)
        
        # Sliders
        self.jitter_scale, self.jitter_label = self._create_slider("Jitter", 0.0, 1.0, 0.01, self.state.jitter, TOOLTIPS["jitter"], vbox)
        self.thinking_scale, self.thinking_label = self._create_slider("Thinking Prob.", 0.0, 0.1, 0.001, self.state.thinking_pause_prob, TOOLTIPS["thinking_pause_prob"], vbox)
        self.max_pause_scale, self.max_pause_label = self._create_slider("Max Pause (ms)", 1000, 30000, 500, self.state.max_pause, TOOLTIPS["max_pause"], vbox)
        
        self.jitter_scale.connect("value-changed", self._on_jitter_changed)
        self.thinking_scale.connect("value-changed", self._on_thinking_changed)
        self.max_pause_scale.connect("value-changed", self._on_max_pause_changed)
        
        # Switches & Entries
        self.no_fatigue_switch = self._create_switch_row("Disable Fatigue", self.state.no_fatigue, TOOLTIPS["no_fatigue"], vbox)
        self.no_fatigue_switch.connect("state-set", self._on_no_fatigue_changed)
        
        self.seed_entry = self._create_entry_row("RNG Seed (Empty=Random)", str(self.state.seed) if self.state.seed else "", TOOLTIPS["seed"], vbox)
        self.seed_entry.connect("changed", lambda e: self._on_seed_changed(e.get_text()))
        
        # Shortcuts Section
        shortcuts_frame = Gtk.Frame()
        shortcuts_frame.set_label("Global Shortcuts (Work in Progress)")
        shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        shortcuts_box.set_sensitive(False)
        shortcuts_box.set_margin_top(8)
        shortcuts_box.set_margin_bottom(8)
        shortcuts_box.set_margin_start(8)
        shortcuts_box.set_margin_end(8)
        shortcuts_frame.set_child(shortcuts_box)
        vbox.append(shortcuts_frame)
        
        # Start/Pause Shortcut
        sp_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sp_lbl = Gtk.Label(label="Start/Pause:")
        sp_lbl.set_xalign(0)
        sp_box.append(sp_lbl)
        self.sp_entry = Gtk.Entry()
        self.sp_entry.set_hexpand(True)
        self.sp_entry.set_editable(False)
        self.sp_entry.set_text(getattr(self.state, "global_shortcut", "Ctrl+Shift+F12"))
        sp_box.append(self.sp_entry)
        sp_btn = Gtk.Button(label="Change")
        sp_btn.connect("clicked", lambda b: self._start_recording(self.sp_entry, "global_shortcut"))
        sp_box.append(sp_btn)
        shortcuts_box.append(sp_box)
        
        # Speed Boost Shortcut
        sb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sb_lbl = Gtk.Label(label="Speed Boost:")
        sb_lbl.set_xalign(0)
        sb_box.append(sb_lbl)
        self.sb_entry = Gtk.Entry()
        self.sb_entry.set_hexpand(True)
        self.sb_entry.set_editable(False)
        self.sb_entry.set_text(getattr(self.state, "speed_boost_shortcut", "Ctrl+Shift"))
        sb_box.append(self.sb_entry)
        sb_btn = Gtk.Button(label="Change")
        sb_btn.connect("clicked", lambda b: self._start_recording(self.sb_entry, "speed_boost_shortcut"))
        sb_box.append(sb_btn)
        shortcuts_box.append(sb_box)

        # Reset Button
        self.reset_btn = Gtk.Button(label="Reset to Defaults")
        self.reset_btn.set_margin_top(8)
        self.reset_btn.connect("clicked", self._on_reset_clicked)
        vbox.append(self.reset_btn)
        
        # Credits
        credits_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        credits_box.set_halign(Gtk.Align.CENTER)
        credits_box.set_margin_top(8)
        
        credits_box.append(Gtk.Label(label="Made with ♥ by"))
        
        from gi.repository import Gdk, Gio
        aryan_lbl = Gtk.Label()
        aryan_lbl.set_markup("<span foreground='lightblue'>ThisWasAryan</span>")
        aryan_lbl.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        
        gesture1 = Gtk.GestureClick.new()
        def _on_aryan_clicked(g, n, x, y):
            Gio.AppInfo.launch_default_for_uri("https://github.com/ThisWasAryan", None)
        gesture1.connect("pressed", _on_aryan_clicked)
        aryan_lbl.add_controller(gesture1)
        credits_box.append(aryan_lbl)
        
        credits_box.append(Gtk.Label(label="|"))
        
        repo_lbl = Gtk.Label()
        repo_lbl.set_markup("<span foreground='lightblue'>Repository</span>")
        repo_lbl.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        
        gesture2 = Gtk.GestureClick.new()
        def _on_repo_clicked(g, n, x, y):
            Gio.AppInfo.launch_default_for_uri("https://github.com/ThisWasAryan/clack", None)
        gesture2.connect("pressed", _on_repo_clicked)
        repo_lbl.add_controller(gesture2)
        credits_box.append(repo_lbl)
        
        vbox.append(credits_box)

    def _create_slider(self, name, min_val, max_val, step, default, tooltip, parent_box):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=name)
        lbl.set_size_request(100, -1)
        lbl.set_xalign(0)
        box.append(lbl)
        
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_range(min_val, max_val)
        scale.set_value(default)
        scale.set_hexpand(True)
        scale.set_draw_value(False)
        box.append(scale)
        
        # Determine formatting based on step
        is_float = step < 1.0
        val_str = f"{default:.3f}" if step < 0.01 else (f"{default:.2f}" if is_float else f"{int(default)}")
        val_lbl = Gtk.Label(label=val_str)
        val_lbl.set_size_request(50, -1)
        val_lbl.set_xalign(1)
        box.append(val_lbl)
        
        info = Gtk.Button(label="?")
        info.set_tooltip_text(tooltip)
        def _on_info_clicked(btn):
            popover = Gtk.Popover()
            label = Gtk.Label(label=tooltip)
            label.set_wrap(True)
            label.set_max_width_chars(40)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            popover.set_child(label)
            popover.set_parent(btn)
            popover.popup()
        info.connect("clicked", _on_info_clicked)
        box.append(info)
        
        parent_box.append(box)
        return scale, val_lbl
        
    def _create_switch_row(self, name, default, tooltip, parent_box):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=name)
        lbl.set_xalign(0)
        lbl.set_hexpand(True)
        box.append(lbl)
        
        switch = Gtk.Switch()
        switch.set_active(default)
        box.append(switch)
        
        info = Gtk.Button(label="?")
        info.set_tooltip_text(tooltip)
        def _on_info_clicked(btn):
            popover = Gtk.Popover()
            label = Gtk.Label(label=tooltip)
            label.set_wrap(True)
            label.set_max_width_chars(40)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            popover.set_child(label)
            popover.set_parent(btn)
            popover.popup()
        info.connect("clicked", _on_info_clicked)
        box.append(info)
        
        parent_box.append(box)
        return switch
        
    def _create_entry_row(self, name, default, tooltip, parent_box):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=name)
        lbl.set_xalign(0)
        box.append(lbl)
        
        entry = Gtk.Entry()
        entry.set_text(default)
        entry.set_hexpand(True)
        box.append(entry)
        
        info = Gtk.Button(label="?")
        info.set_tooltip_text(tooltip)
        def _on_info_clicked(btn):
            popover = Gtk.Popover()
            label = Gtk.Label(label=tooltip)
            label.set_wrap(True)
            label.set_max_width_chars(40)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            popover.set_child(label)
            popover.set_parent(btn)
            popover.popup()
        info.connect("clicked", _on_info_clicked)
        box.append(info)
        
        parent_box.append(box)
        return entry
        
    def _start_recording(self, entry, state_key):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CANCEL,
            text="Recording Shortcut...",
            secondary_text="Press the desired key combination now."
        )
        ctrl = Gtk.EventControllerKey.new()
        ctrl.connect("key-pressed", self._on_record_key, entry, state_key, dialog)
        dialog.add_controller(ctrl)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    def _on_record_key(self, ctrl, keyval, keycode, state, entry, state_key, dialog):
        from gi.repository import Gdk
        name = Gdk.keyval_name(keyval)
        if name in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Super_L", "Super_R"):
            return True # wait for main key
            
        mods = []
        if state & Gdk.ModifierType.CONTROL_MASK:
            mods.append("Ctrl")
        if state & Gdk.ModifierType.SHIFT_MASK:
            mods.append("Shift")
        if state & Gdk.ModifierType.ALT_MASK:
            mods.append("Alt")
            
        if name:
            if name.endswith("_L") or name.endswith("_R"):
                return True
            res = "+".join(mods + [name])
            entry.set_text(res)
            
            setattr(self.state, state_key, res)
            schedule_save(self.state)
            win = self.get_transient_for()
            if win and hasattr(win, "shortcut_manager"):
                win.shortcut_manager.register(
                    self.state.global_shortcut,
                    self.state.speed_boost_shortcut
                )
            
            dialog.close()
            return True
        return False

    def _on_jitter_changed(self, scale):
        val = scale.get_value()
        self.jitter_label.set_text(f"{val:.2f}")
        self.state.jitter = val
        schedule_save(self.state)

    def _on_thinking_changed(self, scale):
        val = scale.get_value()
        self.thinking_label.set_text(f"{val:.3f}")
        self.state.thinking_pause_prob = val
        schedule_save(self.state)

    def _on_max_pause_changed(self, scale):
        val = scale.get_value()
        self.max_pause_label.set_text(f"{int(val)}")
        self.state.max_pause = val
        schedule_save(self.state)

    def _on_no_fatigue_changed(self, switch, state):
        self.state.no_fatigue = state
        schedule_save(self.state)
        return False

    def _on_seed_changed(self, text):
        if text.strip() == "":
            self.state.seed = None
            schedule_save(self.state)
        else:
            try:
                self.state.seed = int(text)
                schedule_save(self.state)
            except ValueError:
                pass

    def _on_shortcut_changed(self, entry):
        pass # Now handled by the recording dialog

    def _on_reset_clicked(self, btn):
        from .state import ClackState
        default_state = ClackState()
        
        # Copy to self.state
        self.state.jitter = default_state.jitter
        self.state.thinking_pause_prob = default_state.thinking_pause_prob
        self.state.max_pause = default_state.max_pause
        self.state.no_fatigue = default_state.no_fatigue
        self.state.seed = default_state.seed
        
        self.state.wpm = default_state.wpm
        self.state.error_rate = default_state.error_rate
        self.state.correction_rate = default_state.correction_rate
        self.state.correct_all_mistakes = default_state.correct_all_mistakes
        
        # Update Settings UI
        self.jitter_scale.set_value(self.state.jitter)
        self.thinking_scale.set_value(self.state.thinking_pause_prob)
        self.max_pause_scale.set_value(self.state.max_pause)
        self.no_fatigue_switch.set_active(self.state.no_fatigue)
        self.seed_entry.set_text("")
        
        # Update Main Window UI
        win = self.get_transient_for()
        if win:
            # Reconnect temporarily suppressed
            win.wpm_scale.set_value(self.state.wpm)
            win.error_scale.set_value(self.state.error_rate * 100)
            win.correct_scale.set_value(self.state.correction_rate * 100)
            win.mistakes_toggle.set_active(self.state.correct_all_mistakes)
            
            # Select "Proficient" preset since defaults match it
            model = win.preset_dropdown.get_model()
            for i in range(model.get_n_items()):
                if model.get_item(i).get_string() == "Proficient":
                    win.preset_dropdown.set_selected(i)
                    break

        schedule_save(self.state)
