import json
import os
from pathlib import Path

def get_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        config_dir = Path(config_home) / "clack"
    else:
        config_dir = Path.home() / ".config" / "clack"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "gui.json"

def load_settings(state):
    """Load user settings from JSON into ClackState."""
    path = get_config_path()
    if not path.exists():
        return
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Map values directly to state
        for key in ["wpm", "error_rate", "correction_rate", "correct_all_mistakes",
                   "jitter", "session_length", "thinking_pause_prob", "max_pause",
                   "no_fatigue", "seed"]:
            if key in data:
                setattr(state, key, data[key])
                
        # Also store shortcuts in state if not there
        if "global_shortcut" in data:
            state.global_shortcut = data["global_shortcut"]
        else:
            state.global_shortcut = "Ctrl+Shift+F12"
            
        if "speed_boost_shortcut" in data:
            state.speed_boost_shortcut = data["speed_boost_shortcut"]
        else:
            state.speed_boost_shortcut = "Ctrl+Shift"
            
    except Exception as e:
        print(f"Failed to load clack settings: {e}")

def save_settings(state):
    """Save user settings from ClackState to JSON."""
    path = get_config_path()
    
    data = {
        "wpm": state.wpm,
        "error_rate": state.error_rate,
        "correction_rate": state.correction_rate,
        "correct_all_mistakes": state.correct_all_mistakes,
        "jitter": state.jitter,
        "session_length": state.session_length,
        "thinking_pause_prob": state.thinking_pause_prob,
        "max_pause": state.max_pause,
        "no_fatigue": state.no_fatigue,
        "seed": state.seed,
        "global_shortcut": getattr(state, "global_shortcut", "Ctrl+Shift+F12"),
        "speed_boost_shortcut": getattr(state, "speed_boost_shortcut", "Ctrl+Shift")
    }
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save clack settings: {e}")

_save_timeout_id = 0

def schedule_save(state):
    """Debounces save operations by 500ms using GLib.timeout_add."""
    import gi
    gi.require_version('GLib', '2.0')
    from gi.repository import GLib
    
    global _save_timeout_id
    if _save_timeout_id != 0:
        GLib.source_remove(_save_timeout_id)
        
    def _do_save():
        global _save_timeout_id
        save_settings(state)
        _save_timeout_id = 0
        return False  # Don't repeat
        
    _save_timeout_id = GLib.timeout_add(500, _do_save)
