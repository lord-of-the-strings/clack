use crate::constants::*;
use crate::rng::ClackRng;
use std::str::FromStr;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyboardLayout {
    Qwerty,
    Dvorak,
    Colemak,
    Azerty,
}

impl Default for KeyboardLayout {
    fn default() -> Self {
        Self::Qwerty
    }
}

impl FromStr for KeyboardLayout {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "qwerty" => Ok(Self::Qwerty),
            "dvorak" => Ok(Self::Dvorak),
            "colemak" => Ok(Self::Colemak),
            "azerty" => Ok(Self::Azerty),
            _ => Err(format!("Unknown layout: {}", s)),
        }
    }
}

pub fn key_position(c: char, layout: KeyboardLayout) -> Option<(i32, i32)> {
    let c = c.to_ascii_lowercase();
    match layout {
        KeyboardLayout::Qwerty => qwerty_position(c),
        KeyboardLayout::Dvorak => dvorak_position(c),
        KeyboardLayout::Colemak => colemak_position(c),
        KeyboardLayout::Azerty => azerty_position(c),
    }
}

fn qwerty_position(c: char) -> Option<(i32, i32)> {
    match c {
        // Row 0
        '1' => Some((0, 0)), '2' => Some((1, 0)), '3' => Some((2, 0)), '4' => Some((3, 0)),
        '5' => Some((4, 0)), '6' => Some((5, 0)), '7' => Some((6, 0)), '8' => Some((7, 0)),
        '9' => Some((8, 0)), '0' => Some((9, 0)), '-' => Some((10, 0)), '=' => Some((11, 0)),
        // Row 1
        'q' => Some((0, 1)), 'w' => Some((1, 1)), 'e' => Some((2, 1)), 'r' => Some((3, 1)),
        't' => Some((4, 1)), 'y' => Some((5, 1)), 'u' => Some((6, 1)), 'i' => Some((7, 1)),
        'o' => Some((8, 1)), 'p' => Some((9, 1)), '[' => Some((10, 1)), ']' => Some((11, 1)),
        // Row 2
        'a' => Some((0, 2)), 's' => Some((1, 2)), 'd' => Some((2, 2)), 'f' => Some((3, 2)),
        'g' => Some((4, 2)), 'h' => Some((5, 2)), 'j' => Some((6, 2)), 'k' => Some((7, 2)),
        'l' => Some((8, 2)), ';' => Some((9, 2)), '\'' => Some((10, 2)),
        // Row 3
        'z' => Some((0, 3)), 'x' => Some((1, 3)), 'c' => Some((2, 3)), 'v' => Some((3, 3)),
        'b' => Some((4, 3)), 'n' => Some((5, 3)), 'm' => Some((6, 3)), ',' => Some((7, 3)),
        '.' => Some((8, 3)), '/' => Some((9, 3)),
        // Row 4
        ' ' => Some((5, 4)),
        _ => None,
    }
}

fn dvorak_position(c: char) -> Option<(i32, i32)> {
    match c {
        // Row 0
        '1' => Some((0, 0)), '2' => Some((1, 0)), '3' => Some((2, 0)), '4' => Some((3, 0)),
        '5' => Some((4, 0)), '6' => Some((5, 0)), '7' => Some((6, 0)), '8' => Some((7, 0)),
        '9' => Some((8, 0)), '0' => Some((9, 0)), '[' => Some((10, 0)), ']' => Some((11, 0)),
        // Row 1
        '\'' => Some((0, 1)), ',' => Some((1, 1)), '.' => Some((2, 1)), 'p' => Some((3, 1)),
        'y' => Some((4, 1)), 'f' => Some((5, 1)), 'g' => Some((6, 1)), 'c' => Some((7, 1)),
        'r' => Some((8, 1)), 'l' => Some((9, 1)), '/' => Some((10, 1)), '=' => Some((11, 1)),
        // Row 2
        'a' => Some((0, 2)), 'o' => Some((1, 2)), 'e' => Some((2, 2)), 'u' => Some((3, 2)),
        'i' => Some((4, 2)), 'd' => Some((5, 2)), 'h' => Some((6, 2)), 't' => Some((7, 2)),
        'n' => Some((8, 2)), 's' => Some((9, 2)), '-' => Some((10, 2)),
        // Row 3
        ';' => Some((0, 3)), 'q' => Some((1, 3)), 'j' => Some((2, 3)), 'k' => Some((3, 3)),
        'x' => Some((4, 3)), 'b' => Some((5, 3)), 'm' => Some((6, 3)), 'w' => Some((7, 3)),
        'v' => Some((8, 3)), 'z' => Some((9, 3)),
        // Row 4
        ' ' => Some((5, 4)),
        _ => None,
    }
}

fn colemak_position(c: char) -> Option<(i32, i32)> {
    match c {
        // Row 0
        '1' => Some((0, 0)), '2' => Some((1, 0)), '3' => Some((2, 0)), '4' => Some((3, 0)),
        '5' => Some((4, 0)), '6' => Some((5, 0)), '7' => Some((6, 0)), '8' => Some((7, 0)),
        '9' => Some((8, 0)), '0' => Some((9, 0)), '-' => Some((10, 0)), '=' => Some((11, 0)),
        // Row 1
        'q' => Some((0, 1)), 'w' => Some((1, 1)), 'f' => Some((2, 1)), 'p' => Some((3, 1)),
        'g' => Some((4, 1)), 'j' => Some((5, 1)), 'l' => Some((6, 1)), 'u' => Some((7, 1)),
        'y' => Some((8, 1)), ';' => Some((9, 1)), '[' => Some((10, 1)), ']' => Some((11, 1)),
        // Row 2
        'a' => Some((0, 2)), 'r' => Some((1, 2)), 's' => Some((2, 2)), 't' => Some((3, 2)),
        'd' => Some((4, 2)), 'h' => Some((5, 2)), 'n' => Some((6, 2)), 'e' => Some((7, 2)),
        'i' => Some((8, 2)), 'o' => Some((9, 2)), '\'' => Some((10, 2)),
        // Row 3
        'z' => Some((0, 3)), 'x' => Some((1, 3)), 'c' => Some((2, 3)), 'v' => Some((3, 3)),
        'b' => Some((4, 3)), 'k' => Some((5, 3)), 'm' => Some((6, 3)), ',' => Some((7, 3)),
        '.' => Some((8, 3)), '/' => Some((9, 3)),
        // Row 4
        ' ' => Some((5, 4)),
        _ => None,
    }
}

fn azerty_position(c: char) -> Option<(i32, i32)> {
    match c {
        // Row 0
        '1' => Some((0, 0)), '2' => Some((1, 0)), '3' => Some((2, 0)), '4' => Some((3, 0)),
        '5' => Some((4, 0)), '6' => Some((5, 0)), '7' => Some((6, 0)), '8' => Some((7, 0)),
        '9' => Some((8, 0)), '0' => Some((9, 0)), '-' => Some((10, 0)), '=' => Some((11, 0)),
        // Row 1
        'a' => Some((0, 1)), 'z' => Some((1, 1)), 'e' => Some((2, 1)), 'r' => Some((3, 1)),
        't' => Some((4, 1)), 'y' => Some((5, 1)), 'u' => Some((6, 1)), 'i' => Some((7, 1)),
        'o' => Some((8, 1)), 'p' => Some((9, 1)), '[' => Some((10, 1)), ']' => Some((11, 1)),
        // Row 2
        'q' => Some((0, 2)), 's' => Some((1, 2)), 'd' => Some((2, 2)), 'f' => Some((3, 2)),
        'g' => Some((4, 2)), 'h' => Some((5, 2)), 'j' => Some((6, 2)), 'k' => Some((7, 2)),
        'l' => Some((8, 2)), 'm' => Some((9, 2)), '\'' => Some((10, 2)),
        // Row 3
        'w' => Some((0, 3)), 'x' => Some((1, 3)), 'c' => Some((2, 3)), 'v' => Some((3, 3)),
        'b' => Some((4, 3)), 'n' => Some((5, 3)), ',' => Some((6, 3)), ';' => Some((7, 3)),
        ':' => Some((8, 3)), '/' => Some((9, 3)),
        // Row 4
        ' ' => Some((5, 4)),
        _ => None,
    }
}

pub fn distance(pos1: (i32, i32), pos2: (i32, i32)) -> f64 {
    let dx = (pos1.0 - pos2.0) as f64;
    let dy = (pos1.1 - pos2.1) as f64;
    (dx * dx + dy * dy).sqrt()
}

pub fn apply_distance_modifier(iki_raw: f64, pos1: (i32, i32), pos2: (i32, i32)) -> f64 {
    let d = distance(pos1, pos2);
    iki_raw * (1.0 + (d * 0.05))
}
#[derive(PartialEq, Eq)]
pub enum Hand {
    Left,
    Right,
    Neutral,
}

pub fn get_hand(pos: (i32, i32)) -> Hand {
    if pos == (5, 4) {
        return Hand::Neutral;
    }
    if pos.0 <= 4 {
        Hand::Left
    } else {
        Hand::Right
    }
}

pub fn apply_hand_modifier(iki_raw: f64, prev_pos: (i32, i32), curr_pos: (i32, i32)) -> f64 {
    let h1 = get_hand(prev_pos);
    let h2 = get_hand(curr_pos);

    if h1 == Hand::Neutral || h2 == Hand::Neutral {
        return iki_raw;
    }

    if h1 == h2 {
        iki_raw * 1.15
    } else {
        iki_raw * 0.85
    }
}

pub fn shift_penalty(rng: &mut ClackRng) -> f64 {
    let sigma = SHIFT_PENALTY_SIGMA;
    let mu = SHIFT_PENALTY_MU_MS.ln() - (sigma * sigma / 2.0);
    rng.sample_log_normal(mu, sigma).clamp(SHIFT_PENALTY_MIN_MS, SHIFT_PENALTY_MAX_MS)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_distance_calculations() {
        let qwerty = KeyboardLayout::Qwerty;
        let dvorak = KeyboardLayout::Dvorak;

        let q_a = key_position('a', qwerty).unwrap();
        let q_s = key_position('s', qwerty).unwrap();
        let q_p = key_position('p', qwerty).unwrap();
        
        let d_a = key_position('a', dvorak).unwrap();
        let d_o = key_position('o', dvorak).unwrap();

        let dist_qwerty = distance(q_a, q_s);
        let dist_dvorak = distance(d_a, d_o);
        let far_qwerty = distance(q_a, q_p);

        assert!(dist_qwerty < 1.5, "Qwerty a->s should be close");
        assert!(dist_dvorak < 1.5, "Dvorak a->o should be close");
        assert!(far_qwerty > 5.0, "Qwerty a->p should be far");
    }

    #[test]
    fn test_shift_penalty_calc() {
        let mut rng = crate::rng::ClackRng::new(Some(42));
        let p = shift_penalty(&mut rng);
        assert!(p > 0.0);
    }
}
