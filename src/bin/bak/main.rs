use log::LevelFilter;
use std::rc::Rc;

extern crate clap;
extern crate env_logger;
extern crate human_panic;
extern crate semver;

extern crate bakfile;

mod cmd;
mod display;
mod exec;
mod versioning;

fn main() -> anyhow::Result<()> {
    human_panic::setup_panic!();

    let cli = cmd::bak();
    let matches = cli.get_matches();
    log::trace!("comamnds successfully read"); // Will only print with RUST_LOG=trace as verbosity comes next

    let verbosity = matches.get_count("verbose");
    let quiet = matches.get_flag("quiet");
    let mut log_builder = env_logger::Builder::new();
    log_builder.filter_level(match verbosity {
        0 => match quiet {
            true => LevelFilter::Error, // no_warn I think is in my tree
            false => LevelFilter::Warn,
        },
        1 => LevelFilter::Info,
        2 => LevelFilter::Debug,
        _ => LevelFilter::Trace, // I mean, it must be high or low
    });
    log_builder.init(); // that is, you can't, you know...
    log::trace!("logger initialized");

    let config = bakfile::configuration::get_config(); // ...tune in
    log::trace!("bak config loaded");
    let bakdb = bakfile::bakdb::BakDBHandler::new(config.clone()).unwrap(); // but it's alright
    log::trace!("bakfile database handler initialized");

    exec::bak(config, Rc::new(bakdb), matches) // That is, I think it's not too bad
}
