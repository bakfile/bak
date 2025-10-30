extern crate directories;
extern crate shellexpand;

use anyhow::Result;

use crate::config;

pub(crate) fn get_config_template_string(i_config: &crate::config::Config) -> Result<String> {
    return Ok(format!(
        "###
#   This file is partially managed by bak.
###

###
#   Where bakfiles are stored. default:
#   \"{default_bakfile_location}\"
###
bakfile_location = \"{bakfile_location}\"

###
#   Location of bakfile database
#   \"{default_bakdb_location}\"
###
bak_database_location = \"{bak_database_location}\"

###
#  Commands
###

# Command to use for `bak open`
# %bakfile will be substituted with the bakfile to open
# default: \"$PAGER %bakfile\"
bak_open_exec = \"{bak_open_exec}\"

# %old and %new will be substituted with the files to diff
# default: \"diff %old %new\"
bak_diff_exec = \"{bak_diff_exec}\"

# default: \"cp %old %new\"
# if this is commented out, bak will use a built-in copy function, which may
# be more efficient for some operations, but which, because it is not managed by
# your operating system, may be dangerous
bak_cp_exec = \"{bak_cp_exec}\"

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
bak_config_generated_by_library_version = \"{bakfile_version}\"
",
        bakfile_location = i_config.bakfile_location,
        bak_database_location = i_config.bak_database_location,
        bak_cp_exec = i_config.bak_cp_exec.clone().or(Some(config::DEFAULT_CP_CMD.to_string())).expect("Unable to retrieve default cp command"),
        bak_open_exec = i_config.bak_open_exec,
        bak_diff_exec = i_config.bak_diff_exec,
        bak_list_relpaths = i_config.bak_list_relative_paths,
        bak_list_colors = i_config.bak_list_colors,
        bakfile_version = i_config.bakfile_library_version,
        default_bakfile_location = config::get_default_bakfile_loc().unwrap().to_str().unwrap(),
        default_bakdb_location = config::get_default_bak_db_loc().unwrap().to_str().unwrap()
    ));
}
