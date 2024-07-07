extern crate directories;
extern crate shellexpand;

use log::{info, trace};
use shellexpand::LookupError;
use std::{borrow::Cow, path::PathBuf};

use anyhow::Result;

use crate::config::{get_default_bakfile_loc, get_default_bak_db_loc};

pub fn get_config_template_string(i_config: &crate::config::Config) -> Result<String> {
    #[allow(nonstandard_style)]
    let BAK_OPEN_DEFAULT: &str = "$PAGER %bakfile";
    #[allow(nonstandard_style)]
    let BAK_DIFF_DEFAULT: &str = "diff %bakfile %file";

    fn expando_the_magnificent(i_str: &str, get_default: fn() -> Result<PathBuf, anyhow::Error>) -> Result<Cow<str>> {
    // Just a helper to replace a snippet that I kept rewriting in two places
        let expanded: Result<Cow<str>, LookupError<std::env::VarError>> = shellexpand::full(i_str);
        match expanded {
            Ok(some_value) => Ok(some_value),
            Err(LookupError) => {
                let out: String = get_default();
                info!("Invalid value detected in config: {}\n
                        Reverting to default value: {}", i_str, &out);
                Ok(Cow::from(out))
            }
        }
    }

    let bakfile_location: Result<PathBuf> = {
        let i_str = i_config.bakfile_location.as_str();
        match i_str {
            "default" => get_default_bakfile_loc()?,
            _ => {
                trace!("detected bakfile_location: {}", i_str);
                let expanded = expando_the_magnificent(i_str, get_default_bakfile_loc).unwrap_or("default");
                match expanded.as_str() {
                    "default" => get_default_bakfile_loc()?,
                    _ => PathBuf::from(expanded)
                }
            }
        }
    };
    let bak_database_location: PathBuf = match i_config.bak_database_location.as_str() {
        "default" => get_default_bak_db_loc()?,
        _ => {
            let input_value = expando_the_magnificent(i_config.bak_database_location.as_str(), get_default_bak_db_loc)
                .unwrap_or(Cow::from("default"))
                .into_owned();
            match input_value.as_str() {
                "default" => get_default_bakfile_loc()?,
                _ => PathBuf::from(input_value),
            }
        }
    };
    let bak_open_exec: String = match i_config.bak_open_exec.as_str() {
        "default" => BAK_OPEN_DEFAULT.to_string(),
        _ => {
            let _foo = i_config.bak_open_exec.to_string();
            trace!("detected bak_open_exec: {}", _foo);
            _foo
        }
    };
    let bak_diff_exec: String = match i_config.bak_diff_exec.as_str() {
        "default" => BAK_DIFF_DEFAULT.to_string(),
        _ => {
            let _foo = i_config.bak_diff_exec.to_string();
            trace!("detected bak_diff_exec: {}", _foo);
            _foo
        }
    };
    let config_generated_by_bak_version: String = crate::util::get_bak_version().to_string();

    return Ok(format!(
        "###
#   This file is partially managed by bak.
#   You can change settings freely, but any other changes you make, such as
#   adding your own comments, will be overwritten from a template next time bak
#   or a subcommand is run.
#
#   Settings displaying \"default\" will be replaced with their default values
#   on next run; if you've run bak and you still see that, please file a
#   bug report!
###

###
#   Where bakfiles are stored. default:
#   $XDG_DATA_HOME/bak/bakfiles 
#   or
#   ~/.local/share/bak/bakfiles
###
bakfile_location = \"{bakfile_location}\"

###
#   Location of bakfile database
#   default: $XDG_DATA_HOME/bak/bak.db
#   or
#   ~/.local/share/bak/bak.db
###
bak_database_location = \"{bak_database_location}\"

###
#  Commands
#  %bakfile and %file will be substituted as appropriate (see defaults)
###

# Command to use for `bak open`
# default: \"$PAGER %bakfile\"
bak_open_exec = \"{bak_open_exec}\"

# default: \"diff %bakfile %file\"
bak_diff_exec = \"{bak_diff_exec}\"

###
#  Flags
###

# display relative paths in `bak list` by default
bak_list_relative_paths = {bak_list_relpaths}

# colorize output for bak list (disable for perf)
bak_list_colors = {bak_list_colors}

###
#   This last bit is info bak stores about itself. Touching this will probably break bak.
###
bak_config_generated_by_version = \"{bak_version}\"
",
        bakfile_location = bakfile_location.display(),
        bak_database_location = bak_database_location.display(),
        bak_open_exec = bak_open_exec,
        bak_diff_exec = bak_diff_exec,
        bak_list_relpaths = i_config.bak_list_relative_paths,
        bak_list_colors = i_config.bak_list_colors,
        bak_version = config_generated_by_bak_version
    ));
}
