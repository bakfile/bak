use std::fs::{copy, remove_file};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::rc::Rc;

use anyhow::{Error, Result};
use chrono::Local;
use clap::ArgMatches;
use console::Term;
use dialoguer::Input;

use bakfile::bakdb::{BakDBHandler};
use bakfile::Bakfile;
use bakfile::configuration::Config;

use crate::display::display_bak_list;

pub(crate) fn bak(config: Rc<Config>, bakdb: Rc<BakDBHandler>, matches: ArgMatches) -> Result<()> {
    #[allow(unused_variables)]
    let quiet: bool = matches.get_flag("quiet");
    let file: Option<&String> = matches.get_one("file");
    match matches.subcommand() {
        None => {
            if let Some(file) = file {
                log::debug!("file: {}", file);
                return bak_create_exec(file.into(), config, bakdb);
            }
            else {
                Ok(()) // This should be unreachable
            }
        }
        Some((cmd, submatches)) => {
            let function: &dyn Fn(&ArgMatches, Rc<Config>, Rc<BakDBHandler>) -> Result<()> = match cmd {
                "list" => &bak_list_exec,
                "diff" => &bak_diff_exec,
                "show" | "open" => &bak_open_exec,
                "up" => &bak_up_exec,
                "down" => &bak_down_exec,
                "where" => &bak_where_exec,
                "del" => &bak_del_exec,
                "off" => &bak_off_exec,
                "config" => &bak_config_exec,
                _ => return Ok(()),
            };
            function(&submatches, config, bakdb)
        }
    }
}

fn call_command(command: Command) -> Result<(), anyhow::Error> {
    let mut command = command;
    command.spawn()?.wait()?;
    //TODO handle certain errors here, though a malformed command should panic as it is a bug
    Ok(())
}

fn write_helper(config: &Config, copy_from: &PathBuf, copy_to: &PathBuf, label: &str) -> Result<()> {
    
    let out: Result<(), Error> = match &config.bak_cp_exec {
        Some(val) => {
            let oops = "Fatal error in path handling in exec::write_helper";
            let command = val.replace("%old", copy_from.to_str().expect(oops))
                .replace("%new", copy_to.to_str().expect(oops));
            call_command(Command::new(command))
        }
        None => {
            write_builtin(copy_from, copy_to)
        }
    };
    match out {
        Ok(()) => (),
        Err(e) => {
            log::warn!("{} encountered error: {}", label, e);
            return Err(e.into());
        }
    }
    log::debug!("{}", format_args!("Successfully copied {:?} to {:?}", copy_from, copy_to));
    Ok(())
}

fn write_builtin(copy_from: &PathBuf, copy_to: &PathBuf) -> Result<()> {
    // used to perform copy operations when no copy util is defined in config
    let out = copy(copy_from, copy_to);
    match out {
        Ok(n) => {
        log::trace!("{}", format_args!("Wrote {}B to {:?}", n, copy_to));
        }
        Err(e) => return Err(e.into())
    }
    Ok(())
}

fn bak_list_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    let (_filename, diff, colors, bakfiles) = _bak_list_parameter_helper(submatches, &config, bakdb.clone());
    display_bak_list(&bakfiles, &config, diff, colors, false)
}

fn bak_config_exec(_submatches: &ArgMatches, config: Rc<Config>, _bakdb: Rc<BakDBHandler>) -> Result<()> {
    let term = Term::stdout();
    Ok(term.write_line(&config.to_string().replace("\"", ""))?)
}

fn bak_create_exec(filename: PathBuf, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    let bakfile_dir = bakfile_dir_helper(&config);
    if bakfile_dir.is_err() {
        return Err(bakfile_dir.err().unwrap());
    }
    let bakfile = Bakfile::new(
        filename,
        bakfile_dir.unwrap(),
        Local::now()
    )?;
    log::info!("Creating .bakfile for {:?}", bakfile.original_path);
    match write_helper(
        &config,
        &bakfile.original_path,
        &bakfile.bakfile_path,
        "bakfile creation") {
        Ok(()) => {
            log::debug!("Adding bakfile to database");
            bakdb.create_entry(bakfile)
        }
        Err(e) => Err(e)
    }
}

fn bak_off_exec(submatches: &ArgMatches, _config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    let filename = submatches.get_one::<PathBuf>("file").unwrap(); // Clap should enforce this arg
    let bakfiles = bakdb.get_file_entries(filename.to_owned().into())?;
    log::debug!("Deleting {:#} bakfiles of {:?}", bakfiles.len(), filename);
    for bakfile in bakfiles {
        log::trace!("Deleting: {:?}", bakfile.bakfile_path);
        remove_file(bakfile.bakfile_path)?;
    }
    log::trace!("Removing deleted bakfiles from bakdb");
    match bakdb.del_file_entries(filename.into()) {
        Ok(_) => Ok(()),
        Err(e) => Err(e.into())
    }
}

fn bak_down_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    fn bak_down(config: &Config, bakfile: &Bakfile) -> Result<()> {
        log::debug!(
            "overwriting {:?} to restore from {:?}",
            bakfile.original_path,
            bakfile.bakfile_path
        );
        write_helper(&config,&bakfile.bakfile_path, &bakfile.original_path, "bak down")
    }

    match disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Return, false) {
        Ok(some_bakfile) => {
            bak_down(&config, &some_bakfile.unwrap()) // If this Option is None, there's a bug
        }
        Err(e) => no_bakfiles_found_helper(&submatches, e)
    }
}

fn bak_up_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    fn no_bakfiles_found_fallback(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
        let file: Option<&String> = submatches.get_one("file");
        if let Some(file) = file {
            bak_create_exec(file.into(), config, bakdb.clone())
        }
        else {
            Ok(()) // This should be unreachable, as the file arg is required or else clap just prints bak --help
        }
    }
    let _exec = disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Return, false);
    return match _exec {
        // This apparent spaghetti accounts for a nigh-unreachable codepath as well as the intended path, either of which would result from
        // a 'no .bakfiles found' situation
        Ok(Some(bakfile)) => {
            log::info!(
                "Overwriting .bakfile {:?} for {:?}",
                bakfile.bakfile_path,
                bakfile.original_path
            );
            write_helper(&config, &bakfile.original_path, &bakfile.bakfile_path, "bak up")
        }
        Ok(None) => {
            no_bakfiles_found_fallback(submatches, config, bakdb.clone())
        }
        Err(e) => no_bakfiles_found_helper(&submatches, e)
    }
}

fn bak_del_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    match disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Return, false) {
        Ok(Some(bakfile)) => {
            log::debug!(
                "bak del got bakfile {:?} of {:?}",
                bakfile.bakfile_path,
                bakfile.original_path
            );
            log::debug!("deleting file: {:?}", bakfile.bakfile_path);
            match remove_file(bakfile.clone().bakfile_path) {
                Ok(_) => (),
                Err(e) => return Err(e.into())
            }
            log::debug!("removing .bakfile from database");
            bakdb.del_entry(bakfile).map_err(|e| { e.into() })
        }
        Ok(None) => Ok(()), // should be unreachable
        Err(e) => no_bakfiles_found_helper(submatches, e)
    }
}

fn bak_open_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    match disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Show, false) {
        Ok(_) => Ok(()),
        Err(e) => Err(e)
    }
}

fn bak_diff_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    match disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Diff, false) {
        Ok(_) => Ok(()),
        Err(e) => Err(e)
    }
}

fn bak_where_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: Rc<BakDBHandler>) -> Result<()> {
    match disambiguate_and_execute(submatches, &config, bakdb.clone(), DisambiguatedExecOperation::Return, false) {
        Ok(Some(bakfile)) => {
            println!("{:?}", bakfile.bakfile_path);
            Ok(())
        }
        Ok(None) => Ok(()), // should be unreachable
        Err(e) => no_bakfiles_found_helper(submatches, e)
    }
}

#[derive(Debug, Default)]
enum ExecFailReason {
    Cancel,
    Done,
    BadInput,
    NoBakfilesFound,
    #[default]
    UnspecifiedError,
}

impl std::fmt::Display for ExecFailReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?}", self)
    }
}

impl std::error::Error for ExecFailReason {}

#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) enum DisambiguatedExecOperation {
    Diff,
    Show,
    #[default]
    Return,
}

impl DisambiguatedExecOperation {
    fn as_str(&self) -> &'static str {
        match self {
            DisambiguatedExecOperation::Diff => "diff",
            DisambiguatedExecOperation::Show => "display",
            DisambiguatedExecOperation::Return => "return bakfile",
        } //TODO bak up, down, etc
    }
}

fn bakfile_dir_helper(config: &Config) -> Result<PathBuf> {
    let _path = shellexpand::full(&config.bakfile_location).unwrap();
    let path = PathBuf::from(_path.to_string());
    if !path.exists() {
        match std::fs::create_dir_all(path.clone()) {
            Ok(_) => Ok(path),
            Err(e) => Err(e.into())
        }
    }
    else {
        Ok(path)
    }
}

fn no_bakfiles_found_helper(submatches: &ArgMatches, e: Error) -> Result<()> {
    // Transforms the inner helper into a viable return value for the exec functions
    match _no_bakfiles_found_inner(&submatches, e) {
        Ok(_) => Ok(()),
        Err(e) => Err(e)
    }
}

fn _no_bakfiles_found_inner(matches: &ArgMatches, e: Error) -> Result<()> {
    let _e = e.downcast::<ExecFailReason>();
    match _e {
        Ok(ExecFailReason::NoBakfilesFound) => { 
            let file: Option<&String> = matches.get_one("file");
            println!("No .bakfiles found for {:?}", file.unwrap()); // condition where !file.is_some() is unreachable
            Ok(())
        },
        Ok(_) => Err(_e.unwrap().into()),
        _ => Err(_e.err().unwrap())
    }
}

fn _bak_list_parameter_helper(
    submatches: &ArgMatches,
    config: &Config,
    bakdb: Rc<BakDBHandler>
    ) -> (Option<PathBuf>, bool, bool, Vec<Bakfile>) {
    let filename = match submatches.get_one::<PathBuf>("file") {
        None => None,
        Some(loc) => Some(PathBuf::from(loc)),
    };
    let colors = match submatches.contains_id("colors") {
        true => submatches.get_flag("colors"),
        false => config.bak_list_colors
    };
    let diff = submatches.get_flag("compare");
    let bakfiles = match &filename {
        Some(file) => bakdb.get_file_entries(file.clone()).unwrap(), //TODO failures
        None => bakdb.get_all_entries().unwrap(),
    };
    return (filename, diff, colors, bakfiles);
}

pub(crate) fn disambiguate_and_execute(
    submatches: &ArgMatches,
    config: &Config,
    bakdb: Rc<BakDBHandler>,
    operation: DisambiguatedExecOperation,
    stderr: bool,
) -> Result<Option<Bakfile>> {
    let (filename, diff, colors, bakfiles) =
        _bak_list_parameter_helper(submatches, &config, bakdb.clone());
    log::debug!(
        "running bak operation '{:?}' with params:
        filename: {:?},
        diff: {},
        colors: {}",
        operation,
        filename,
        diff,
        colors
    );
    log::trace!("found {} entries:\n{:?}", bakfiles.len(), bakfiles);
    if bakfiles.is_empty() {
        println!("No bakfiles found for {:?}", filename);
        return Err(ExecFailReason::NoBakfilesFound.into());
    }
    let (bakfile, operation) = match bakfiles.len() > 1 {
        true => match disambiguate(bakfiles,
                                    config,
                                    submatches,
                                    Some(operation),
                                    stderr) {
            Ok(disambiguation_result) => disambiguation_result,
            Err(e) => return Err(e),
        },
        false => {
            let bakfile = bakfiles.get(0).unwrap();
            (bakfile.clone(), operation)
        }
    };

    match operation {
        DisambiguatedExecOperation::Return => {
            return Ok(Some(bakfile));
        }
        _ => match call_command(run_disambiguate_op(&operation, bakfile, &config)?) {
            Ok(_) => Ok(None),
            Err(e) => {
                let err = e.downcast()?;
                match err {
                    ExecFailReason::Done => Ok(None),
                    _ => Err(err.into()),
                }
            }
        },
    }
}

fn disambiguate(
    bakfiles: Vec<Bakfile>,
    config: &Config,
    submatches: &ArgMatches,
    operation: Option<DisambiguatedExecOperation>,
    stderr: bool,
) -> Result<(Bakfile, DisambiguatedExecOperation)> {
    let diff = submatches.get_flag("compare");
    let colors = submatches.get_flag("colors");
    crate::display::display_bak_list(
        &bakfiles,
        &config,
        diff,
        colors,
        stderr,
    )?;

    let mut disambiguate_operation = operation.unwrap_or_default();
    let original_operation = disambiguate_operation.clone();

    let mut firstprompt: bool = true;

    let mut gen_prompt = |operation: &DisambiguatedExecOperation| -> String {
        let _options: &str = match operation {
            &DisambiguatedExecOperation::Diff => "[V]iew",
            &DisambiguatedExecOperation::Show => "[D]iff",
            &DisambiguatedExecOperation::Return => "[V]iew, [D]iff",
        };
        let mut options = _options.to_string();
        if firstprompt {
            firstprompt = false;
        } else {
            options += ", [L]ist"
        }
        options += ", [C]ancel";
        format!(
            "Select a bakfile to {} by entering a number, or\n{}",
            operation.as_str(),
            options.as_str()
        )
    };

    let mut prompt = gen_prompt(&original_operation);

    fn get_input(prompt: &str) -> String {
        Input::<String>::new()
            .with_prompt(prompt)
            .interact_text()
            .unwrap()
            .to_lowercase()
    }

    loop {
        let _input = get_input(&prompt);
        let input = _input.as_str();
        match input.parse::<u64>() {
            Ok(n) => {
                if n <= 0 {
                    println!("Invalid input.");
                    continue;
                }
                // try for bakfile by index
                // let index: usize = match (n - 1).try_into() {
                //     Ok(u) => u,
                //     Err(_) => return Err(ExecFailReason::BadInput.into()),
                // };
                // let selection = bakfiles.iter().nth(index);

                let mut selection: Option<&Bakfile> = None;
                for bakfile in bakfiles.iter() {
                    if bakfile.rowid == Some(n) {
                        selection = Some(bakfile);
                    }
                }

                match selection {
                    None => {
                        println!("Invalid selection.");
                        continue;
                    }
                    Some(bakfile) => {
                        if disambiguate_operation == original_operation {
                            // This is what the user originally called. Return the selected bakfile upstairs to execute the operation.
                            return Ok((bakfile.clone(), disambiguate_operation));
                        }
                        // The user has selected an alternative operation
                        call_command(run_disambiguate_op(
                            // run_disambiguate_op() will build the shell command, and call_command will... yep
                            &disambiguate_operation,
                            bakfile.clone(),
                            &config,
                        )?)?;
                        // We have finished the alternative operation. Go back to the first one.
                        disambiguate_operation = original_operation.clone();
                        prompt = gen_prompt(&original_operation);
                    }
                }
            }
            Err(_) => {
                // try for a different option from above
                let operation = input.chars().nth(0);
                log::trace!(
                    "Input not a uint. Trying first unicode char... {}",
                    match operation {
                        Some(c) => format!("'{}'", c),
                        None => "failed".to_string(),
                    }
                );
                match operation {
                    Some('d') => {
                        log::debug!("User selection: diff");
                        disambiguate_operation = DisambiguatedExecOperation::Diff;
                    }
                    Some('v') => {
                        log::debug!("User selection: show");
                        disambiguate_operation = DisambiguatedExecOperation::Show;
                    }
                    Some('c') => {
                        log::debug!("User selection: cancel");
                        return Err(ExecFailReason::Cancel.into());
                    }
                    Some('l') => {
                        log::debug!("User selection: list");
                        crate::display::display_bak_list(
                            &bakfiles,
                            &config,
                            diff,
                            colors,
                            stderr,
                        )?;
                    }
                    _ => {
                        log::debug!("User input not recognized");
                        return Err(ExecFailReason::BadInput.into());
                    }
                }
                prompt = gen_prompt(&disambiguate_operation);
            }
        }
    }
}

fn just_execute(
    _submatches: &ArgMatches,
    config: &Config,
    bakfile: Bakfile,
    operation: DisambiguatedExecOperation,
    ) -> anyhow::Result<()> {
    call_command(run_disambiguate_op(&operation, bakfile, config)?)
}

#[allow(unreachable_patterns)]
fn run_disambiguate_op(
    operation: &DisambiguatedExecOperation,
    bakfile: Bakfile,
    config: &Config) -> Result<Command> {
    let mut command_string: String;
    match operation {
        DisambiguatedExecOperation::Diff => {
            command_string = config.bak_diff_exec.clone();
        }
        DisambiguatedExecOperation::Show => {
            command_string = config.bak_open_exec.clone();
        }
        DisambiguatedExecOperation::Return => return Err(ExecFailReason::Done.into()),
        // unreachable?
        _ => {
            log::debug!("{:?}", operation);
            return Err(ExecFailReason::UnspecifiedError.into()); //TODO this is a failure and stuff
        }
    }

    let expanded = shellexpand::full(&command_string)?;
    command_string = expanded.to_string();
    command_string = command_string
                        .replace("%f", bakfile.bakfile_path.to_str().unwrap()) // for Show operation
                        .replace("%new", bakfile.bakfile_path.to_str().unwrap()) // for Diff operation
                        .replace("%old", bakfile.original_path.to_str().unwrap());
    log::debug!("executing: {}", command_string);
    let command_split: Vec<&str> = command_string.split(' ').collect();

    let mut command = Command::new(command_split[0]);
    command.args(&command_split[1..]);
    log::trace!(
        "parsed to: {:?} {:?}",
        command.get_program(),
        command.get_args()
    );
    Ok(command)
}
