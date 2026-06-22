
#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::ClackRng;

    #[test]
    fn test_burst_trigger_and_drain() {
        let mut burst = BurstState::new();
        let mut rng = ClackRng::new(Some(42));
        
        burst.trigger_burst(&mut rng);
        assert!(burst.chars_remaining >= crate::constants::BURST_DURATION_MIN_CHARS);
        assert!(burst.is_active());

        let initial_chars = burst.chars_remaining;
        for _ in 0..initial_chars {
            let pause = burst.advance_char(&mut rng);
            if burst.chars_remaining > 0 {
                assert!(pause.is_none());
            } else {
                assert!(pause.is_some());
            }
        }
        
        assert!(!burst.is_active());
        assert_eq!(burst.chars_remaining, 0);
    }
}
