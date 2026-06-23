"""
Thread-safe shared state object.

Provides the `ClackState` class which holds all typing status,
configuration parameters, and position tracking data shared across threads.
"""

import threading
from typing import Optional

class ClackState:
    """
    Thread-safe container for application state.
    Access to fields should be mediated by internal locks.
    """
    def __init__(self):
        self._lock = threading.RLock()
        
        # Operational State
        self._original_text: str = ""
        self._pause_position: int = 0
        self._is_typing: bool = False
        self._is_paused: bool = False
        self._current_behavioral_state: str = "IDLE"
        self._target_window_id: str = ""
        
        # Configuration (defaults for Proficient preset)
        self._wpm: float = 75.0
        self._error_rate: float = 0.04
        self._correction_rate: float = 0.85
        self._correct_all_mistakes: bool = True
        self._jitter: float = 0.15
        self._session_length: int = 500
        self._thinking_pause_prob: float = 0.015
        self._max_pause: int = 5000
        self._no_fatigue: bool = False
        self._seed: Optional[int] = None

    # Properties for operational state
    @property
    def original_text(self) -> str:
        with self._lock: return self._original_text
    
    @original_text.setter
    def original_text(self, val: str):
        with self._lock: self._original_text = val

    @property
    def pause_position(self) -> int:
        with self._lock: return self._pause_position
        
    @pause_position.setter
    def pause_position(self, val: int):
        with self._lock: self._pause_position = val

    @property
    def total_chars(self) -> int:
        with self._lock: return len(self._original_text)
        
    def increment_position(self):
        with self._lock: self._pause_position += 1

    def decrement_position(self):
        with self._lock:
            if self._pause_position > 0:
                self._pause_position -= 1

    @property
    def is_typing(self) -> bool:
        with self._lock: return self._is_typing
        
    @is_typing.setter
    def is_typing(self, val: bool):
        with self._lock: self._is_typing = val

    @property
    def is_paused(self) -> bool:
        with self._lock: return self._is_paused
        
    @is_paused.setter
    def is_paused(self, val: bool):
        with self._lock: self._is_paused = val

    @property
    def current_behavioral_state(self) -> str:
        with self._lock: return self._current_behavioral_state
        
    @current_behavioral_state.setter
    def current_behavioral_state(self, val: str):
        with self._lock: self._current_behavioral_state = val

    @property
    def target_window_id(self) -> str:
        with self._lock: return self._target_window_id
        
    @target_window_id.setter
    def target_window_id(self, val: str):
        with self._lock: self._target_window_id = val

    # Properties for configuration
    @property
    def wpm(self) -> float:
        with self._lock: return self._wpm
        
    @wpm.setter
    def wpm(self, val: float):
        with self._lock: self._wpm = val

    @property
    def error_rate(self) -> float:
        with self._lock: return self._error_rate
        
    @error_rate.setter
    def error_rate(self, val: float):
        with self._lock: self._error_rate = val

    @property
    def correction_rate(self) -> float:
        with self._lock: return self._correction_rate
        
    @correction_rate.setter
    def correction_rate(self, val: float):
        with self._lock: self._correction_rate = val

    @property
    def correct_all_mistakes(self) -> bool:
        with self._lock: return self._correct_all_mistakes
        
    @correct_all_mistakes.setter
    def correct_all_mistakes(self, val: bool):
        with self._lock: self._correct_all_mistakes = val

    @property
    def jitter(self) -> float:
        with self._lock: return self._jitter
        
    @jitter.setter
    def jitter(self, val: float):
        with self._lock: self._jitter = val

    @property
    def session_length(self) -> int:
        with self._lock: return self._session_length
        
    @session_length.setter
    def session_length(self, val: int):
        with self._lock: self._session_length = val

    @property
    def thinking_pause_prob(self) -> float:
        with self._lock: return self._thinking_pause_prob
        
    @thinking_pause_prob.setter
    def thinking_pause_prob(self, val: float):
        with self._lock: self._thinking_pause_prob = val

    @property
    def max_pause(self) -> int:
        with self._lock: return self._max_pause
        
    @max_pause.setter
    def max_pause(self, val: int):
        with self._lock: self._max_pause = val

    @property
    def no_fatigue(self) -> bool:
        with self._lock: return self._no_fatigue
        
    @no_fatigue.setter
    def no_fatigue(self, val: bool):
        with self._lock: self._no_fatigue = val

    @property
    def seed(self) -> Optional[int]:
        with self._lock: return self._seed
        
    @seed.setter
    def seed(self, val: Optional[int]):
        with self._lock: self._seed = val
