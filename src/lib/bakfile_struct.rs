/***
 * This struct represents a bakfile at runtime. It's used by the db handler and "downstream" by the executable.
 * If you need to change it, you probably want to use a robust editor or you're gonna spend ages chasing references.
 */
use std::ffi::OsString;
use std::io::Error as IOError;
use std::path::PathBuf;

use chrono::{DateTime, Local};

#[derive(Clone, Debug)]
pub struct Bakfile {
    pub filename: OsString,                 // relative path for display
    pub bakfile_path: PathBuf,              // abspath to .bak
    pub original_path: PathBuf,             // abspath to original file
    pub initial_creation: DateTime<Local>,  // creation of bakfile
    pub last_updated: DateTime<Local>,      // last explicit operation
    pub restored: bool,                     // TODO track user, group, perms?
    pub rowid: Option<u64>,                 // Bakfile objects created during bakfile creation won't have a rowid from the database
}

impl Bakfile {
    pub fn new(
        i_filename: PathBuf,
        bakfile_dir: PathBuf,
        when: chrono::DateTime<Local>,
        ) -> Result<Bakfile, IOError> {
        // Does not actually copy the bakfile! That's the executable's problem.
        let _filename = std::fs::canonicalize(i_filename);
        let absolute_path = match _filename {
            Ok(some_path) => match some_path.try_exists() {
                Ok(true) => some_path,
                _ => {
                    return Err(IOError::from(
                        std::io::ErrorKind::NotFound));
                }
            },
            Err(e) => {
                return Err(e);
            }
        };
        let filename = absolute_path
            .file_name()
            .unwrap_or(absolute_path.as_os_str());

        let out = Bakfile {
            filename: filename.to_os_string(),
            bakfile_path: Self::generate_bakfile_path(&absolute_path, when, bakfile_dir).unwrap(),
            original_path: absolute_path,
            initial_creation: when,
            last_updated: when,
            restored: false,
            rowid: None,
        };
        log::trace!("Generated bakfile struct: {:?}", out);
        Ok(out)
    }

    fn generate_bakfile_path(
        abspath: &PathBuf,
        when: chrono::DateTime<Local>,
        bakfile_dir: PathBuf,
    ) -> Result<PathBuf, IOError> {
        let mut new_filename = abspath
            .to_string_lossy()
            .replace("/", "-")
            .strip_prefix("-")
            .unwrap()
            .to_string();
        new_filename = new_filename
            + format!(
                ".{}.bak",
                format_args!("{}-{}", when.timestamp(), when.timestamp_subsec_micros())
            )
            .as_str();
        Ok(bakfile_dir.join(new_filename))
    }
}
