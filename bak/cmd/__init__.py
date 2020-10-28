import os
import sqlite3

from datetime import datetime
from shutil import copy2

from data import bakfile, bak_db

# TODO: #2 implement signatures below
# TODO: customizable file extension

bak_dir = os.path.expanduser(os.environ["BAK_DIR"])


def _assemble_bakfile(filename):
    bakfile_name = "".join(["/",
                            filename,
                            ".",
                            '-'.join(str(
                                datetime.now().timestamp()).split('.')),
                            ".bak"])
    # TODO get bakfile directory from config
    bakfile_path = bak_dir.rstrip("/") + bakfile_name

    new_bak_entry = bakfile.BakFile(filename,
                                    os.path.abspath(filename),
                                    bakfile_path,
                                    datetime.now(),
                                    datetime.now())
    return new_bak_entry


def show_bak_list(db_loc: (str, os.path),
                  filename: (None, str, os.path) = None):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    pass


def create_bakfile(filename: (str, os.path), db_handler: bak_db.BakDBHandler = None):
    """ Default command. Roughly equivalent to
            cp filename $XDG_DATA_DIR/.bakfiles/filename.bak
        but inserts relevant metadata into the database.

    Arguments:
        filename: (str|os.path)
        db_loc: (str|os.path)
    """
    if not db_handler:
        db = os.path.expanduser(os.environ["BAK_DB_LOC"])
        db_handler = bak_db.BakDBHandler(db)
    if not os.path.exists(filename):
        # TODO descriptive failure
        return False
    new_bakfile = _assemble_bakfile(filename)
    copy2(new_bakfile.original_file, new_bakfile.bakfile_loc)
    db_handler.create_bakfile_entry(new_bakfile)


def bak_up_cmd(filename: (str, os.path), db_handler: (str, os.path)):
    """ Create a .bakfile, replacing the most recent .bakfile of
        `filename`, if one exists

    Args:
        filename (str|os.path)
        db_loc (str|os.path)
    """
    new_bakfile = _assemble_bakfile(filename)
    copy2(new_bakfile.original_file, new_bakfile.bakfile_loc)
    db_handler.update_bakfile_entry(new_bakfile)


def bak_down_cmd(filename: (str, os.path),
                 db_handler: bak_db.BakDBHandler,
                 keep_bakfile: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|os.path)
        db_loc (str|os.path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
    """
    bakfile_entry = db_handler.get_bakfile_entry(filename)
    filename = os.path.expanduser(filename)

    os.remove(filename)
    copy2(bakfile_entry.bakfile_loc, filename)
    if not keep_bakfile:
        os.remove(bakfile_entry.bakfile_loc)
    db_handler.del_bakfile_entry(filename)


def bak_off_cmd(filename: (None, str, os.path),
                db_handler: bak_db.BakDBHandler,
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
        f"Confirming: Remove .bakfile for {os.path.expanduser(filename)}?"
        f"(y/N)") if not quietly else True
    if confirm:
        bakfile_entry = db_handler.get_bakfile_entry(filename)
        os.remove(bakfile_entry.bakfile_loc)
        db_handler.del_bakfile_entry(bakfile_entry.original_file)
        return True
    else:
        return False
