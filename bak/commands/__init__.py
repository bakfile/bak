import os
import sqlite3

from datetime import datetime
from typing import List
from shutil import copy2
from subprocess import call
from typing import List
from warnings import warn

import click
from config import Config

from rich.console import Console
from rich.table import Table

from bak.data import bakfile, bak_db

# TODO: customizable file extension

try:
    data_dir = os.environ["XDG_DATA_HOME"]
except KeyError:
    data_dir = os.path.expanduser("~/.local/share")
try:
    config_dir = os.environ["XDG_CONFIG_HOME"]
except KeyError:
    config_dir = os.path.expanduser("~/.config")

config_file = os.path.join(config_dir, 'bak.cfg')
cfg = Config(config_file)

bak_dir = cfg['bakfile_location'] or os.path.join(data_dir,
                                                  "bak", "bakfiles")
bak_db_loc = cfg['bak_database_location'] or \
    os.path.join(data_dir, "bak", "bak.db")

bak_list_relpaths = cfg['bak_list_relative_paths']

if not os.path.exists(bak_dir):
    os.makedirs(bak_dir)

db_handler = bak_db.BakDBHandler(bak_db_loc)


def expandpath(i_path):
    return os.path.abspath(os.path.expanduser(i_path))


def _assemble_bakfile(filename):
    time_now = datetime.now()
    splitname = os.path.split(expandpath(filename))
    bakfile_name = "".join([".".join(i[1:].replace("/", "-")
                                     for i in splitname[:-1]) +
                            '-' +
                            splitname[-1],
                            ".",
                            '-'.join(str(
                                time_now.timestamp()).split('.')),
                            ".bak"]).replace(" ", "-")
    bakfile_path = os.path.join(bak_dir, bakfile_name)

    new_bak_entry = bakfile.BakFile(os.path.basename(filename),
                                    os.path.abspath(filename),
                                    bakfile_path,
                                    time_now,
                                    time_now)
    return new_bak_entry


default_select_prompt = ("Enter a number, or: (V)iew (D)iff (C)ancel", 'c')


def _get_bakfile_entry(filename,
                       select_prompt=default_select_prompt,
                       err=False):
    entries = db_handler.get_bakfile_entries(expandpath(filename))
    if not entries or len(entries) == 0:
        return None
    # If there's only one bakfile corresponding to filename, return that.
    # If there's more than one, disambiguate.
    return entries[0] if len(entries) == 1 else \
        _do_select_bakfile(entries, select_prompt, err)


def _do_select_bakfile(bakfiles: List[bakfile.BakFile],
                       select_prompt=default_select_prompt,
                       err=False):
    click.echo(
        f"Found {len(bakfiles)} bakfiles for file: {bakfiles[0].orig_abspath}",
        err=err)
    click.echo("Please select from the following: ", err=err)
    _range = range(len(bakfiles))
    for i in _range:
        click.echo(
            f"{i + 1}: .bakfile last modified at {bakfiles[i].date_modified}",
            err=err)

    def get_choice():
        return click.prompt(*select_prompt, err=err).lower()
    choice = get_choice()

    while True:
        if choice == "c":
            click.echo("Cancelled.", err=err)
            return None
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
                if idx not in _range:
                    click.echo("Invalid selection. Aborting.", err=err)
                    return None
                elif view:
                    bak_print_cmd(bakfiles[idx])
                    choice = get_choice()
                    continue
                else:
                    return bakfiles[idx]
            except (ValueError, TypeError) as e:
                warn(e)
                click.echo("Invalid input. Aborting.", err=err)
                return None
            get_choice()


def show_bak_list(filename: (None, str, os.path) = None,
                  relative_paths: bool = False):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    # pass
    bakfiles: list[bakfile.BakFile]
    bakfiles = db_handler.get_bakfile_entries(filename) if filename else \
                db_handler.get_all_entries()

    _title = f".bakfiles of {os.path.abspath(os.path.expanduser(filename))}" if \
                filename else ".bakfiles"

    table = Table(title=_title)
    
    table.add_column("Original File")
    table.add_column("Date Created")
    table.add_column("Last Modified")

    for _bakfile in bakfiles:
        table.add_row((os.path.relpath(_bakfile.original_file)) if \
                      relative_paths else \
                      _bakfile.orig_abspath,
                      _bakfile.date_created,
                      _bakfile.date_modified)
        
    console = Console()
    console.print(table)

def create_bakfile(filename: str):
    """ Default command. Roughly equivalent to
            cp filename $XDG_DATA_DIR/.bakfiles/filename.bak
        but inserts relevant metadata into the database.

    Arguments:
        filename: (str|os.path)
    """
    filename = expandpath(filename)
    if not os.path.exists(filename):
        # TODO descriptive failure
        return False
    new_bakfile = _assemble_bakfile(filename)
    copy2(new_bakfile.orig_abspath, new_bakfile.bakfile_loc)
    db_handler.create_bakfile_entry(new_bakfile)


def bak_up_cmd(filename: str):
    """ Create a .bakfile, replacing the most recent .bakfile of
        `filename`, if one exists

    Args:
        filename (str|os.path)
    """
    # Return Truthy things for failures that echo their own output,
    # false for nonspecific or generic failures.
    # Put differently, False is for complete failures. If this function
    # handles a failure gracefully, it should return True.

    filename = expandpath(filename)
    old_bakfile = db_handler.get_bakfile_entries(filename)
    if not old_bakfile:
        click.echo(f"No bakfile found for {filename}")
        return True
    # Disambiguate
    old_bakfile = old_bakfile[0] if len(old_bakfile) == 1 else \
        _do_select_bakfile(old_bakfile)
    if old_bakfile is None:
        click.echo("Cancelled.")
        return True
    elif not isinstance(old_bakfile, bakfile.BakFile):
        return False

    old_bakfile.date_modified = datetime.now()
    copy2(old_bakfile.original_file, old_bakfile.bakfile_loc)
    db_handler.update_bakfile_entry(old_bakfile)
    return True


def bak_down_cmd(filename: str,
                 keep_bakfile: bool = False,
                 quiet: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|os.path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
    """
    filename = expandpath(filename)
    bakfile_entries = db_handler.get_bakfile_entries(filename)
    if not bakfile_entries:
        click.echo(f"No bakfiles found for {filename}")
        return

    bakfile_entry = _do_select_bakfile(bakfile_entries) if len(
        bakfile_entries) > 1 else bakfile_entries[0]

    if not bakfile_entry:
        click.echo(f"No bakfiles found for {filename}")
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
        click.echo("Cancelled.")
        return
    # os.remove(filename)
    # copy2(bakfile_entry.bakfile_loc, filename)
    if not keep_bakfile:
        os.rename(bakfile_entry.bakfile_loc, filename)
        for entry in bakfile_entries:
            # bakfile_entry's bakfile has already been moved
            # trying to rm it would print a failure
            if entry != bakfile_entry:
                os.remove(entry.bakfile_loc)
            db_handler.del_bakfile_entry(entry)


def __remove_bakfiles(bakfile_entries):
    for entry in bakfile_entries:
        os.remove(entry.bakfile_loc)
        db_handler.del_bakfile_entry(entry)


def bak_off_cmd(filename: (None, str, os.path),
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
    filename = expandpath(filename)
    bakfiles = db_handler.get_bakfile_entries(filename)
    if not bakfiles:
        click.echo(f"No bakfiles found for {os.path.abspath(filename)}")
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
    if not isinstance(bak_to_print, bakfile.BakFile):
        _bak_to_print = _get_bakfile_entry(bak_to_print,
                                           select_prompt=(
                                               default_select_prompt))
                                            #    "View which .bakfile? (#)",
                                            #    "c"))
        if not _bak_to_print:
            click.echo(
                f"No bakfiles found for {os.path.abspath(bak_to_print)}")
        else:
            bak_to_print = _bak_to_print
        if not isinstance(bak_to_print, bakfile.BakFile):
            return  # _get_bakfile_entry() handles failures, so just exit here
    pager = using if using else \
        (cfg['bak_show_exec'] or os.environ['PAGER']) or 'less'
    pager = pager.strip('"').strip("'").split(" ")
    call(pager + [bak_to_print.bakfile_loc])


def bak_getfile_cmd(bak_to_get: (str, bakfile.BakFile)):
    if not isinstance(bak_to_get, bakfile.BakFile):
        filename = bak_to_get
        bak_to_get = _get_bakfile_entry(bak_to_get, err=True)
        if not bak_to_get:
            click.echo(f"No bakfiles found for {os.path.abspath(filename)}")
            return  # _get_bakfile_entry() handles failures, so just exit
    click.echo(bak_to_get.bakfile_loc)


def bak_diff_cmd(filename: str, command='diff'):
    # TODO write tests for this (mildly tricky)
    bak_to_diff = filename if isinstance(filename, bakfile.BakFile) else \
        _get_bakfile_entry(expandpath(filename))
    if not command:
        command = cfg['bak_diff_exec'] or 'diff'
    if not bak_to_diff:
        click.echo(f"No bakfiles found for {os.path.abspath(filename)}")
        return
    command = command.strip('"').strip("'").split(" ")
    call(command +
         [bak_to_diff.bakfile_loc, bak_to_diff.orig_abspath])
