use anyhow::Result;
use comfy_table::modifiers::*;
use comfy_table::presets::UTF8_FULL;
// use comfy_table::Color::{Green, Red, Reset as DefaultColor, Yellow};
use comfy_table::{Cell, Row, Table};
use console::Term;

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
    table.set_header(vec!["#", "Original File", "Date Created", "Last Modified"]);

    let mut rows = vec![];
    for bakfile in bakfiles {
        // These should already be ordered by rowid from the database
        let mut row = Row::new();
        //TODO construct cell contents as ("{} {#}", diff_indicator, index)
        row.add_cell(Cell::new(format!("{:#}", bakfile.rowid.unwrap())));
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
    Ok(())
}
