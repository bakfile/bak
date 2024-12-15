use std::fmt;

#[derive(Debug, Default)]
pub enum ExecFailCode {
    Cancel,
    Done,
    BadInput,
    NoBakfilesFound,
    #[default]
    UnspecifiedError,
}

impl fmt::Display for ExecFailCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

impl std::error::Error for ExecFailCode {}