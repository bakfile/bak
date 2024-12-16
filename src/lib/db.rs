use std::path::PathBuf;
use std::rc::Rc;

use anyhow::{Context, Result};
use log::{debug, warn};
use rusqlite::{params, Connection, Row, Rows};

use crate::Bakfile;
use crate::config::Config;
use crate::util::SystemError;

#[allow(nonstandard_style)]
const FRESH_DB_COMMAND: &'static str =
    "CREATE TABLE if not exists bakfiles (original_file, original_abspath, bakfile, date_created, date_modified, restored)";

fn get_connection(configuration: &Config) -> rusqlite::Result<Connection> {
    let path = PathBuf::from(configuration.bak_database_location.clone());
    if path.exists() {
        debug!("Connecting to database: {}", path.display());
        let conn =
            Connection::open_with_flags(path, rusqlite::OpenFlags::SQLITE_OPEN_READ_WRITE)
                .expect(&SystemError::CORRUPT_BAK_DB_ERROR.to_string());
        debug!("Database connection successful");
        return Ok(conn);
    }
    warn!(
        "Bakfile database not found. Writing a new one at: {}",
        path.to_str().unwrap()
    );
    let conn = Connection::open(path);
    match conn {
        Ok(ref _conn) => {}
        Err(e) => {
            return Err(e);
        }
    };
    let conn = conn.expect(&SystemError::CORRUPT_BAK_DB_ERROR.to_string());
    debug!("Empty database created");
    conn.execute(FRESH_DB_COMMAND, [])
        .expect("Unable to write fresh bakfile database.");
    debug!("Clean bakfile database successfully written");
    Ok(conn)
}

pub struct BakDBHandler<'db> {
    configuration: Rc<Config>,
    pub(crate) conn: Connection,
    _lifetimehell: std::marker::PhantomData<&'db bool>,
}

impl<'db> BakDBHandler<'db> {
    pub fn new(configuration: Rc<Config>) -> Result<BakDBHandler<'db>, rusqlite::Error> {
        let path = PathBuf::from(configuration.bak_database_location.clone());
        if !path.exists() {
            std::fs::create_dir_all(path.parent().unwrap()).expect("failed to create containing folders for bakfile database");
        }
        let conn = get_connection(&configuration).unwrap();
        let out = BakDBHandler {
            configuration,
            conn,
            _lifetimehell: std::marker::PhantomData,
        };
        Ok(out)
    }

    fn construct_bakfile_from_entry(&self, row: &Row) -> Result<Bakfile, rusqlite::Error> {
        // crash loudly and human_panic, because errors in the bakdb are catastrophic
        let rowid: u64 = row.get(0)?;
        let filename: String = row.get("original_file")?;
        let _bakfile_path: String = row.get("bakfile")?;
        let bakfile_path = PathBuf::from(_bakfile_path);
        let _original_path: String = row.get("original_abspath")?;
        let original_path = PathBuf::from(_original_path);
        let _initial_creation: String = row.get("date_created")?;
        let initial_creation = chrono::DateTime::parse_from_rfc3339(&_initial_creation)
            .expect("Invalid datetime in bak DB")
            .with_timezone(&chrono::Local);
        let _last_updated: String = row.get("date_modified")?;
        let last_updated = chrono::DateTime::parse_from_rfc3339(&_last_updated)
            .expect("Invalid datetime in bak DB")
            .with_timezone(&chrono::Local);
        let _restored: i8 = row.get("restored")?;
        //let _restored: i8 = _restored_string.parse().unwrap(); //TODO
        let restored: bool = _restored != 0;
        let out = Bakfile {
            filename: filename.into(),
            bakfile_path,
            original_path,
            initial_creation,
            last_updated,
            restored,
            rowid: Some(rowid),
        };
        Ok(out)
    }

    fn construct_bakfiles_from_entries(
        &self,
        mut rows: Rows,
    ) -> Result<Vec<Bakfile>, rusqlite::Error> {
        let mut out: Vec<Bakfile> = vec![];
        loop {
            let contents = rows.next()?;
            match contents {
                None => {
                    break;
                }
                Some(row) => {
                    out.push(self.construct_bakfile_from_entry(row).unwrap());
                }
            }
        }
        Ok(out)
    }

    pub fn create_entry(&self, bakfile: Bakfile) -> Result<()> {
        let out = self.conn.execute(
            "
                INSERT INTO bakfiles VALUES
                (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                bakfile.filename.to_str(),
                String::from(
                    bakfile
                        .original_path
                        .to_str()
                        .expect("Malformed Bakfile object: bad original_path"),
                ),
                String::from(
                    bakfile
                        .bakfile_path
                        .to_str()
                        .expect("Malformed Bakfile object: bad bakfile_path"),
                ),
                bakfile.initial_creation.to_rfc3339(),
                bakfile.last_updated.to_rfc3339(),
                bakfile.restored as i32,
            ],
        );
        match out {
            Err(e) => Err(e.into()),
            _ => Ok(()),
        }
    }

    // TODO clean this up when the rest of this file is anyhowified
    pub fn get_entry_by_rowid(&self, rowid: u64) -> anyhow::Result<Bakfile> {
        let func_context = "bak::db::BakDBHandler::get_entry_by_rowid";
        match self.conn.query_row(
            "SELECT rowid, * from bakfiles WHERE rowid = (?)",
            params![rowid],
            |row| self.construct_bakfile_from_entry(row),
        ) {
            Ok(bakfile) => Ok(bakfile),
            Err(e) => match e {
                rusqlite::Error::QueryReturnedNoRows => Err(anyhow::Error::new(
                    crate::util::ExecFailCode::NoBakfilesFound,
                ))
                .context(func_context),
                _ => Err(anyhow::Error::new(e)).context(func_context),
            },
        }
    }

    pub fn get_file_entries(&self, path: PathBuf) -> Result<Vec<Bakfile>, rusqlite::Error> {
        let mut statement = self
            .conn
            .prepare("SELECT rowid, * FROM bakfiles WHERE original_abspath = (?) ORDER BY rowid")?;
        let rows = statement.query([path.to_str()])?;
        self.construct_bakfiles_from_entries(rows)
    }

    pub fn get_all_entries(&self) -> Result<Vec<Bakfile>, rusqlite::Error> {
        let mut statement = self
            .conn
            .prepare("SELECT rowid, * FROM bakfiles ORDER BY rowid")?;
        let rows = statement.query([])?;
        self.construct_bakfiles_from_entries(rows)
    }

    pub fn del_entry(&self, bakfile: Bakfile) -> Result<(), rusqlite::Error> {
        let params = params![bakfile.bakfile_path.to_str()];
        match self.conn.execute(
            "SELECT * FROM bakfiles WHERE bakfile_path = ?1 ORDER BY rowid",
            params,
        ) {
            Ok(1) => {
                match self
                    .conn
                    .execute("DELETE FROM bakfiles WHERE bakfile_path = ?1", params)
                {
                    Ok(1) => return Ok(()),
                    Ok(_) => {
                        panic!("Catastrophic error updating bakfile database: deleted too many entries");
                    }
                    Err(e) => {
                        return Err(e);
                    }
                }
            }
            Ok(_) => {
                panic!(
                    "Error removing entry from bakfile database: too many entries matched query"
                );
            }
            Err(e) => {
                return Err(e);
            }
        }
    }

    pub fn del_file_entries(&self, file: PathBuf) -> Result<usize, rusqlite::Error> {
        let params = params![file.to_str()];
        match self
            .conn
            .execute("DELETE FROM bakfiles WHERE original_abspath = ?1", params)
        {
            Ok(n) => return Ok(n),
            Err(e) => {
                return Err(e);
            }
        }
    }

    pub fn update_bakfile_entry(
        &self,
        old_bakfile: Bakfile,
        new_bakfile: Bakfile,
    ) -> Result<(), rusqlite::Error> {
        let old_params = params![
            old_bakfile.bakfile_path.to_str(),
            old_bakfile.initial_creation.to_rfc3339()
        ];
        match self.conn.execute(
            "SELECT * FROM bakfiles WHERE bakfile_path = ?1 AND initial_creation = ?2 ORDER BY rowid",
            old_params,
        ) {
            Ok(1) => {
                match self.conn.execute(
                    "DELETE FROM bakfiles WHERE bakfile_path = ?1 AND initial_creation = ?2",
                    old_params,
                ) {
                    Ok(1) => (),
                    Ok(_) => {
                        panic!("Catastrophic error updating bakfile database: deleted too many entries before inserting new entry");
                    }
                    Err(e) => {
                        return Err(e);
                    }
                };
                self.create_entry(new_bakfile).unwrap();
                Ok(())
            }
            Ok(_) => {
                panic!("Error updating bakfile database: found too many bakfiles matching query");
            }
            Err(e) => Err(e),
        }
    }

    pub fn set_restored_flag(
        &self,
        bakfile: Bakfile,
        status: bool,
    ) -> Result<(), rusqlite::Error> {
        match self.conn.execute(
            "UPDATE bakfiles SET restored = ?1 WHERE bakfile_path = ?2 AND initial_creation = ?3",
            params![
                status,
                bakfile.bakfile_path.to_str(),
                bakfile.initial_creation.to_rfc3339()
            ],
        ) {
            Ok(1) => Ok(()),
            Ok(_) => {
                panic!("Error writing to bakfile database: wrote too many restored flags at once");
            }
            Err(e) => Err(e),
        }
    }
}