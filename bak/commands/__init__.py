import os
import sqlite3

from datetime import datetime
from typing import List
from shutil import copy2
from subprocess import call
from typing import List
from warnings import warn

import click

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
bak_dir = os.path.join(data_dir, "bak", "bakfiles")
bak_db_loc = os.path.join(data_dir, "bak", "bak.db")

if not os.path.exists(bak_dir):
    os.makedirs(bak_dir)

db_handler = bak_db.BakDBHandler(bak_db_loc)


def expandpath(i_path):
    return os.path.abspath(os.path.expanduser(i_path))


def _assemble_bakfile(filename):
    time_now = datetime.now()
    splitname = os.path.split(expandpath(filename))
    bakfile_name = "".join([".".join(i[1:].replace("/", "-") for i in splitname[:-1]) +
                            '-' +
                            splitname[-1],  # [os.path.split(filename)[-1],
                            ".",
                            '-'.join(str(
                                time_now.timestamp()).split('.')),
                            ".bak"]).replace(" ", "-")
    # TODO #26 get bakfile directory from config
    bakfile_path = os.path.join(bak_dir, bakfile_name)

    new_bak_entry = bakfile.BakFile(os.path.basename(filename),
                                    os.path.abspath(filename),
                                    bakfile_path,
                                    time_now,
                                    time_now)
    return new_bak_entry


default_select_prompt = ("Enter a number, or: (V)iew (C)ancel", 'c')


def _get_bakfile_entry(filename, select_prompt=default_select_prompt, err=False):
    entries = db_handler.get_bakfile_entries(expandpath(filename))
    if not entries or len(entries) == 0:
        return None
    return entries[0] if len(entries) == 1 else _do_select_bakfile(entries, select_prompt, err)


def _do_select_bakfile(bakfiles: List[bakfile.BakFile],
                       select_prompt=default_select_prompt,
                       err=False):
    click.echo(
        f"Found {len(bakfiles)} bakfiles for file: {bakfiles[0].orig_abspath}", err=err)
    click.echo("Please select from the following: ", err=err)
    _range = range(len(bakfiles))
    for i in _range:
        click.echo(
            f"{i + 1}: .bakfile last modified at {bakfiles[i].date_modified}", err=err)
    choice = click.prompt(*select_prompt, err=err)
    # TODO add diff and print as choices here
    # "Enter a number, or: (V)iew (C)ancel", default='c').lower()
    if choice != "c":
        view = False
        try:
            if choice == "v":
                idx = int(click.prompt("View which .bakfile?", err=err)) - 1
                # idx = int(click.prompt("View which .bakfile? (#)")) - 1
                view = True
            else:
                idx = int(choice) - 1
            if idx not in _range:
                click.echo("Invalid selection. Aborting.", err=err)
                return None
            else:
                if view:
                    bak_print_cmd(bakfiles[idx])
                    return
                return bakfiles[idx]
        except (ValueError, TypeError) as e:
            warn(e)
            click.echo("Invalid input. Aborting.", err=err)
            return None
    else:
        click.echo("Aborting.", err=err)
        return None


def show_bak_list(filename: (None, str, os.path) = None):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    pass


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
    # false for nonspecific or generic failures

    filename = expandpath(filename)
    old_bakfile = db_handler.get_bakfile_entries(filename)
    if not old_bakfile:
        click.echo(f"No bakfile found for {filename}")
        return True
    # Disambiguate
    old_bakfile = old_bakfile[0] if len(old_bakfile) == 1 else \
        _do_select_bakfile(old_bakfile)
    if old_bakfile is None:
        return True
    elif not isinstance(old_bakfile, bakfile.BakFile):
        return False

    new_bakfile = _assemble_bakfile(filename)
    new_bakfile.date_created = old_bakfile.date_created
    copy2(new_bakfile.original_file, new_bakfile.bakfile_loc)
    db_handler.update_bakfile_entry(old_bakfile, new_bakfile)
    return True


def bak_down_cmd(filename: str,
                 keep_bakfile: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|os.path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
    """
    filename = expandpath(filename)
    bakfile_entries = db_handler.get_bakfile_entries(filename)

    # TODO still only pulling first result
    bakfile_entry = _do_select_bakfile(bakfile_entries) if len(
        bakfile_entries) > 1 else bakfile_entries[0]

    if not bakfile_entry:
        return

    os.remove(filename)
    copy2(bakfile_entry.bakfile_loc, filename)
    if not keep_bakfile:
        for entry in bakfile_entries:
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
        click.echo(f"No bakfiles found for {filename}")
    confirm = input(
        f"Confirming: Remove {len(bakfiles)} .bakfiles for {filename}? "
        f"(y/N) ").lower() == 'y' if not quietly else True
    if confirm:
        __remove_bakfiles(db_handler.get_bakfile_entries(filename))
        return True
    else:
        return False


def bak_print_cmd(bak_to_print: (str, bakfile.BakFile), using: (str, None) = None):
    if not isinstance(bak_to_print, bakfile.BakFile):
        bak_to_print = _get_bakfile_entry(bak_to_print,
                                          select_prompt=("View which .bakfile? (#)", "c"))
        if not isinstance(bak_to_print, bakfile.BakFile):
            return  # _get_bakfile_entry() handles failures, so just exit here
    if using:
        pager = using
    else:
        try:
            pager = os.environ['PAGER']
        except KeyError:
            pager = 'less'
    call([pager, bak_to_print.bakfile_loc])


def bak_getfile_cmd(bak_to_get: (str, bakfile.BakFile)):
    if not isinstance(bak_to_get, bakfile.BakFile):
        bak_to_get = _get_bakfile_entry(bak_to_get, err=True)
        if not bak_to_get:
            return  # _get_bakfile_entry() handles failures, so just exit
        click.echo(bak_to_get.bakfile_loc)


def bak_diff_cmd(filename):
    # TODO configurable diff executable
    bak_to_diff = _get_bakfile_entry(expandpath(filename))
    call(['diff', bak_to_diff.bakfile_loc, bak_to_diff.orig_abspath])
