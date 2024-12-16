extern crate clap;
extern crate env_logger;
extern crate human_panic;
extern crate semver;

extern crate bakfile;

mod cmd;
mod versioning;

fn main() -> anyhow::Result<()> {
    println!("Hello from bak {}, running atop bakfile {}", versioning::BAK_VERSION(), bakfile::util::LIBBAKFILE_VERSION());

    env_logger::init();
    human_panic::setup_panic!();

    let config = bakfile::configuration::get_config();
    let bakdb = bakfile::bakdb::BakDBHandler::new(config).unwrap();

    let _bakfile = bakfile::Bakfile {
        filename: "foo.txt".into(),
        bakfile_path: "/home/chance/.local/share/bakfiles/home-chance-foo-txt-09-13-15.bak".into(),
        original_path: "/home/chance/foo.txt".into(),
        initial_creation: chrono::DateTime::default(),
        last_updated: chrono::DateTime::default(),
        restored: false,
        rowid: None
    };
    bakdb.create_entry(_bakfile.clone()).expect("");
    let entries = bakdb.get_all_entries().expect("");
    println!("{:?}", entries);
    bakdb.del_entry(_bakfile.clone()).unwrap();
    let entries = bakdb.get_all_entries().expect("");
    println!("{:?}", entries);

    bakdb.create_entry(_bakfile.clone()).expect("");
    bakdb.create_entry(_bakfile.clone()).expect("");
    let entries = bakdb.get_all_entries().expect("");
    println!("{:?}", entries);

    bakdb.del_file_entries(_bakfile.original_path.clone()).expect("");
    let entries = bakdb.get_all_entries().expect("");
    println!("{:?}", entries);


    Ok(())
}
