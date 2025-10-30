use std::path::PathBuf;

use clap::{value_parser, Arg, ArgAction, ArgGroup, Command};

pub(crate) fn bak<'bak>() -> Command {
    Command::new("bak")
    .version(clap::crate_version!())
        .author("ChanceNCounter <ChanceNCounter@icloud.com>")
        .about("the bakfile manager")
        .override_usage(
            "\tbak <FILE>
        or
        bak <COMMAND> [OPTIONS] [FILE]
        
        Without a command, creates a new bakfile:
            bak foo.txt
            
        For further information, see: bak <COMMAND> --help",
        )
        .propagate_version(true)
        .subcommand_required(false)
        .arg_required_else_help(true)
        .subcommand(bak_off_cmd())
        .subcommand(bak_down_cmd())
        .subcommand(bak_diff_cmd())
        .subcommand(bak_list_cmd())
        .subcommand(bak_up_cmd())
        .subcommand(bak_open_cmd())
        .subcommand(bak_where_cmd())
        .subcommand(bak_del_cmd())
        .subcommand(bak_config_cmd())
        .arg(
            Arg::new("verbose")
                .short('v')
                .long("verbose")
                .action(ArgAction::Count)
                .global(true)
                .help("use up to 3 times to increase verbosity ('-vvv')"),
        )
        .arg(
            Arg::new("quiet")
                .short('q')
                .long("quiet")
                .action(ArgAction::SetTrue)
                .help("suppress confirmation prompts (will NOT suppress verbosity or errors)")
                .global(true),
        )
        .arg(
            Arg::new("noquiet")
                .short('Q')
                .long("noquiet")
                .action(ArgAction::SetTrue)
                .help("overrides 'quiet' setting in bak config")
                .conflicts_with("quiet")
                .global(true),
        )
        .arg(
            Arg::new("file")
                .value_name("FILE")
                .required(false)
                .help("file to bak")
                .index(1),
        )
}

fn file_arg() -> Arg {
    Arg::new("file")
        .value_name("FILE")
        .help("original file")
        .value_parser(value_parser!(PathBuf))
}

fn one_bakfile_arg() -> Arg {
    Arg::new("id")
        .value_name("#")
        .short('#')
        .long("id")
        .help("bakfile ID # (as displayed by `bak list`)")
        .value_parser(value_parser!(u64))
        .allow_negative_numbers(false)
}

fn bak_up_cmd() -> Command {
    Command::new("up")
        .about("Replace a bakfile with a fresh copy of the parent file")
        .args(bak_list_args())
        .arg(file_arg())
        .arg(
            one_bakfile_arg()
                .help("index of bakfile to overwrite (optional)")
                .required(false),
        )
}

fn bak_down_cmd() -> Command {
    Command::new("down")
    .about("Restores a parent file from a bakfile (.bakfiles deleted without '--keep')")
    .alias("restore")
    .args(bak_list_args())
    .arg(file_arg())
    .arg(Arg::new("keepers")
        .short('k')
        .long("keep")
        .action(ArgAction::Append)
        .required(false)
        .value_name("#,#...")
        .help("bakfiles to keep (comma-separated)\nex: `--keep 1,3` to retain bakfiles #1 and #3 of parent file"))
}

fn bak_off_cmd() -> Command {
    Command::new("off")
        .about("Use when finished to delete .bakfiles")
        .arg(file_arg().required(true))
}

fn bak_diff_cmd() -> Command {
    Command::new("diff")
        .about("diff a file against its .bakfile")
        .args(bak_list_args())
        .arg(file_arg())
        .arg(one_bakfile_arg())
        .group(
            ArgGroup::new("bakfile_selection")
                .args(["file", ])
                .required(true),
        )
}

fn bak_list_cmd() -> Command {
    Command::new("list")
        .about("List all .bakfiles, or a particular parent file's")
        .args(bak_list_args())
        .arg(file_arg().required(false))
}

fn bak_open_cmd() -> Command {
    Command::new("open")
    .visible_alias("show")
    .about("View or edit a .bakfile in an external program\n(editing not recommended, but it's your data to mangle)")
    .args(bak_list_args())
    .arg(one_bakfile_arg()
        .required(false))
    .arg(Arg::new("program")
         .long("in")
         .required(false)
         .visible_aliases(["with", "using"])
         .help("program to open .bakfile with (bakfile will be passed as arg)\n\tdefault: $PAGER or from config"))
    .arg(file_arg().required(false))
}

fn bak_where_cmd() -> Command {
    Command::new("where")
        .alias("get-bak")
        .about("Outputs the real path of a .bakfile. Useful for piping, and not much else.")
        .args(bak_list_args())
        .arg(file_arg())
        .arg(
            one_bakfile_arg()
                .help("ID # of bakfile to overwrite (optional)")
                .required(false),
        )
}

fn bak_del_cmd() -> Command {
    Command::new("del")
        .aliases(["delete", "rm", "remove"])
        .about("Delete a single .bakfile by number (see `bak list FILENAME`)")
        .args(bak_list_args())
        .arg(file_arg())
        .arg(
            one_bakfile_arg()
                .help("index of bakfile to delete (optional)")
                .required(false),
        )
}

// TODO bak config i/o was a hassle the first time, will be a hassle the second time
fn bak_config_cmd() -> Command {
    Command::new("config").about("Print bak's current configuration to stdout")
}

fn bak_list_args() -> Vec<Arg> {
    vec![
        Arg::new("colors")
            .short('c')
            .long("color")
            .alias("colors")
            .conflicts_with("no_colors")
            .required(false)
            .action(ArgAction::SetTrue),
        Arg::new("no_colors")
            .short('C')
            .long("nocolor")
            .alias("nocolors")
            .conflicts_with("colors")
            .required(false)
            .action(ArgAction::SetTrue),
        Arg::new("compare")
            .short('d')
            .long("diff")
            .visible_alias("compare")
            .action(ArgAction::SetTrue)
            .help("Indicate changed bakfiles (may be slow if large .bakfiles are present)"),
        Arg::new("nocompare")
            .short('D')
            .long("nodiff")
            .visible_alias("nocompare")
            .action(ArgAction::SetTrue)
            .help("Overrides 'always diff' setting in bak config"),
    ]
}
