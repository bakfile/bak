extern crate clap;
extern crate semver;

extern crate bakfile;

mod cmd;
mod versioning;

fn main() -> anyhow::Result<()> {
    println!("Hello from bak {}, running atop bakfile {}", versioning::BAK_VERSION(), bakfile::util::LIBBAKFILE_VERSION());
    Ok(())
}
