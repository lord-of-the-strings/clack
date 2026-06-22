import os

code_rs = r"""#[derive(Default, Debug, Clone)]
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
"""

with open("clack-core/src/code.rs", "w") as f:
    f.write(code_rs)

with open("clack-core/src/lib.rs", "r") as f:
    lib_rs = f.read()

if "pub mod code;" not in lib_rs:
    lib_rs = lib_rs.replace("pub mod constants;", "pub mod code;\npub mod constants;")

if "pub code_mode: bool," not in lib_rs:
    lib_rs = lib_rs.replace("pub state_output: bool,", "pub state_output: bool,\n    pub code_mode: bool,")
    lib_rs = lib_rs.replace("state_output: false,", "state_output: false,\n            code_mode: false,")

if "code_context:" not in lib_rs:
    lib_rs = lib_rs.replace("accumulated_pause: u64,", "accumulated_pause: u64,\n    code_context: code::CodeContext,")
    lib_rs = lib_rs.replace("accumulated_pause: 0,", "accumulated_pause: 0,\n            code_context: code::CodeContext::new(),")

# Find where `word_mod` is applied
word_mod_target = "let word_mod = language::apply_word_modifier(1.0, word.trim_end());"
new_word_mod = """let mut word_mod = language::apply_word_modifier(1.0, word.trim_end());
        if self.config.code_mode && code::is_code_identifier(word) {
            word_mod *= 1.15; // 15% slowdown for identifiers
        }"""
lib_rs = lib_rs.replace(word_mod_target, new_word_mod)

# Update per-character processing to update code context
char_loop_target = "let c = chars[i];"
new_char_loop = """let c = chars[i];
            if self.config.code_mode {
                self.code_context.update(c);
            }"""
lib_rs = lib_rs.replace(char_loop_target, new_char_loop)

# Apply bracket depth multiplier to target_iki for individual characters
compute_char_iki_target = "let mut iki_raw = timing::sample_raw_iki(&mut self.rng, target_iki, self.config.jitter);"
new_compute_char_iki = """let depth_mod = if self.config.code_mode { self.code_context.get_depth_multiplier() } else { 1.0 };
        let mut iki_raw = timing::sample_raw_iki(&mut self.rng, target_iki * depth_mod, self.config.jitter);"""
lib_rs = lib_rs.replace(compute_char_iki_target, new_compute_char_iki)

with open("clack-core/src/lib.rs", "w") as f:
    f.write(lib_rs)

with open("clack-cli/src/main.rs", "r") as f:
    main_rs = f.read()

if "code_mode: bool," not in main_rs:
    main_rs = main_rs.replace("generate_man: bool,", "generate_man: bool,\n\n    #[arg(long)]\n    code_mode: bool,")
    main_rs = main_rs.replace("config.state_output = cli.state_output;", "config.state_output = cli.state_output;\n    config.code_mode = cli.code_mode;")

with open("clack-cli/src/main.rs", "w") as f:
    f.write(main_rs)
