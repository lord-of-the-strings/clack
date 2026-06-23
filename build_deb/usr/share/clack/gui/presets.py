"""
Preset definitions and default configuration values.

Defines the parameters for typing styles like 'Hunt & Peck', 'Casual',
'Proficient', and 'Fast'.
"""

from dataclasses import dataclass

@dataclass
class Preset:
    wpm: float
    error_rate: float
    correction_rate: float
    jitter: float
    thinking_pause_prob: float

PRESETS = {
    "Hunt & Peck": Preset(wpm=20, error_rate=0.08, correction_rate=0.75, jitter=0.25, thinking_pause_prob=0.04),
    "Casual":      Preset(wpm=45, error_rate=0.05, correction_rate=0.82, jitter=0.18, thinking_pause_prob=0.02),
    "Proficient":  Preset(wpm=75, error_rate=0.04, correction_rate=0.85, jitter=0.15, thinking_pause_prob=0.015),
    "Fast":        Preset(wpm=100, error_rate=0.02, correction_rate=0.92, jitter=0.10, thinking_pause_prob=0.008),
}
