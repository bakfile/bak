// This file just exports the contents of the `enums` directory.
// They're organized for use under `crate::utils` and exported in `../lib.rs`
mod fail_codes;
mod system_error;

pub use fail_codes::ExecFailCode;
pub use system_error::SystemError;