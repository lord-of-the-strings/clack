original_rest = """
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
"""

qwerty = [
    r"1234567890-=",
    r"qwertyuiop[]",
    r"asdfghjkl;'",
    r"zxcvbnm,./",
]
dvorak = [
    r"1234567890[]",
    r"',.pyfgcrl/=",
    r"aoeuidhtns-",
    r";qjkxbmwvz"
]
colemak = [
    r"1234567890-=",
    r"qwfpgjluy;[]",
    r"arstdhneio'",
    r"zxcvbkm,./"
]
azerty = [
    r"1234567890-=",
    r"azertyuiop[]",
    r"qsdfghjklm'",
    r"wxcvbn,;:/"
]

def generate_match(layout_lines):
    lines = []
    for r, row in enumerate(layout_lines):
        lines.append(f"        // Row {r}")
        pieces = []
        for c, ch in enumerate(row):
            if ch == "'":
                ch_str = "\"'\""
            elif ch == "\\":
                ch_str = "'\\\\'"
            else:
                ch_str = f"'{ch}'"
            pieces.append(f"{ch_str} => Some(({c}, {r}))")
        
        for i in range(0, len(pieces), 4):
            lines.append("        " + ", ".join(pieces[i:i+4]) + ",")
    lines.append("        // Row 4")
    lines.append("        ' ' => Some((5, 4)),")
    lines.append("        _ => None,")
    return "\n".join(lines)


content = """use crate::constants::*;
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
""" + generate_match(qwerty) + """
    }
}

fn dvorak_position(c: char) -> Option<(i32, i32)> {
    match c {
""" + generate_match(dvorak) + """
    }
}

fn colemak_position(c: char) -> Option<(i32, i32)> {
    match c {
""" + generate_match(colemak) + """
    }
}

fn azerty_position(c: char) -> Option<(i32, i32)> {
    match c {
""" + generate_match(azerty) + """
    }
}
""" + original_rest

with open("clack-core/src/keyboard.rs", "w") as f:
    f.write(content)
