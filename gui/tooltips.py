"""
Centralized UI tooltip strings.

Contains the `TOOLTIPS` dictionary with user-facing explanations
for GUI controls.
"""

TOOLTIPS = {
    "wpm": "Words per minute. Higher = faster typing. Average human typist is 40-60 WPM.",
    "error_rate": "How often typos occur. 4% is realistic for a proficient typist. 0% disables errors entirely.",
    "correction_rate": "How often typos get corrected. 85% is realistic. Uncorrected typos remain in the final text.",
    "correct_all_mistakes": "When on, all errors are corrected before the text is complete. The typing process still looks human with mistakes happening and being fixed, but the final output will be clean.",
    "jitter": "Randomness in typing rhythm. Higher values create more variable timing between keystrokes. 0.15 is realistic.",
    "session_length": "Expected total character count. Used to compute warmup and fatigue curves. Set to approximate length of your text.",
    "thinking_pause_prob": "Probability of a thinking pause between words. 1.5% is realistic. Higher values add more pauses.",
    "max_pause": "Maximum duration of any single pause in milliseconds. Prevents unrealistically long pauses.",
    "no_fatigue": "When on, disables warmup slowdown at the start and fatigue effects at the end of long typing sessions.",
    "seed": "Random number generator seed. Set a specific number for reproducible behavior. Leave blank for random.",
    "global_shortcut": "Global keyboard shortcut to start, pause, or resume typing from any application.",
    "speed_boost": "Hold this key combination while typing to temporarily increase speed by 1.5×.",
}
