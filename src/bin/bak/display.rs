use anyhow::Result;
use bakfile::util::sha256_files;
use comfy_table::modifiers::*;
use comfy_table::presets::UTF8_FULL;
use comfy_table::{Cell, Row, Table};
use console::{Style, Term};

use log::trace;

use bakfile::{Bakfile, configuration::Config};

pub(crate) fn display_bak_list(
    bakfiles: &Vec<Bakfile>,
    configuration: &Config,
    diff: bool,
    colors: bool,
    stderr: bool,
) -> Result<()> {
    trace!(
        "Displaying bak list. Incoming params:\n
            bakfiles: {:?}\n
            config object: {:p}\n
            diff: {}\n
            colors: {}",
        bakfiles.len(),
        configuration,
        diff,
        colors
    );
    let term = match stderr {
        true => Term::stderr(),
        false => Term::stdout(),
    };
    let mut table = Table::new();
    table
        .load_preset(UTF8_FULL)
        .apply_modifier(UTF8_ROUND_CORNERS)
        .apply_modifier(UTF8_SOLID_INNER_BORDERS);
    let header: Vec<&str> = vec!["#", "Original File", ".bakfile Created", ".bakfile Updated"];
    table.set_header(header);

    let mut rows = vec![];
    for bakfile in bakfiles {
        // These should already be ordered by rowid from the database
        let mut row = Row::new();
        //TODO construct cell contents as ("{} {#}", diff_indicator, index)
        let rowid = bakfile.rowid.unwrap();
        let fstring = match diff {
            false => { format!("{:#}", rowid) },
            true => {
                if sha256_files(bakfile.original_path.clone(), bakfile.bakfile_path.clone())? {
                    format!("{:#}*", rowid)
                } else {
                    format!("{:#}", rowid)
                }
            }
        };
        row.add_cell(Cell::new(fstring));
        row.add_cell(Cell::new(format!("{}", bakfile.original_path.display())));
        row.add_cell(Cell::new(
            bakfile
                .initial_creation
                .naive_local()
                .format("%Y-%m-%d %H:%M:%S"),
        ));
        row.add_cell(Cell::new(
            bakfile
                .last_updated
                .naive_local()
                .format("%Y-%m-%d %H:%M:%S"),
        ));
        rows.push(row);
    }
    table.add_rows(rows);
    term.write_line(&format!("{}", table))?;
    if diff { term.write_line("* - original file has changed since last bak operation")?; }
    Ok(())
}