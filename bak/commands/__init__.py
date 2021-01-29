import os
import sqlite3
from pathlib import Path

from datetime import datetime
from typing import Optional
from shutil import copy2
from subprocess import call
from sys import stderr, stdout
from typing import List
from warnings import warn

import click
from config import Config

from rich import box
from rich.color import Color
from rich.console import Console
from rich.style import Style
from rich.table import Table

from bak.data import bakfile, bak_db

# TODO: customizable file extension

try:
    data_dir = Path(os.environ["XDG_DATA_HOME"]).expanduser().resolve()
except KeyError:
    data_dir = Path("~/.local/share").expanduser().resolve()
try:
    config_dir = Path(os.environ["XDG_CONFIG_HOME"]).expanduser().resolve()
except KeyError:
    config_dir = Path("~/.config").expanduser().resolve()

config_file = config_dir / 'bak.cfg'
cfg = Config(str(config_file))

bak_dir = cfg['bakfile_location'] or data_dir / 'bak' / 'bakfiles'
bak_db_loc = cfg['bak_database_location'] or data_dir / 'bak' / 'bak.db'

bak_list_relpaths = cfg['bak_list_relative_paths']

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
                                    time_now)
    return new_bak_entry


default_select_prompt = ("Enter a number, or: (V)iew (D)iff (C)ancel", 'C')


def _get_bakfile_entry(filename: Path,
                       select_prompt=default_select_prompt,
                       err=True):
    entries = db_handler.get_bakfile_entries(filename)
    if not entries:
        return None
    # If there's only one bakfile corresponding to filename, return that.
    # If there's more than one, disambiguate.
    return entries[0] if len(entries) == 1 else \
        _do_select_bakfile(entries, select_prompt, err)


def _do_select_bakfile(bakfiles: List[bakfile.BakFile],
                       select_prompt=default_select_prompt,
                       err=True):
    console = Console(file=stderr if err else stdout)
    console.print(
        f"Found {len(bakfiles)} bakfiles for file: {bakfiles[0].orig_abspath}")
    console.print("Please select from the following: ")
    _range = range(len(bakfiles))
    for i in _range:
        console.print(
            f"{i + 1}: .bakfile last modified at {bakfiles[i].date_modified.split('.')[0]}")

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
                elif choice == "l":
                    show_bak_list(bakfiles[0].orig_abspath)
                    choice = get_choice()
                    continue
                else:
                    idx = int(choice) - 1
                if idx not in _range:
                    console.print("Invalid selection. Aborting.")
                    return False
                elif view:
                    bak_print_cmd(bakfiles[idx])
                    choice = get_choice()
                    continue
                else:
                    return bakfiles[idx]
            except (ValueError, TypeError) as e:
                warn(e)
                console.print("Invalid input. Aborting.")
                return False
            get_choice()


def show_bak_list(filename: Optional[Path] = None,
                  relative_paths: bool = False):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    # pass
    bakfiles: List[bakfile.BakFile]
    bakfiles = db_handler.get_bakfile_entries(filename) if filename else \
        db_handler.get_all_entries()

    console = Console()
    if bakfiles is []:
        console.print(f"No .bakfiles found for "
                      f"{filename}" if
                      filename else "No .bakfiles found")
        return

    _title = f".bakfiles of {filename}" if \
        filename else ".bakfiles"

    table = Table(title=_title,
                  show_lines=True, box=box.HEAVY_EDGE)

    table.add_column("")
    table.add_column("Original File")
    table.add_column("Date Created")
    table.add_column("Last Modified")

    i = 1
    for _bakfile in bakfiles:
        table.add_row(str(i),
                      os.path.relpath(filename) if
                      relative_paths else
                      _bakfile.orig_abspath,
                      _bakfile.date_created.split('.')[0],
                      _bakfile.date_modified.split('.')[0])
        i += 1

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
                               ("Enter a number to overwrite a .bakfile, or:\n(V)iew (L)ist (C)ancel", "C")))

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
                 keep_bakfile: bool = False,
                 quiet: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|os.path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
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

    if quiet:
        confirm = 'y'
    else:
        confirm_prompt = f"Confirm: Restore {filename} and erase bakfiles?\n" \
            if not keep_bakfile else \
            f"Confirm: Restore {filename} and keep bakfiles?\n"
        confirm_prompt += "(y/n)"
        confirm = click.prompt(confirm_prompt, default='n')
    if confirm.lower()[0] != 'y':
        console.print("Cancelled.")
        return
    if not keep_bakfile:
        os.rename(bakfile_entry.bakfile_loc, bakfile_entry.orig_abspath)
        for entry in bakfile_entries:
            # bakfile_entry's bakfile has already been moved
            # trying to rm it would print a failure
            if entry != bakfile_entry:
                os.remove(entry.bakfile_loc)
            db_handler.del_bakfile_entry(entry)
    else:
        copy2(bakfile_entry.bakfile_loc, bakfile_entry.orig_abspath)


def __remove_bakfiles(bakfile_entries):
    for entry in bakfile_entries:
        os.remove(entry.bakfile_loc)
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
                                               "Enter a number to select a .bakfile, or:\n(D)iff (L)ist (C)ancel",
                                               "C"))
        #    "View which .bakfile? (#)",
        #    "c"))
        if _bak_to_print == None:
            console.print(
                f"No bakfiles found for {os.path.abspath(bak_to_print)}")
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
        if bak_to_get == None:
            console.print(f"No bakfiles found for {os.path.abspath(filename)}")
            return  # _get_bakfile_entry() handles failures, so just exit
    print(bak_to_get.bakfile_loc)


def bak_diff_cmd(filename: (bakfile.BakFile, Path), command='diff'):
    # TODO write tests for this (mildly tricky)
    console = Console()

    bak_to_diff = filename if isinstance(filename, bakfile.BakFile) else \
        _get_bakfile_entry(filename,
                           select_prompt=(
                               ("Enter a number to diff a .bakfile, or:\n(V)iew (L)ist (C)ancel", "C")))
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
