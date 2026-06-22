use crate::constants::ERROR_RATE_MAX_EFFECTIVE;
use crate::rng::ClackRng;

pub enum ErrorType {
    Typo,
    Transposition,
    Omission,
    PanicStuckKey,
    PanicPrefix,
}

pub fn should_generate_error(rng: &mut ClackRng, error_rate: f64) -> bool {
    let effective_rate = error_rate.min(ERROR_RATE_MAX_EFFECTIVE);
    rng.sample_bool(effective_rate)
}

pub fn select_error_type(rng: &mut ClackRng) -> ErrorType {
    let roll = rng.sample_uniform(0.0, 1.0);
    if roll < 0.65 {
        ErrorType::Typo
    } else if roll < 0.90 {
        ErrorType::Transposition
    } else if roll < 0.98 {
        ErrorType::Omission
    } else if roll < 0.99 {
        ErrorType::PanicStuckKey
    } else {
        ErrorType::PanicPrefix
    }
}

pub fn generate_typo(rng: &mut ClackRng, c: char) -> char {
    // simplified adjacent keys for MVP
    let adjacents = match c.to_ascii_lowercase() {
        'q' => "wa", 'w' => "qeas", 'e' => "wrsd", 'r' => "etdf", 't' => "ryfg", 'y' => "tugh",
        'u' => "yijh", 'i' => "uokj", 'o' => "iplk", 'p' => "o[l", 'a' => "qwsz", 's' => "awedxz",
        'd' => "serfcx", 'f' => "drtgvc", 'g' => "ftyhvb", 'h' => "gyujbn", 'j' => "huiknm",
        'k' => "jiolm,", 'l' => "kop;.", 'z' => "asx", 'x' => "zsdc", 'c' => "xdfv", 'v' => "cfgb",
        'b' => "vghn", 'n' => "bhjm", 'm' => "njk,",
        _ => "x",
    };
    let idx = rng.sample_uniform_int(0, adjacents.len() - 1);
    adjacents.chars().nth(idx).unwrap()
}
