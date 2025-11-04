use std::fs::{copy, remove_file};
use std::io::Write;
use std::path::PathBuf;
use std::process::Command;
use std::rc::Rc;

use anyhow::{Error, Result};
use chrono::Local;
use clap::ArgMatches;
use dialoguer::Input;

use bakfile::bakdb::BakDBHandler;
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
                return bak_create_exec(file.into(), config, &bakdb);
            }
            else {
                Ok(()) // This should be unreachable
            }
        }
        Some((cmd, submatches)) => {
            let function: &dyn Fn(&ArgMatches, Rc<Config>, &BakDBHandler) -> Result<()> = match cmd {
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
            let result = function(&submatches, config, &bakdb);
            if result.is_err() {
                return no_bakfiles_found_helper(
                    submatches,
                    true,
                    result.err().unwrap())
            }
            result
        }
    }
}

fn call_command(mut command_string: String, config: &Config, escalate: bool) -> Result<(), anyhow::Error> {
    if cfg!(unix) && escalate {
    log::trace!("got sudo command: {}", &config.sudo_command);
        command_string = config.sudo_command.replace("%c", &command_string);
        command_string = command_string.replace("%q", "\"");
    }
    log::debug!("executing: {}", command_string);
    let command_split: Vec<&str> = command_string.split(' ').collect();

    let mut command = Command::new(command_split[0]);
    command.args(&command_split[1..]);
    log::trace!(
        "parsed to: {:?} {:?}",
        command.get_program(),
        command.get_args()
    );
    log::trace!("calling command: {:?}", command);
    command.spawn()?.wait()?;
    Ok(())
}

fn write_helper(config: &Config, copy_from: &PathBuf, copy_to: &PathBuf, label: &str, escalate: bool) -> Result<()> {
    
    let out: Result<(), Error> = match &config.bak_cp_exec {
        Some(val) => {
            let oops = "Fatal error in path handling in exec::write_helper";
            let command_string = val.replace("%old", copy_from.to_str().expect(oops))
                .replace("%new", copy_to.to_str().expect(oops));
            call_command(command_string, &config, escalate)
        }
        None => {
            write_builtin(copy_from, copy_to)
        }
    };
    match out {
        Ok(()) => (),
        Err(e) => {
            log::warn!("{} encountered error: {}", label, e);
            return Err(e);
        }
    }
    log::debug!("{}", format_args!("copy operation from {:?} to {:?} returned a good exit code 
                (this does not mean the copy was successsful)", copy_from, copy_to));
    Ok(())
}

fn write_builtin(copy_from: &PathBuf, copy_to: &PathBuf) -> Result<()> {
    // used to perform copy operations when no copy util is defined in config
    let bytes = copy(copy_from, copy_to)?;
    log::trace!("{}", format_args!("Wrote {}B to {:?}", bytes, copy_to));
    Ok(())
}

fn bak_list_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    let (_filename, diff, colors, bakfiles) = _bak_list_parameter_helper(submatches, &config, &bakdb);
    if bakfiles.is_empty() {
        no_bakfiles_found_helper(submatches, true, anyhow::anyhow!(ExecFailReason::NoBakfilesFound))?;
        return Ok(());
    }
    display_bak_list(&bakfiles, &config, diff, colors, false)
}

fn bak_config_exec(_submatches: &ArgMatches, config: Rc<Config>, _bakdb: &BakDBHandler) -> Result<()> {
    println!("{}", &config.to_string().replace("\"", ""));
    Ok(())
}

fn bak_create_exec(filename: PathBuf, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    let bakfile_dir = bakfile_dir_helper(&config)?;
    let bakfile = Bakfile::new(
        filename,
        bakfile_dir,
        Local::now()
    )?;
    log::info!("Creating .bakfile for {}", bakfile.original_path.to_string_lossy());
    match write_helper(
        &config,
        &bakfile.original_path,
        &bakfile.bakfile_path,
        "bakfile creation",
        false) {
        Ok(()) => {
            log::debug!("Adding bakfile to database");
            bakdb.create_entry(bakfile)
        }
        Err(e) => Err(e)
    }
}

fn bak_off_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    let filename = submatches.get_one::<PathBuf>("file").unwrap(); // Clap should enforce this arg
    let bakfiles = bakdb.get_file_entries(filename.to_owned().into())?;
    if bakfiles.is_empty() {
        return Err(anyhow::anyhow!(ExecFailReason::NoBakfilesFound))
    }
    if !confirm_helper(format!("Delete all bakfiles of {}?", filename.to_string_lossy()).as_str(),
    quiet(&submatches, &config))? {
        return Ok(())
    }
    log::debug!("Deleting {:#} bakfiles of {:?}", bakfiles.len(), filename);
    for bakfile in bakfiles {
        log::trace!("Deleting: {:?}", bakfile.bakfile_path);
        remove_file(bakfile.bakfile_path)?;
    }
    log::trace!("Removing deleted bakfiles from bakdb");
    bakdb.del_file_entries(filename.into())?;
    Ok(())
}

fn bak_down_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    fn bak_down(submatches: &ArgMatches, config: &Config, bakfile: &Bakfile) -> Result<()> {
    if !confirm_helper(format!("Overwrite {} and restore from bakfile?", bakfile.original_path.to_string_lossy()).as_str(),
                quiet(&submatches, &config))?  {
        return Ok(())
    }
        log::debug!(
            "overwriting {:?} to restore from {:?}",
            bakfile.original_path,
            bakfile.bakfile_path
        );
        write_helper(&config,&bakfile.bakfile_path, &bakfile.original_path, "bak down", submatches.get_flag("escalate"))
    }

    let some_bakfile = execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Return, false)?;
    bak_down(&submatches, &config, &some_bakfile.unwrap()) // If this Option is None, there's a bug
}

fn bak_up_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    fn no_bakfiles_found_fallback(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
        let file: Option<&PathBuf> = submatches.get_one("file");
        if let Some(file) = file {
            bak_create_exec(file.to_owned(), config, &bakdb)
        }
        else {
            Ok(()) // This should be unreachable, as the file arg is required or else clap just prints bak --help
        }
    }
    let _exec = execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Return, false);
    return match _exec {
        // This apparent spaghetti accounts for a nigh-unreachable codepath as well as the intended path, either of which would result from
        // a 'no .bakfiles found' situation
        Ok(Some(bakfile)) => {
            if !confirm_helper(format!("Overwrite bakfile with current version of {}?", bakfile.original_path.to_string_lossy()).as_str(),
                quiet(&submatches, &config))? {
                return Ok(())
            }
            log::info!(
                "Overwriting .bakfile {} for {}",
                bakfile.bakfile_path.to_string_lossy(),
                bakfile.original_path.to_string_lossy()
            );
            write_helper(&config, &bakfile.original_path, &bakfile.bakfile_path, "bak up", submatches.get_flag("escalate"))
        }
        Ok(None) => {
            no_bakfiles_found_fallback(submatches, config, &bakdb)
        }
        Err(e) => {
            no_bakfiles_found_helper(&submatches, false, e)?; // If the error isn't NoBakfilesFound, ? will propagate it
            no_bakfiles_found_fallback(submatches, config, &bakdb) // If it was, fall back on create
        }
    }
}

fn bak_del_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    let bakfile = execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Return, false)?.unwrap();
        log::debug!(
            "bak del got bakfile {:?} of {:?}",
            bakfile.bakfile_path,
            bakfile.original_path
        );
        if !confirm_helper(format!("Delete bakfile of {}?", bakfile.original_path.to_string_lossy()).as_str(),
        quiet(&submatches, &config))? {
            return Ok(())
        }
        log::debug!("deleting file: {:?}", bakfile.bakfile_path);
        remove_file(bakfile.clone().bakfile_path)?;
        log::debug!("removing .bakfile from database");
        bakdb.del_entry(bakfile).map_err(|e| { e.into() })
}

fn bak_open_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Show, false)?;
    Ok(())
}

fn bak_diff_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Diff, false)?;
    Ok(())
}

fn bak_where_exec(submatches: &ArgMatches, config: Rc<Config>, bakdb: &BakDBHandler) -> Result<()> {
    let bakfile = execute(submatches, &config, &bakdb, DisambiguatedExecOperation::Return, true)?.unwrap();
    println!("{}", bakfile.bakfile_path.to_str().unwrap());
    Ok(())
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
        write!(f, "{}", self)
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

pub(crate) fn quiet(submatches: &ArgMatches, config: &Config) -> bool {
    return submatches.get_flag("quiet") || (config.quiet && !submatches.get_flag("no_quiet"));
}

fn confirm_helper(prompt: &str, quiet: bool) -> Result<bool> {
    if quiet { return Ok(true); }
    loop {
        let input = Input::<String>::new();
        match input.with_prompt(prompt.to_owned() + "\n" + "(Y/N)").interact_text().unwrap().to_lowercase().as_str() {
            "y" => return Ok(true),
            "n" => return Ok(false),
            _ => ()
        }
    }
}

fn bakfile_dir_helper(config: &Config) -> Result<PathBuf> {
    let _path = shellexpand::full(&config.bakfile_location)?;
    let path = PathBuf::from(_path.to_string());
    if !path.exists() {
        std::fs::create_dir_all(path.clone())?;
        Ok(path)
    }
    else {
        Ok(path)
    }
}

fn no_bakfiles_found_helper(submatches: &ArgMatches, print: bool, e: Error) -> Result<()> {
    let _e = e.downcast::<ExecFailReason>();
    match _e {
        Ok(ExecFailReason::NoBakfilesFound) => { 
            let file: Option<&PathBuf> = submatches.get_one("file");
            if print {
                let mut term = console::Term::stderr();
                term.write("No .bakfiles found".as_bytes())?; 
                if file.is_some() {
                    term.write(format!(" for {}\n",
                    file.as_deref().unwrap().to_str().unwrap()).as_bytes())?; // condition where !file.is_some() is unreachable
                }
                else {
                    term.write("\n".as_bytes())?;
                }
            }
            Ok(())
        },
        Ok(_) => Err(anyhow::anyhow!(_e.unwrap())),
        _ => Err(_e.err().unwrap())
    }
}

fn _bak_list_parameter_helper(
    submatches: &ArgMatches,
    config: &Config,
    bakdb: &BakDBHandler
    ) -> (Option<PathBuf>, bool, bool, Vec<Bakfile>) {
    let filename = match submatches.get_one::<PathBuf>("file") {
        None => None,
        Some(loc) => Some(PathBuf::from(loc)),
    };
    let colors = match submatches.contains_id("colors") {
        true => submatches.get_flag("colors"),
        false => config.bak_list_colors
    };
    let diff = submatches.get_flag("compare") || (config.bak_list_diff && !submatches.get_flag("nocompare"));
    let bakfiles = match &filename {
        Some(file) => bakdb.get_file_entries(file.clone()).unwrap(), //TODO failures
        None => bakdb.get_all_entries().unwrap(),
    };
    return (filename, diff, colors, bakfiles);
}

fn execute(
    submatches: &ArgMatches,
    config: &Config,
    bakdb: &BakDBHandler,
    operation: DisambiguatedExecOperation,
    stderr: bool) -> Result<Option<Bakfile>> {
        log::trace!("executing: {:?}", operation);
        if let Some(id) = submatches.get_one("num") {
            log::trace!("getting bakfile");
            let bakfile = bakdb.get_entry_by_rowid(*id)?;
            log::trace!("bakfile found: {:?}", bakfile);
            just_execute(submatches, &config, bakfile, operation)
        }
        else {
            return disambiguate_and_execute(submatches, &config, &bakdb, operation, stderr);
        }
    }
fn disambiguate_and_execute(
    submatches: &ArgMatches,
    config: &Config,
    bakdb: &BakDBHandler,
    operation: DisambiguatedExecOperation,
    stderr: bool,
) -> Result<Option<Bakfile>> {
    let (filename, diff, colors, bakfiles) =
        _bak_list_parameter_helper(submatches, &config, &bakdb);
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
        return Err(anyhow::anyhow!(ExecFailReason::NoBakfilesFound));
    }
    let (bakfile, operation) = match bakfiles.len() > 1 {
        true => match disambiguate(bakfiles,
                                    config,
                                    submatches,
                                    Some(operation),
                                    stderr,
                                    diff,
                                    colors) {
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
        _ => match run_disambiguate_op(&operation, bakfile, &submatches, &config) {
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
    diff: bool,
    colors: bool
) -> Result<(Bakfile, DisambiguatedExecOperation)> {
    display_bak_list(
        &bakfiles,
        &config,
        diff,
        colors,
        stderr
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
                    console::Term::stderr().write_line("Invalid input.")?;
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
                        console::Term::stderr().write_line("Invalid selection.")?;
                        continue;
                    }
                    Some(bakfile) => {
                        if disambiguate_operation == original_operation {
                            // This is what the user originally called. Return the selected bakfile upstairs to execute the operation.
                            return Ok((bakfile.clone(), disambiguate_operation));
                        }
                        // The user has selected an alternative operation
                        run_disambiguate_op(
                            // run_disambiguate_op() will build and call the shell command
                            &disambiguate_operation,
                            bakfile.clone(),
                            &submatches,
                            &config,
                        )?;
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
    submatches: &ArgMatches,
    config: &Config,
    bakfile: Bakfile,
    operation: DisambiguatedExecOperation,
    ) -> Result<Option<Bakfile>> {
    if operation == DisambiguatedExecOperation::Return {
        return Ok(Some(bakfile))
    }
    run_disambiguate_op(&operation, bakfile.clone(), submatches, config)?;
    Ok(None)

}

#[allow(unreachable_patterns)]
fn run_disambiguate_op(
    operation: &DisambiguatedExecOperation,
    bakfile: Bakfile,
    submatches: &ArgMatches,
    config: &Config) -> Result<()> {
    let mut command_string: String;
    match operation {
        DisambiguatedExecOperation::Diff => {
            command_string = config.bak_diff_exec.clone();
        }
        DisambiguatedExecOperation::Show => {
            command_string = match submatches.get_one::<String>("program") {
                Some(program)=> program.to_owned() + &" %f".to_string(),
                None => config.bak_open_exec.clone()
            }
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
    call_command(command_string, &config, submatches.get_flag("escalate"))
}
