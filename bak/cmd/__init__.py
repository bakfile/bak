import os
import sqlite3

from datetime import datetime
from shutil import copy2

from data import bakfile, bak_db

# TODO: #2 implement signatures below
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


def _assemble_bakfile(filename):
    time_now = datetime.now()
    bakfile_name = "".join(["/",
                            filename,
                            ".",
                            '-'.join(str(
                                time_now.timestamp()).split('.')),
                            ".bak"])
    # TODO #16 get bakfile directory from config
    bakfile_path = bak_dir.rstrip("/") + bakfile_name

    new_bak_entry = bakfile.BakFile(filename,
                                    os.path.abspath(filename),
                                    bakfile_path,
                                    time_now,
                                    time_now)
    return new_bak_entry


def _do_select_bakfile(bakfiles: List[bakfile.BakFile]):
    click.echo(
        f"Found {len(bakfiles)} bakfiles for file: {bakfiles[0].orig_abspath}")
    click.echo("Please select from the following: ")
    _range = range(len(bakfiles))
    for i in _range:
        click.echo(
            f"{i + 1}: .bakfile last modified at {bakfiles[i].date_modified}")
    choice = click.prompt(
        # TODO add diff and print as choices here
        "Enter a number, or: (C)ancel", default='c')
    if choice.lower() != "c":
        try:
            choice = int(choice) - 1
            if choice not in _range:
                click.echo("Invalid selection. Aborting.")
                return None
            else:
                return bakfiles[choice]
        except (ValueError, TypeError):
            click.echo("Invalid selection. Aborting.")
            return None
    else:
        click.echo("Aborting.")
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
    if not os.path.exists(filename):
        # TODO descriptive failure
        return False
    new_bakfile = _assemble_bakfile(filename)
    copy2(new_bakfile.original_file, new_bakfile.bakfile_loc)
    db_handler.create_bakfile_entry(new_bakfile)


def bak_up_cmd(filename: str):
    """ Create a .bakfile, replacing the most recent .bakfile of
        `filename`, if one exists

    Args:
        filename (str|os.path)
    """
    # Return Truthy things for failures that echo their own output,
    # false for nonspecific or generic failures

    filename = os.path.expanduser(filename)
    old_bakfile = db_handler.get_bakfile_entries(filename)
    if not old_bakfile:
        click.echo(f"No bakfile found for {filename}")
        return True
    # Disambiguate
    old_bakfile = old_bakfile[0] if len(old_bakfile) == 1 else \
        _do_select_bakfile(old_bakfile)
    if old_bakfile is None:
        return True
    elif not isinstance(bakfile.BakFile, old_bakfile):
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
    bakfile_entry = db_handler.get_bakfile_entry(filename)
    filename = os.path.expanduser(filename)
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

    Args:
        filename ([type], optional): [description]. Defaults to None.
    """
    confirm = input(
        f"Confirming: Remove .bakfile for {os.path.expanduser(filename)}? "
        f"(y/N) ") if not quietly else True
    if confirm.lower() == 'y':
        bakfile_entry = db_handler.get_bakfile_entry(filename)
        os.remove(bakfile_entry.bakfile_loc)
        db_handler.del_bakfile_entry(bakfile_entry.original_file)
        return True
    else:
        return False
