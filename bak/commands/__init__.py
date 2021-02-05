import os
import sqlite3
from datetime import datetime
from filecmp import cmp as compare_files
from pathlib import Path
from shutil import copy2
from subprocess import call
from sys import stderr, stdout
from typing import List, Optional
from warnings import warn

import click
from config import Config
from rich import box
from rich.color import Color
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from bak.configuration.cfg import data_dir
from bak.configuration.cfg import bak_cfg as cfg
from bak.data import bak_db, bakfile

bak_dir = cfg['bakfile_location'] or data_dir / 'bak' / 'bakfiles'
bak_db_loc = cfg['bak_database_location'] or data_dir / 'bak' / 'bak.db'

bak_list_relpaths = cfg['bak_list_relative_paths']
bak_list_colors = cfg['bak_list_colors']

if not bak_dir.exists():
    bak_dir.mkdir(parents=True)

db_handler = bak_db.BakDBHandler(bak_db_loc)


def _assemble_bakfile(filename: Path):
    time_now = datetime.now()
    bakfile_name = "".join(
        ["-".join(i for i in filename.parent.parts[1:])
         + '-' + filename.name, ".", '-'.join(str(time_now.timestamp()).split('.')), ".bak"]).replace(" ", "-")
    bakfile_path = bak_dir / bakfile_name

    new_bak_entry = bakfile.BakFile(filename.name,
                                    filename,
                                    bakfile_path,
                                    time_now,
                                    time_now,
                                    restored=False)
    return new_bak_entry


default_select_prompt = ("Enter a number, or: (V)iew (D)iff (C)ancel", 'C')


def _get_bakfile_entry(filename: Path,
                       select_prompt=default_select_prompt,
                       err=True,
                       diff=False):
    entries = db_handler.get_bakfile_entries(filename)
    if not entries:
        return None
    # If there's only one bakfile corresponding to filename, return that.
    # If there's more than one, disambiguate.
    return entries[0] if len(entries) == 1 else \
        _do_select_bakfile(entries, select_prompt, err, diff)

# TODO: this is a quick kludge to integrate 'bak list'
# A proper rewrite is in order
def _do_select_bakfile(bakfiles: List[bakfile.BakFile],
                       select_prompt=default_select_prompt,
                       err=True,
                       diff=True):
    console = Console(file=stderr if err else stdout)

    show_bak_list(bakfiles[0].orig_abspath, err=err, colors=bak_list_colors, compare=diff)

    def get_choice():
        return click.prompt(*select_prompt, err=err).lower()

    choice = get_choice()

    while True:
        if choice == "c":
            console.print("Cancelled.")
            return False
        else:
            view = False
            try:
                if choice == "v":
                    idx = int(click.prompt(
                        "View which .bakfile?", err=err)) - 1
                    view = True
                elif choice == "d":
                    idx = int(click.prompt(
                        "Diff which .bakfile?", err=err)) - 1
                    bak_diff_cmd(bakfiles[idx])
                    choice = get_choice()
                    continue
                else:
                    idx = int(choice) - 1
                if idx not in range(len(bakfiles)):
                    console.print("Invalid selection. Aborting.")
                    return False
                elif view:
                    bak_print_cmd(bakfiles[idx])
                    choice = get_choice()
                    continue
                else:
                    return bakfiles[idx]
            except (ValueError, TypeError) as error:
                warn(error)
                console.print("Invalid input. Aborting.")
                return False
            get_choice()


def _identify_baks(entries):
    # entries = db_handler.get_bakfile_entries(filename)
    oldest_version: bakfile.BakFile
    oldest_date = datetime.now()
    newest_version: bakfile.BakFile
    newest_date = datetime(1970, 1, 1, 1, 1)
    for entry in entries:
        timestamp = datetime.fromisoformat(entry.date_modified)
        if timestamp < oldest_date:
            oldest_version = entry
            oldest_date = timestamp
        if timestamp > newest_date:
            newest_version = entry
            newest_date = timestamp
    return (oldest_version, newest_version)


def show_bak_list(filename: Optional[Path] = None,
                  relative_paths: bool = False,
                  err=False,
                  colors=False,
                  compare=False):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    bold_style = Style(bold=True, italic=True)
    purple_style = Style(bold=True, italic=True, color="purple")
    blue_style = Style(color="blue")
    none_style = Style()

    def _rotate_style(bold: bool):
        if not colors:
            return bold_style if bold else none_style
        return purple_style if bold else blue_style


    console = Console(file=stderr if err else stdout)

# Get bakfiles
    bakfiles: List[bakfile.BakFile]
    bakfiles = db_handler.get_bakfile_entries(filename) if filename else \
        db_handler.get_all_entries()

    console = Console(file=stderr if err else stdout)
    if not bakfiles:
        console.print(f"No .bakfiles found for "
                      f"{filename}" if
                      filename else "No .bakfiles found")
        return

# Set up table

    if colors:
        caption = Text()
        caption.append('-- ', style="red")
        caption.append('oldest .bak   ', style='dim italic')
        caption.append('++ ', style="green")
        caption.append('newest .bak   ', style='dim italic')
        caption.append('** ', style="yellow")
        caption.append('restored   ', style='dim italic')
        if compare:
            caption.append('$ ', style="green")
            caption.append('current version of file\n', style='dim italic')
        else:
            caption.append('\n')
        caption.append('   (files may have been edited since restoration)', style='dim italic')
    else:
        caption = '-- oldest .bak   ++ newest .bak   ** restored' + ('  $ current version of file' if compare else '') +\
                  '\n   (files may have been edited since restoration)'

    _title = f".bakfiles of {filename}" if \
        filename else ".bakfiles"

    table = Table(title=_title,
                  show_lines=True,
                  box=box.HEAVY_EDGE,
                  caption=caption)
    table.add_column("", justify='right', style=None)
    table.add_column("Original File")
    table.add_column("Date Created")
    table.add_column("Last Modified")

    # Distinguish .bakfiles from different original files
    filenames = set(_bakfile.orig_abspath for _bakfile in bakfiles)
    _identified_baks = dict()
    for _filename in filenames:
        _identified_baks[_filename] = _identify_baks(
            [_bakfile for _bakfile in bakfiles if _bakfile.orig_abspath == _filename])
    i = 1
    current_filename = bakfiles[0].orig_abspath
    current_style = blue_style if colors else none_style
    bold = False # First line will be opposite, toggled between population and rendering of table row

    # Begin individual row prep
    for _bakfile in bakfiles:
        # Alternate styles on every other filename
        if current_filename != _bakfile.orig_abspath:
            current_filename = _bakfile.orig_abspath
            bold = not bold
            current_style = _rotate_style(bold)

        # Apply identifying markers to indices
        if compare:
            current_version_marker = \
            Text("$ ") if compare_files(_bakfile.bakfile_loc, current_filename) else None
        else:
            current_version_marker = None

        if current_version_marker:
            if colors:
                current_version_marker.stylize("green")

        restored_marker = \
            Text('** ') if _bakfile.restored else None
        if colors:
            if restored_marker:
                restored_marker.stylize("yellow")


        _id_baks = _identified_baks[_bakfile.orig_abspath]
        marker = ('-- ' if _bakfile is _id_baks[0] \
                else ('++ ' if _bakfile is _id_baks[1] \
                    else ""))
        if marker:
            marker=Text(marker)
            if colors:
                marker.stylize("green" if '+' in marker else "red" if '-' in marker else None)
            index = marker.append(str(i))
        else:
            index = Text(str(i))
        index.stylize("bold")

        if restored_marker:
            index = restored_marker.append_text(index)
        if current_version_marker:
            if not (marker or restored_marker):
                current_version_marker += "   "
            index = current_version_marker.append_text(index)

        # Prepare and stylize this row's content
        o_path = Text(os.path.relpath(current_filename) if
                    relative_paths else
                    current_filename)
        o_created = Text(_bakfile.date_created.split('.')[0])
        o_modified = Text(_bakfile.date_modified.split('.')[0])

        if filename and colors:
            o_path.stylize('green')
        else:
            o_path.stylize(current_style)
        o_created.stylize(current_style)
        o_modified.stylize(current_style)
        # End row prep

        table.add_row(index,
                      o_path,
                      o_created,
                      o_modified)
        i += 1
    # End table prep
    console.print(table)


def create_bakfile(filename: Path):
    """ Default command. Roughly equivalent to
            cp filename $XDG_DATA_DIR/.bakfiles/filename.bak
        but inserts relevant metadata into the database.

    Arguments:
        filename: (str|os.path)
    """
    if not filename.exists():
        # TODO descriptive failure
        return False
    current_entries = db_handler.get_bakfile_entries(filename.expanduser().resolve())
    if current_entries:
        if compare_files(_identify_baks(current_entries)[1].bakfile_loc, filename.expanduser().resolve()):
            if not click.confirm("No changes to file since last bak. Would you like to create a duplicate .bakfile?"):
                click.echo("Cancelled.")
                return
    new_bakfile = _assemble_bakfile(filename)
    copy2(new_bakfile.orig_abspath, new_bakfile.bakfile_loc)
    db_handler.create_bakfile_entry(new_bakfile)


def bak_up_cmd(filename: Path):
    """ Overwrite an existing .bakfile with the file's current contents

    Args:
        filename (str|os.path)
    """
    # Return Truthy things for failures that echo their own output,
    # false for nonspecific or generic failures.
    # Put differently, False is for complete failures. If this function
    # handles a failure gracefully, it should return True.

    console = Console()

    old_bakfile = db_handler.get_bakfile_entries(filename)
    if old_bakfile is None:
        console.print(f"No bakfile found for {filename}")
        console.print(f"Creating {filename}.bak")
        return create_bakfile(filename)

    # Disambiguate
    old_bakfile = old_bakfile[0] if len(old_bakfile) == 1 else \
        _do_select_bakfile(old_bakfile,
                           select_prompt=(
                               ("Enter a number to overwrite a .bakfile, or:\n(V)iew (C)ancel", "C")))

    if old_bakfile is None:
        console.print("Cancelled.")
        return True
    elif not isinstance(old_bakfile, bakfile.BakFile):
        return False

    old_bakfile.date_modified = datetime.now()
    copy2(old_bakfile.original_file, old_bakfile.bakfile_loc)
    db_handler.update_bakfile_entry(old_bakfile)
    return True


def bak_down_cmd(filename: Path,
                 destination: Optional[Path],
                 keep_bakfile: bool = False,
                 quiet: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|Path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
        quiet (bool): If True, does not ask user to confirm
        destination (None|Path): destination path to restore to
    """
    console = Console()
    bakfile_entries = db_handler.get_bakfile_entries(filename)
    if not bakfile_entries:
        console.print(f"No bakfiles found for {filename}")
        return

    bakfile_entry = _do_select_bakfile(bakfile_entries) if len(
        bakfile_entries) > 1 else bakfile_entries[0]

    if bakfile_entry is None:
        console.print(f"No bakfiles found for {filename}")
        return
    elif not bakfile_entry:
        return
    if not destination:
        destination = Path(bakfile_entry.orig_abspath).expanduser()

    if quiet:
        confirm = 'y'
    else:
        if destination != bakfile_entry.orig_abspath:
            if destination.exists():
                confirm = click.confirm(f"Overwrite {destination}?")
        
        confirm_prompt = f"Confirm: Restore {filename} to {destination} and erase bakfiles?" \
            if not keep_bakfile else \
            f"Confirm: Restore {filename} to {destination} and keep bakfiles?"
        confirm = click.confirm(confirm_prompt, default=False)
    if not confirm:
        console.print("Cancelled.")
        return
    copy2(bakfile_entry.bakfile_loc, destination)
    if not keep_bakfile:
        for entry in bakfile_entries:
            Path(entry.bakfile_loc).unlink(missing_ok=True)
            db_handler.del_bakfile_entry(entry)
    else:
        copy2(bakfile_entry.bakfile_loc, bakfile_entry.orig_abspath)
        for entry in bakfile_entries:
            if entry.restored:
                if entry.bakfile_loc != bakfile_entry.bakfile_loc:
                    db_handler.set_restored_flag(entry, False)
        db_handler.set_restored_flag(bakfile_entry, True)


def __remove_bakfiles(bakfile_entries):
    for entry in bakfile_entries:
        Path(entry.bakfile_loc).unlink()
        db_handler.del_bakfile_entry(entry)


def bak_off_cmd(filename: Optional[Path],
                quietly=False):
    """ Used when finished. Deletes `filename.bak`. Prompts if ambiguous:
            3 .bakfiles detected:
                1. filename.bak   |   <metadata>
                2. filename.bak.1 |   <metadata>
                3. filename.bak.2 |   <metadata>
            Delete:
                (A)ll, (1,2,3), (N)one, (C)ancel
        NOTE: that output isn't implemented yet, but it does offer decent
              options when disambiguation is required
    Args:
        filename ([type], optional): [description]. Defaults to None.
    """
    console = Console()
    bakfiles = db_handler.get_bakfile_entries(filename)
    if not bakfiles:
        console.print(f"No bakfiles found for {filename}")
        return False
    confirm = input(
        f"Confirming: Remove {len(bakfiles)} .bakfiles for {filename}? "
        f"(y/N) ").lower() == 'y' if not quietly else True
    if confirm:
        __remove_bakfiles(db_handler.get_bakfile_entries(filename))
        return True
    else:
        return False


def bak_print_cmd(bak_to_print: (str, bakfile.BakFile),
                  using: (str, None) = None):
    # if this thing is given a string, it needs to go find
    # a corresponding bakfile
    console = Console()

    if not isinstance(bak_to_print, bakfile.BakFile):
        _bak_to_print = _get_bakfile_entry(bak_to_print,
                                           select_prompt=(
                                               "Enter a number to select a .bakfile, or:\n(D)iff (C)ancel",
                                               "C"))
        if _bak_to_print is None:
            console.print(
                f"No bakfiles found for {Path(bak_to_print).resolve()}")
        else:
            bak_to_print = _bak_to_print
        if not isinstance(bak_to_print, bakfile.BakFile):
            return  # _get_bakfile_entry() handles failures, so just exit here
    pager = using if using else \
        (cfg['bak_open_exec'] or os.environ['PAGER']) or 'less'
    pager = pager.strip('"').strip("'").split(" ")
    call(pager + [bak_to_print.bakfile_loc])


def bak_getfile_cmd(bak_to_get: (str, bakfile.BakFile)):
    console = Console(file=stderr)

    if not isinstance(bak_to_get, bakfile.BakFile):
        filename = bak_to_get
        bak_to_get = _get_bakfile_entry(bak_to_get, err=True)
        if bak_to_get is None:
            console.print(f"No bakfiles found for {Path(filename).resolve()}")
            return  # _get_bakfile_entry() handles failures, so just exit
    print(bak_to_get.bakfile_loc)


def bak_diff_cmd(filename: (bakfile.BakFile, Path), command='diff'):
    # TODO write tests for this (mildly tricky)
    console = Console()

    bak_to_diff = filename if isinstance(filename, bakfile.BakFile) else \
        _get_bakfile_entry(filename,
                           diff=True,
                           select_prompt=(
                               ("Enter a number to diff a .bakfile, or:\n(V)iew (C)ancel", "C")))
    if not command:
        command = cfg['bak_diff_exec'] or 'diff'
    if bak_to_diff is None:
        console.print(f"No bakfiles found for {filename}")
        return
    if not bak_to_diff:
        return
    command = command.strip('"').strip("'").split(" ")
    call(command +
         [bak_to_diff.bakfile_loc, bak_to_diff.orig_abspath])
