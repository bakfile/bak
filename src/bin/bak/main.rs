extern crate clap;
extern crate env_logger;
extern crate semver;

extern crate bakfile;

mod cmd;
mod versioning;

fn main() -> anyhow::Result<()> {
    println!("Hello from bak {}, running atop bakfile {}", versioning::BAK_VERSION(), bakfile::util::LIBBAKFILE_VERSION());
    env_logger::init();
    let config = bakfile::configuration::get_config();
    Ok(())
}
