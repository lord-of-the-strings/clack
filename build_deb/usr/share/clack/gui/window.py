import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio
from .presets import PRESETS
from .tooltips import TOOLTIPS
from .settings import SettingsPanel
from .persistence import schedule_save

class ClackWindow(Gtk.ApplicationWindow):
    """
    The main application window, managing transitions between states
    and connecting UI signals to application logic.
    """
    def __init__(self, application, state, runner, **kwargs):
        super().__init__(application=application, **kwargs)
        self.state = state
        self.runner = runner
        
        self.set_title("Clack")
        self.set_default_size(320, -1)
        self.set_resizable(False)
        self.set_decorated(True)
        
        try:
            self.set_keep_above(True)
        except AttributeError:
            # GTK4 removed set_keep_above, but if available in a compat layer, use it.
            pass
            
        # Drag gesture for moving window
        drag = Gtk.GestureDrag()
        drag.connect("drag-update", self._on_drag_update)
        self.add_controller(drag)
        
        # Main Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)
        self.set_child(self.main_box)
        
        self._build_expanded_layout()
        self._build_collapsed_layout()
        
        # Initial state
        self.expanded_box.set_visible(True)
        self.collapsed_box.set_visible(False)
        
        # Wire runner callbacks
        # In a real app we'd pass callbacks to the runner, but here we can poll or let the runner call GLib.idle_add directly.
        # Let's let the runner call our methods via idle_add.
        self.runner._ui_update_progress = self.update_progress
        self.runner._ui_update_state = self.update_state_label
        self.runner._ui_complete = self.on_typing_complete
        self.runner._ui_auto_paused = self._on_auto_paused
        self.runner._ui_error = self._on_error
        self.runner._ui_correction = self._on_correction
        
        self._correction_flash = False
        self._blink_state = True
        self._blink_tag = 0
        
        # Shortcuts
        from .shortcuts import ShortcutManager
        self.shortcut_manager = ShortcutManager(
            start_callback=self._on_start_pause_shortcut,
            speed_callback_on=None,
            speed_callback_off=None
        )
        self.shortcut_manager.register(
            getattr(self.state, "global_shortcut", "Ctrl+Shift+F12"),
            getattr(self.state, "speed_boost_shortcut", "Ctrl+Shift")
        )

    def _on_drag_update(self, gesture, offset_x, offset_y):
        # Very basic dragging (requires X11 or specific Wayland setups)
        pass # Not easily done cleanly in GTK4 Wayland without protocols.

    def _build_expanded_layout(self):
        self.expanded_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.append(self.expanded_box)
        
        # Text input
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 120)
        self.text_overlay = Gtk.Overlay()
        
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.get_buffer().connect("changed", self._on_text_changed)
        
        self.watermark_label = Gtk.Label(label="<span alpha='50%'>Paste your text here...</span>")
        self.watermark_label.set_use_markup(True)
        self.watermark_label.set_halign(Gtk.Align.START)
        self.watermark_label.set_valign(Gtk.Align.START)
        self.watermark_label.set_margin_top(8)
        self.watermark_label.set_margin_start(8)
        
        self.text_overlay.set_child(self.text_view)
        self.text_overlay.add_overlay(self.watermark_label)
        
        scrolled.set_child(self.text_overlay)
        self.expanded_box.append(scrolled)
        
        # Preset Dropdown
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_label = Gtk.Label(label="Style:")
        preset_box.append(preset_label)
        
        preset_names = ["Proficient", "Hunt & Peck", "Casual", "Fast", "Custom"]
        self.preset_dropdown = Gtk.DropDown.new_from_strings(preset_names)
        self._updating_preset = False
        
        matched_index = 4
        for i, name in enumerate(preset_names):
            if name in PRESETS:
                p = PRESETS[name]
                if (abs(self.state.wpm - p.wpm) < 0.1 and
                    abs(self.state.error_rate - p.error_rate) < 0.001 and
                    abs(self.state.correction_rate - p.correction_rate) < 0.001 and
                    abs(self.state.jitter - p.jitter) < 0.001 and
                    abs(self.state.thinking_pause_prob - p.thinking_pause_prob) < 0.001):
                    matched_index = i
                    break
                    
        self.preset_dropdown.set_selected(matched_index)
        self.preset_dropdown.connect("notify::selected-item", self._on_preset_changed)
        preset_box.append(self.preset_dropdown)
        self.expanded_box.append(preset_box)
        
        # Sliders
        self.wpm_scale, self.wpm_label = self._create_slider("WPM", 10, 150, 1, self.state.wpm, TOOLTIPS["wpm"])
        self.error_scale, self.error_label = self._create_slider("Errors", 0, 15, 0.1, self.state.error_rate * 100, TOOLTIPS["error_rate"], is_percent=True)
        self.correct_scale, self.correct_label = self._create_slider("Correction", 0, 100, 1, self.state.correction_rate * 100, TOOLTIPS["correction_rate"], is_percent=True)
        
        self.wpm_scale.connect("value-changed", lambda s: self._on_slider_changed("wpm", s))
        self.error_scale.connect("value-changed", lambda s: self._on_slider_changed("error_rate", s, 0.01))
        self.correct_scale.connect("value-changed", lambda s: self._on_slider_changed("correction_rate", s, 0.01))
        
        # No Leftover Mistakes Toggle
        toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.mistakes_toggle = Gtk.Switch()
        self.mistakes_toggle.set_active(self.state.correct_all_mistakes)
        self.correct_scale.set_sensitive(not self.state.correct_all_mistakes)
        self.mistakes_toggle.connect("state-set", self._on_mistakes_toggle)
        toggle_box.append(self.mistakes_toggle)
        toggle_label = Gtk.Label(label="No leftover mistakes")
        toggle_label.set_tooltip_text(TOOLTIPS["correct_all_mistakes"])
        toggle_box.append(toggle_label)
        self.expanded_box.append(toggle_box)
        
        # Advanced Settings Button
        settings_btn = Gtk.Button(label="Advanced Settings...")
        settings_btn.connect("clicked", self._on_settings_clicked)
        self.expanded_box.append(settings_btn)
        
        # Start Button
        self.start_button = Gtk.Button()
        self.start_button.set_size_request(-1, 44)
        
        self.start_button.set_child(Gtk.Label(label="▶ Start Typing"))
        
        self.start_button.connect("clicked", self._on_start_clicked)
        self.expanded_box.append(self.start_button)

    def _create_slider(self, name, min_val, max_val, step, default, tooltip, is_percent=False):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=name)
        lbl.set_size_request(80, -1)
        lbl.set_xalign(0)
        box.append(lbl)
        
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_range(min_val, max_val)
        scale.set_value(default)
        scale.set_hexpand(True)
        scale.set_draw_value(False)
        box.append(scale)
        
        val_lbl = Gtk.Label(label=f"{int(default)}{'%' if is_percent else ''}")
        val_lbl.set_size_request(40, -1)
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
        
        self.expanded_box.append(box)
        return scale, val_lbl

    def _build_collapsed_layout(self):
        self.collapsed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.main_box.append(self.collapsed_box)
        
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.collapsed_box.append(row1)
        
        # Status light
        self.status_light = Gtk.DrawingArea()
        self.status_light.set_size_request(12, 12)
        self.status_light.set_draw_func(self._draw_status_light)
        row1.append(self.status_light)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("0%")
        row1.append(self.progress_bar)
        
        # Pause button
        self.pause_button = Gtk.Button(label="⏸")
        self.pause_button.connect("clicked", self._on_pause_resume_clicked)
        row1.append(self.pause_button)
        
        # Stop button
        self.stop_button = Gtk.Button(label="⏹")
        self.stop_button.connect("clicked", self._on_stop_clicked)
        row1.append(self.stop_button)
        
        # State label
        self.state_label = Gtk.Label(label="IDLE")
        self.state_label.set_xalign(0)
        # We can't use set_markup for opacity easily without span, so we just do span.
        self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>IDLE</span>")
        self.collapsed_box.append(self.state_label)

    def _on_stop_clicked(self, btn):
        if self.state.is_typing or self.state.is_paused:
            self.runner.pause()
        self.on_typing_complete()

    def _draw_status_light(self, area, cr, width, height):
        if getattr(self, "_correction_flash", False):
            cr.set_source_rgb(0.9, 0.2, 0.2) # Red flash
        elif self.state.is_paused:
            cr.set_source_rgb(0.8, 0.6, 0.1)
        else:
            state = getattr(self.state, "current_behavioral_state", "IDLE")
            if state == "FLOW":
                cr.set_source_rgb(0.2, 0.8, 0.2)
            elif state == "THINKING":
                cr.set_source_rgb(0.2, 0.4, 0.9)
            elif state == "DISTRACTED":
                cr.set_source_rgb(0.8, 0.4, 0.1)
            elif state == "FATIGUED":
                cr.set_source_rgb(0.6, 0.1, 0.6)
            else:
                cr.set_source_rgb(0.5, 0.8, 0.5)
                
        cr.arc(width/2, height/2, min(width, height)/2 - 2, 0, 2*3.14159)
        cr.fill()

    def _toggle_blink(self):
        self._blink_state = not self._blink_state
        self.status_light.queue_draw()
        return True

    def _on_correction(self):
        self._correction_flash = True
        self.status_light.queue_draw()
        GLib.timeout_add(150, self._clear_correction_flash)
        
    def _clear_correction_flash(self):
        self._correction_flash = False
        self.status_light.queue_draw()
        return False

    def _on_text_changed(self, buffer):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        self.watermark_label.set_visible(len(text) == 0)

    def _on_preset_changed(self, dropdown, param):
        item = dropdown.get_selected_item()
        if not item: return
        name = item.get_string()
        if name in PRESETS:
            p = PRESETS[name]
            self._updating_preset = True
            self.wpm_scale.set_value(p.wpm)
            self.error_scale.set_value(p.error_rate * 100)
            self.correct_scale.set_value(p.correction_rate * 100)
            self._updating_preset = False
            
            self.state.wpm = p.wpm
            self.state.error_rate = p.error_rate
            self.state.correction_rate = p.correction_rate
            schedule_save(self.state)

    def _on_slider_changed(self, key, scale, multiplier=1.0):
        val = scale.get_value()
        if key == "wpm":
            self.wpm_label.set_text(f"{int(val)}")
            self.state.wpm = val
        elif key == "error_rate":
            self.error_label.set_text(f"{val:.1f}%")
            self.state.error_rate = val * multiplier
        elif key == "correction_rate":
            self.correct_label.set_text(f"{int(val)}%")
            self.state.correction_rate = val * multiplier
            
        if getattr(self, "_updating_preset", False):
            return
            
        # Switch preset to custom
        model = self.preset_dropdown.get_model()
        for i in range(model.get_n_items()):
            if model.get_item(i).get_string() == "Custom":
                self.preset_dropdown.set_selected(i)
                break
        schedule_save(self.state)

    def _on_mistakes_toggle(self, switch, state):
        self.state.correct_all_mistakes = state
        self.correct_scale.set_sensitive(not state)
        schedule_save(self.state)

    def _on_settings_clicked(self, btn):
        panel = SettingsPanel(self.state)
        panel.set_transient_for(self)
        panel.present()

    def _on_start_clicked(self, btn):
        buf = self.text_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        if not text.strip():
            self._on_error("Text buffer is empty. Please enter some text to simulate typing.")
            return
            
        self.state.original_text = text
        self.state.session_length = len(text)
        self.state.pause_position = 0
        
        self.expanded_box.set_visible(False)
        self.collapsed_box.set_visible(True)
        
        self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>CLICK TARGET WINDOW TO BEGIN...</span>")
        self.pause_button.set_sensitive(False)
        
        if self._blink_tag:
            GLib.source_remove(self._blink_tag)
            self._blink_tag = 0
            
        self.runner.focus_watcher.wait_for_switch(lambda: self._on_focus_acquired(text))

    def _on_focus_acquired(self, text):
        self.pause_button.set_sensitive(True)
        self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>STARTING...</span>")
        if not self._blink_tag:
            self._blink_tag = GLib.timeout_add(250, self._toggle_blink)
        self.runner.start(text, self.state)
        self.status_light.queue_draw()

    def _on_pause_resume_clicked(self, btn):
        if self.state.is_typing:
            self.runner.pause()
            self._on_auto_paused()
        elif self.state.is_paused:
            self.pause_button.set_sensitive(False)
            self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>CLICK TARGET WINDOW TO RESUME...</span>")
            self.runner.focus_watcher.wait_for_switch(self._on_focus_acquired_resume)
        self.status_light.queue_draw()

    def _on_focus_acquired_resume(self):
        self.pause_button.set_sensitive(True)
        self.pause_button.set_label("⏸")
        self.runner.resume()
        self.status_light.queue_draw()

    def _on_auto_paused(self):
        self.pause_button.set_sensitive(True)
        self.pause_button.set_label("▶")
        self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>PAUSED</span>")
        self.status_light.queue_draw()

    def _on_start_pause_shortcut(self):
        if self.state.is_typing:
            self.runner.pause()
            self._on_auto_paused()
        elif self.state.is_paused:
            self.pause_button.set_label("⏸")
            self.state_label.set_markup("<span font_family='monospace' size='small' alpha='60%'>STARTING...</span>")
            self.runner.resume()
            self.status_light.queue_draw()
        elif not self.state.is_typing and not self.state.is_paused:
            self._on_start_clicked(None)

    def update_progress(self, progress: float):
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{int(progress * 100)}%")
        self.status_light.queue_draw()

    def update_state_label(self, state_str: str):
        self.state_label.set_markup(f"<span font_family='monospace' size='small' alpha='60%'>{state_str}</span>")
        self.status_light.queue_draw()

    def on_typing_complete(self):
        self.expanded_box.set_visible(True)
        self.collapsed_box.set_visible(False)
        self.pause_button.set_label("⏸")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        if self._blink_tag:
            GLib.source_remove(self._blink_tag)
            self._blink_tag = 0
        self.status_light.queue_draw()

    def _on_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Clack Error",
            secondary_text=message
        )
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
