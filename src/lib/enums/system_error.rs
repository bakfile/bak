#[allow(nonstandard_style)]
#[derive(Debug, thiserror::Error, Default)]
pub enum SystemError {
    #[error("Unable to detect your system's appdata layout. This is pretty bad. Please contact the bak devs.")]
    BASE_DIRS_ERROR,
    #[error("Corrupt bakfile db detected. Please contact the bak devs for help.")]
    CORRUPT_BAK_DB_ERROR,
    #[error("An unknown error occurred. Please contact the bak devs for help.")]
    #[default]
    UNKNOWN_ERROR
}