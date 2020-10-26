import os
import sqlite3

from rich.console import Console
from rich.table import Table

# TODO: implement signatures below


def show_bak_list(db_loc: (str, os.path),
                  filename: (None, str, os.path) = None):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """
    pass


def create_bakfile(filename: (str, os.path), db_loc: (str, os.path)):
    """ Default command. Roughly equivalent to
            cp filename $XDG_DATA_DIR/.bakfiles/filename.bak
        but inserts relevant metadata into the database.

    Arguments:
        filename: (str|os.path)
        db_loc: (str|os.path)
    """
    pass


def bak_up_cmd(filename: (str, os.path), db_loc: (str, os.path)):
    """ Create a .bakfile, replacing the most recent .bakfile of
        `filename`, if one exists

    Args:
        filename (str|os.path)
        db_loc (str|os.path)
    """
    pass


def bak_down_cmd(filename: (str, os.path),
                 db_loc: (str, os.path),
                 keep_bakfile: bool = False):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|os.path)
        db_loc (str|os.path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
    """
    pass


def bak_off_cmd(filename: (None, str, os.path) = None):
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
