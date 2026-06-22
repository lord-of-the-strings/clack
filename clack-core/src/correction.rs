use crate::constants::{
    DELAYED_CORRECTION_MAX_CHARS, DELAYED_CORRECTION_MIN_CHARS, IMMEDIATE_CORRECTION_SHARE,
};
use crate::rng::ClackRng;
use crate::BehavioralState;

pub enum CorrectionMode {
    Immediate,
    Delayed { chars_to_continue: usize },
}

pub fn select_correction_mode(rng: &mut ClackRng, correction_rate: f64) -> Option<CorrectionMode> {
    if !rng.sample_bool(correction_rate) {
        return None;
    }

    if rng.sample_bool(IMMEDIATE_CORRECTION_SHARE) {
        Some(CorrectionMode::Immediate)
    } else {
        let chars_to_continue =
            rng.sample_uniform_int(DELAYED_CORRECTION_MIN_CHARS, DELAYED_CORRECTION_MAX_CHARS);
        Some(CorrectionMode::Delayed { chars_to_continue })
    }
}

pub fn get_notice_pause(rng: &mut ClackRng, state: BehavioralState, wpm: f64) -> u64 {
    let (min_ms, max_ms) = match state {
        BehavioralState::Flow => (150.0, 250.0),
        BehavioralState::Focused => (180.0, 300.0),
        BehavioralState::Thinking => (300.0, 700.0),
        BehavioralState::Fatigued => (400.0, 1000.0),
        BehavioralState::Distracted => (500.0, 1000.0),
    };
    
    let skill_mod = if wpm < 60.0 {
        1.15
    } else if wpm < 120.0 {
        1.0 + (120.0 - wpm) / 60.0 * 0.15
    } else if wpm < 180.0 {
        1.0 - (wpm - 120.0) / 60.0 * 0.10
    } else {
        0.90
    };

    let base = rng.sample_uniform(min_ms, max_ms);
    (base * skill_mod) as u64
}

pub fn emit_immediate(rng: &mut ClackRng, num_backspaces: usize, correct_chars: &[u8], retype_delay: u64, state: BehavioralState, wpm: f64) -> Vec<crate::ClackEvent> {
    use crate::constants::{BACKSPACE_IKI_MULT_MAX, BACKSPACE_IKI_MULT_MIN};
    let mut events = Vec::new();

    let notice_pause = get_notice_pause(rng, state, wpm);

    for i in 0..num_backspaces {
        let mult = rng.sample_uniform(BACKSPACE_IKI_MULT_MIN, BACKSPACE_IKI_MULT_MAX);
        let bs_delay = (retype_delay as f64 * mult) as u64;
        let delay_ms = if i == 0 { notice_pause + bs_delay } else { bs_delay };
        events.push(crate::ClackEvent {
            delay_ms,
            bytes: vec![0x08],
            state_transition: None,
        });
    }

    for &correct_char in correct_chars {
        events.push(crate::ClackEvent {
            delay_ms: retype_delay,
            bytes: vec![correct_char],
            state_transition: None,
        });
    }

    events
}

pub fn emit_delayed(rng: &mut ClackRng, num_backspaces: usize, base_iki: u64, state: BehavioralState, wpm: f64) -> Vec<crate::ClackEvent> {
    use crate::constants::{
        CHAR_BY_CHAR_BACKSPACE_PROB,
        BACKSPACE_IKI_MULT_MAX, BACKSPACE_IKI_MULT_MIN,
        HELD_BACKSPACE_IKI_MULT_MAX, HELD_BACKSPACE_IKI_MULT_MIN,
    };
    let mut events = Vec::new();

    let notice_pause = get_notice_pause(rng, state, wpm);
    let is_char_by_char = rng.sample_bool(CHAR_BY_CHAR_BACKSPACE_PROB);

    for i in 0..num_backspaces {
        let mult = if is_char_by_char {
            rng.sample_uniform(BACKSPACE_IKI_MULT_MIN, BACKSPACE_IKI_MULT_MAX)
        } else {
            rng.sample_uniform(HELD_BACKSPACE_IKI_MULT_MIN, HELD_BACKSPACE_IKI_MULT_MAX)
        };
        let bs_delay = (base_iki as f64 * mult) as u64;

        let total_delay = if i == 0 { notice_pause + bs_delay } else { bs_delay };

        events.push(crate::ClackEvent {
            delay_ms: total_delay,
            bytes: vec![0x08],
            state_transition: None,
        });
    }

    events
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::ClackRng;

    #[test]
    fn test_backspace_scaling() {
        let mut rng = ClackRng::new(Some(42));
        let base_iki = 100;
        
        let events = emit_immediate(&mut rng, 2, &[b'a', b'b'], base_iki, BehavioralState::Focused, 100.0);
        
        // Total events: 2 backspaces, 2 retypes
        assert_eq!(events.len(), 4);
        
        // Events 0 and 1 are backspaces. Their delay must be scaled off base_iki (100)
        // Backspaces have BACKSPACE_IKI_MULT_MIN (0.6) to BACKSPACE_IKI_MULT_MAX (1.0)
        // Plus event 0 has the notice pause. Let's just check event 1.
        let e1_delay = events[1].delay_ms;
        assert!(e1_delay >= 60 && e1_delay <= 100);
        
        // Retypes should be exactly base_iki
        assert_eq!(events[2].delay_ms, 100);
        assert_eq!(events[3].delay_ms, 100);
    }
}
