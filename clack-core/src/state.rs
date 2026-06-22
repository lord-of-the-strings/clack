use crate::rng::ClackRng;
use crate::{BehavioralState, StateTransition};

pub struct StateManager {
    pub current_state: BehavioralState,
    pub words_in_state: usize,
    pub total_words: usize,
}

impl Default for StateManager {
    fn default() -> Self {
        Self::new()
    }
}

impl StateManager {
    pub fn new() -> Self {
        Self {
            current_state: BehavioralState::Focused,
            words_in_state: 0,
            total_words: 0,
        }
    }

    pub fn advance_word(&mut self) {
        self.words_in_state += 1;
        self.total_words += 1;
    }

    pub fn try_transition(
        &mut self,
        rng: &mut ClackRng,
        is_sentence_boundary: bool,
        is_difficult_word: bool,
        is_fatigued: bool,
        made_error: bool,
    ) -> Option<StateTransition> {
        let prev_state = self.current_state;

        if is_fatigued && self.current_state != BehavioralState::Fatigued {
            self.current_state = BehavioralState::Fatigued;
        } else if made_error && self.current_state == BehavioralState::Flow {
            self.current_state = BehavioralState::Focused;
        } else if is_difficult_word && self.current_state != BehavioralState::Fatigued {
            if rng.sample_bool(0.30) {
                self.current_state = BehavioralState::Thinking;
            } else {
                self.current_state = BehavioralState::Focused;
            }
        } else if is_sentence_boundary && self.current_state != BehavioralState::Fatigued && self.total_words >= 40 && rng.sample_bool(0.05) {
            self.current_state = BehavioralState::Distracted;
        }

        if self.current_state == BehavioralState::Distracted && self.words_in_state >= 3 {
            self.current_state = BehavioralState::Focused;
        }

        // Entering flow if focused for long enough
        if self.current_state == BehavioralState::Focused && self.words_in_state >= 10 {
            self.current_state = BehavioralState::Flow;
        }

        if self.current_state != prev_state {
            self.words_in_state = 0;
            Some(StateTransition {
                prev_state,
                new_state: self.current_state,
                word_count: self.total_words,
            })
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::ClackRng;

    #[test]
    fn test_flow_trigger() {
        let mut sm = StateManager::new();
        let mut rng = ClackRng::new(Some(42));
        
        for _ in 0..10 {
            sm.advance_word();
            sm.try_transition(&mut rng, false, false, false, false);
        }
        assert_eq!(sm.current_state, BehavioralState::Flow);
    }

    #[test]
    fn test_fatigue_trigger() {
        let mut sm = StateManager::new();
        let mut rng = ClackRng::new(Some(42));
        
        sm.try_transition(&mut rng, false, false, true, false);
        assert_eq!(sm.current_state, BehavioralState::Fatigued);
    }

    #[test]
    fn test_distracted_minimum_words() {
        let mut sm = StateManager::new();
        let mut rng = ClackRng::new(Some(42));
        
        // Even at a sentence boundary with RNG manipulated, if words < 40, shouldn't trigger
        // We'll brute force 100 transitions to be sure
        for _ in 0..100 {
            sm.try_transition(&mut rng, true, false, false, false);
            assert_ne!(sm.current_state, BehavioralState::Distracted);
        }

        // Now set total words > 40
        sm.total_words = 45;
        let mut triggered = false;
        for _ in 0..100 {
            sm.try_transition(&mut rng, true, false, false, false);
            if sm.current_state == BehavioralState::Distracted {
                triggered = true;
                break;
            }
        }
        assert!(triggered);
    }
}
