#[derive(Default, Debug, Clone)]
pub struct CodeContext {
    pub bracket_depth: usize,
    pub in_string: bool,
    pub string_char: Option<char>,
}

impl CodeContext {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn update(&mut self, c: char) {
        if self.in_string {
            if Some(c) == self.string_char {
                self.in_string = false;
                self.string_char = None;
            }
        } else {
            match c {
                '{' | '[' | '(' => self.bracket_depth += 1,
                '}' | ']' | ')' => self.bracket_depth = self.bracket_depth.saturating_sub(1),
                '"' | '\'' | '`' => {
                    self.in_string = true;
                    self.string_char = Some(c);
                }
                _ => {}
            }
        }
    }

    pub fn get_depth_multiplier(&self) -> f64 {
        1.0 + (self.bracket_depth as f64 * 0.05)
    }
}

pub fn is_code_identifier(word: &str) -> bool {
    let trimmed = word.trim_end();
    if trimmed.contains('_') {
        return true;
    }
    let has_lower = trimmed.chars().any(|c| c.is_lowercase());
    let has_upper = trimmed.chars().any(|c| c.is_uppercase());
    if has_lower && has_upper {
        return true;
    }
    false
}
