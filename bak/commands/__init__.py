# region lots of imports
import os
import sqlite3
from datetime import datetime
from filecmp import cmp as compare_files
from pathlib import Path
from shutil import copy2
from subprocess import call
from sys import stderr, stdout
from typing import List, Optional, Union
from warnings import warn

import click
from config import Config, KeyNotFoundError
from rich import box
from rich.color import Color
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from bak.configuration import bak_cfg as cfg
from bak.data import bak_db, bakfile
# endregion


# region constants etc.
bak_dir = cfg['bakfile_location'] or cfg.data_dir / 'bak' / 'bakfiles'
bak_db_loc = cfg['bak_database_location'] or cfg.data_dir / 'bak' / 'bak.db'

BAK_LIST_RELPATHS = cfg['bak_list_relative_paths']
BAK_LIST_COLORS = cfg['bak_list_colors']
FASTMODE = cfg['fast_mode']
if not bak_dir.exists():
    bak_dir.mkdir(parents=True)

db_handler = bak_db.BakDBHandler(bak_db_loc)
# endregion


# region helpers
############
############
############
def __assemble_bakfile(filename: Path):
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


def __get_bakfile_entry(filename: Path,
                        select_prompt=default_select_prompt,
                        err=True,
                        diff=False,
                        bakfile_number=0,
                        console: Console=None):
    entries = db_handler.get_bakfile_entries(filename)
    if not entries:
        return None
    if bakfile_number and bakfile_number > 0:
        try:
            return entries[bakfile_number - 1]
        except IndexError:
            console.print(f"No such bakfile: {filename} #{bakfile_number}")
            return None
    # If there's only one bakfile corresponding to filename, return that.
    # If there's more than one, disambiguate.
    return entries[0] if len(entries) == 1 else \
        __do_select_bakfile(entries, select_prompt, err, diff)

# TODO: this is a quick kludge to integrate 'bak list'
# A proper rewrite is in order

def __do_select_bakfile(bakfiles: List[bakfile.BakFile],
                        select_prompt=default_select_prompt,
                        err=True,
                        diff=True,
                        return_index=False):
    console = Console(file=stderr if err else stdout)

    show_bak_list(bakfiles[0].orig_abspath, err=err, colors=(
        BAK_LIST_COLORS and not FASTMODE), compare=diff)

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
                    if return_index:
                        return (bakfiles[idx], idx)
                    return bakfiles[idx]
            except (ValueError, TypeError) as error:
                warn(error)
                console.print("Invalid input. Aborting.")
                return False
            get_choice()


def __remove_bakfiles(entries_to_remove):
    for entry in entries_to_remove:
        Path(entry.bakfile_loc).unlink()
        db_handler.del_bakfile_entry(entry)


def __keep_bakfiles(bakfile_entry, bakfile_entries, new_destination, bakfile_numbers_to_keep):
    if not new_destination:
        for entry in bakfile_entries:
            if all((entry.restored,
                    entry.bakfile_loc != bakfile_entry.bakfile_loc)):
                db_handler.set_restored_flag(entry, False)
        db_handler.set_restored_flag(bakfile_entry, True)
    keep_all = not bakfile_numbers_to_keep
    if not keep_all:
        baks_to_remove = []
        for i, entry in enumerate(bakfile_entries):
            if (i + 1) not in bakfile_numbers_to_keep:
                baks_to_remove.append(bakfile_entries[i])
        __remove_bakfiles(baks_to_remove)


def __identify_baks(entries):
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


def __distinguish_baks(bakfiles):
    filenames = set(_bakfile.orig_abspath for _bakfile in bakfiles)
    _identified_baks = {}
    for _filename in filenames:
        _identified_baks[_filename] = __identify_baks(
            [_bakfile for _bakfile in bakfiles if _bakfile.orig_abspath == _filename])
    return _identified_baks


bold_style = Style(bold=True, italic=True)
purple_style = Style(bold=True, italic=True, color="purple")
blue_style = Style(color="blue")
none_style = Style()


def __generate_caption(colors, compare):
    if colors:
        caption = Text()
        caption.append('-- ', style="red" if colors else none_style)
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
        caption.append(
            '   (files may have been edited since restoration)', style='dim italic')
    else:
        caption = '-- oldest .bak   ++ newest .bak   ** restored' +\
            ('  $ current version of file' if compare else '') +\
            '\n   (files may have been edited since restoration)'
    return caption


def __prep_list_row(_bakfile,
                    compare,
                    colors,
                    current_style,
                    filename_exists,
                    relative_paths,
                    current_filename,
                    _identified_baks,
                    i):
    # Apply identifying markers to indices
    if Path(current_filename).exists() and compare:
        current_version_marker = \
            Text("$ ") if compare_files(
                _bakfile.bakfile_loc, current_filename) else None
    else:
        current_version_marker = None

    restored_marker = \
        Text('** ') if _bakfile.restored else None

    _id_baks = _identified_baks[_bakfile.orig_abspath]
    marker = ('-- ' if _bakfile is _id_baks[0]
              else ('++ ' if _bakfile is _id_baks[1]
                    else ""))
    marker = Text(marker) if marker else Text()

    if colors:
        if restored_marker:
            restored_marker.stylize("yellow")
        if current_version_marker:
            current_version_marker.stylize("green")
        if marker:
            marker.stylize(
                "green" if '+' in marker else "red" if '-' in marker else None)
        index = marker.append(str(i))
    else:
        index = marker.append_text(Text(str(i)))
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

    o_path.stylize('green' if filename_exists and colors else current_style)
    o_created.stylize(current_style)
    o_modified.stylize(current_style)

    return (index, o_path, o_created, o_modified)
########################
########################
########################
# endregion


def show_bak_list(filename: Optional[Path] = None,
                  relative_paths: bool = BAK_LIST_RELPATHS,
                  err=False,
                  colors: bool = BAK_LIST_COLORS,
                  compare: bool = False):
    """ Prints list of .bakfiles with metadata

    Arguments:
        filename (str|os.path, optional):
        List only `filename`'s .bakfiles
    """

    def _rotate_style(bold: bool):
        if not colors:
            return bold_style if bold else none_style
        return purple_style if bold else blue_style

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
    table = Table(title=(f".bakfiles of {filename}" if
                         filename else ".bakfiles"),
                  show_lines=True,
                  box=box.HEAVY_EDGE,
                  caption=__generate_caption(colors, compare))
    table.add_column("", justify='right', style=None)
    table.add_column("Original File")
    table.add_column("Date Created")
    table.add_column("Last Modified")

    # Distinguish .bakfiles from different original files
    i = 1
    current_filename = bakfiles[0].orig_abspath
    current_style = blue_style if colors else none_style
    bold = False  # First line will be opposite, toggled between population and rendering of table row

    # Begin individual row prep and add
    for _bakfile in bakfiles:
        _id_baks = __distinguish_baks(bakfiles)
        # Alternate styles on every other filename
        if current_filename != _bakfile.orig_abspath:
            current_filename = _bakfile.orig_abspath
            bold = not bold
            current_style = _rotate_style(bold)

        table.add_row(*__prep_list_row(_bakfile,  # the current row's bakfile
                                       compare,  # options
                                       colors,
                                       current_style,
                                       filename is not None,
                                       relative_paths,  # end options
                                       current_filename,  # orig_abspath
                                       _id_baks,  # oldest/newest/restored
                                       i  # current row index
                                       ))
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
    current_entries = db_handler.get_bakfile_entries(
        filename.expanduser().resolve())
    if current_entries:
        if compare_files(__identify_baks(current_entries)[1].bakfile_loc, filename.expanduser().resolve()):
            if not click.confirm("No changes to file since last bak. Would you like to create a duplicate .bakfile?"):
                click.echo("Cancelled.")
                return
    new_bakfile = __assemble_bakfile(filename)
    copy2(new_bakfile.orig_abspath, new_bakfile.bakfile_loc)
    db_handler.create_bakfile_entry(new_bakfile)


def bak_up_cmd(filename: Path, bakfile_number: int=0):
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
    if len(old_bakfile) == 1:
        old_bakfile = old_bakfile[0]
        if bakfile_number > 1:
            console.print(f"Only found 1 bakfile for {filename}")
    elif bakfile_number > 0:
        old_bakfile = __get_bakfile_entry(filename, bakfile_number=bakfile_number, console=console)
    else:
        old_bakfile = __do_select_bakfile(old_bakfile,
                            select_prompt=(
                                ("Enter a number to overwrite a .bakfile, or:\n(V)iew (C)ancel", "C")))

    if old_bakfile is None:
        console.print("Cancelled.")
        return True
    elif not isinstance(old_bakfile, bakfile.BakFile):
        return False

    copy2(old_bakfile.original_file, old_bakfile.bakfile_loc)
    old_bakfile.date_modified = datetime.now()
    db_handler.update_bakfile_entry(old_bakfile)
    return True

def _sudo_bak_down_helper(src, dest):
    # TODO spin this off into a separate exec for sanity
    click.echo(f"The destination {dest} is privileged. Falling back on 'sudo cp'")
    call(f"sudo cp {src} {dest}".split(" "))

def bak_down_cmd(filename: Path,
                 destination: Optional[Path],
                 keep_bakfile: Union[bool, List[int]] = None,
                 quiet: bool = False,
                 bakfile_number: int = 0):
    """ Restore `filename` from .bakfile. Prompts if ambiguous (such as
        when there are multiple .bakfiles of `filename`)

    Args:
        filename (str|Path)
        keep_bakfile (bool): If False, .bakfile is deleted (default: False)
        quiet (bool): If True, does not ask user to confirm
        destination (None|Path): destination path to restore to
    """
    bakfile_entry = None
    bakfile_entries = []
    console = Console()
    new_destination = False
    index = 0
    bakfile_entries = db_handler.get_bakfile_entries(filename)
    if not bakfile_entries:
        console.print(f"No bakfiles found for {filename}")
        return
    if bakfile_number:
        bakfile_entry = __get_bakfile_entry(filename,
                                              bakfile_number=bakfile_number,
                                              console=console)
        if not bakfile_entry:
            console.print("Cancelled.")
            return
        index = bakfile_number-1
    else:
        try:
            bakfile_entry, index = __do_select_bakfile(bakfile_entries, return_index=True) if len(
                bakfile_entries) else (bakfile_entries[0], 0)
        except TypeError: # __do_select_bakfile returned False. Operation cancelled.
            return
    if not bakfile_entry:
        console.print(f"No bakfiles found for {filename}" if bakfile_entry is None else "")
        return
    if destination:
        new_destination = destination.expanduser() != bakfile_entry.orig_abspath
    else:
        destination = Path(bakfile_entry.orig_abspath)

    confirm = True if quiet else _bak_down_confirm_helper(filename,
                                                          bakfile_number,
                                                          bakfile_entries,
                                                          destination,
                                                          new_destination,
                                                          keep_bakfile,
                                                          index)
    if not confirm:
        console.print("Cancelled.")
        return

    try:
        copy2(bakfile_entry.bakfile_loc, destination)
    except PermissionError:
        _sudo_bak_down_helper(bakfile_entry.bakfile_loc, destination)

    if not keep_bakfile and not new_destination:
        for entry in bakfile_entries:
            if entry.restored:
                if entry.bakfile_loc != bakfile_entry.bakfile_loc:
                    db_handler.set_restored_flag(entry, False)
        db_handler.set_restored_flag(bakfile_entry, True)

    baks_to_keep = []
    if isinstance(keep_bakfile, list):
        keep_bakfile = sorted(set(keep_bakfile))
        try:
            baks_to_keep = [int(i) for i in keep_bakfile]
        except ValueError:
            if keep_bakfile != ['all']:
                click.echo("Error: bak down --keep only accepts bakfile #s or the word 'all'")
                click.echo("Cancelled.")
                return

    args = [bakfile_entries] if not keep_bakfile else [bakfile_entry,
                                                       bakfile_entries,
                                                       new_destination,
                                                       baks_to_keep]
    helper = __keep_bakfiles if keep_bakfile else __remove_bakfiles
    helper(*args)

def _bak_down_confirm_helper(filename,
                             bakfile_number,
                             bakfile_entries,
                             destination,
                             new_destination, 
                             keep_bakfile, 
                             index):
# TODO at this point, just turn this into something stateful
    if all((new_destination, destination.exists())):
        if not click.confirm(f"Overwrite {destination}?", default=False):
            click.echo("Cancelled.")
            return False

    erase = ''
    keep_which = ''
    joint = ''
    _all = ''
    if keep_bakfile:
        erase = 'keep'
        if isinstance(keep_bakfile, list):
            if len(keep_bakfile) > 1:
                if len(keep_bakfile) > 2:
                    joint = ', '
                else:
                    joint = ' '
                keep_bakfile[-1] = "and " + keep_bakfile[-1]
                keep_which = ' ' + joint.join(keep_bakfile)
            else:
                keep_which = ' ' + keep_bakfile[0]
    if keep_which.endswith('all'):
        _all = ' all'
    elif len(keep_which.strip()) == 1:
        keep_which = ' #' + keep_which.lstrip()
    else:
        keep_which = 's ' + keep_which.lstrip()

    confirm_prompt = f"Confirm: Restore {filename}"

    multiples = bool(len(bakfile_entries))
    restore_from = f"{index + 1}" \
        if (multiples or index != 0) \
        else (f"{bakfile_number}" if bakfile_number else '')
    confirm_prompt += f" from bakfile #{restore_from}" if restore_from else ''
        
    confirm_prompt += f" to {destination}" if new_destination else ""
    confirm_prompt += f" and {erase}{_all} bakfile{keep_which if not _all else ('s' if multiples else '')}?"

    return click.confirm(confirm_prompt, default=False)

def bak_del_cmd(filename:Path, bakfile_number:int, quietly=False):
    """ Deletes a bakfile by number
    """
    console = Console()
    _bakfile = None
    bakfiles = db_handler.get_bakfile_entries(filename)
    if not bakfiles:
        console.print(f"No bakfiles found for {filename}")
        return False
    if not bakfile_number:
        try:
            _bakfile, bakfile_number = \
                __do_select_bakfile(bakfiles,
                                    select_prompt=(("Delete which .bakfile?"),
                                                    default_select_prompt[0]),
                                    return_index=True)
            bakfile_number += 1
        except TypeError:
            return True
    confirm = input(
        f"Confirming: Delete bakfile #{bakfile_number} for {filename}? "
        f"(y/N) ").lower() == 'y' if not quietly else True
    if confirm:
        _bakfile = _bakfile or __get_bakfile_entry(filename,
                                                   bakfile_number=bakfile_number,
                                                   console=console)
        if not _bakfile:
            return False
        __remove_bakfiles([_bakfile])
        return True

def bak_off_cmd(filename: Optional[Path],
                quietly=False):
    """ Used when finished. Deletes all instances of `filename.bak`
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
                  using: (str, None) = None,
                  bakfile_number: int = 0):
    # if this thing is given a string, it needs to go find
    # a corresponding bakfile
    console = Console()

    if not isinstance(bak_to_print, bakfile.BakFile):
        _bak_to_print = __get_bakfile_entry(bak_to_print,
                                            select_prompt=(
                                                "Enter a number to select a .bakfile, or:\n(D)iff (C)ancel",
                                                "C"),
                                            bakfile_number=bakfile_number,
                                            console=console)
        if all((_bak_to_print is None, not bakfile_number)):
            console.print(
                f"No bakfiles found for {Path(bak_to_print).resolve()}")
        else:
            bak_to_print = _bak_to_print
        if not isinstance(bak_to_print, bakfile.BakFile):
            return  # __get_bakfile_entry() handles failures, so just exit here
    pager = using if using else \
        (cfg['bak_open_exec'] or os.environ['PAGER']) or 'less'
    pager = pager.strip('"').strip("'").split(" ")
    call(pager + [bak_to_print.bakfile_loc])


def bak_getfile_cmd(bak_to_get: (str, bakfile.BakFile), bakfile_number:int=0):
    console = Console(file=stderr)

    if not isinstance(bak_to_get, bakfile.BakFile):
        filename = bak_to_get
        bak_to_get = __get_bakfile_entry(bak_to_get,
                                         err=True,
                                         bakfile_number=bakfile_number,
                                         console=console)
        if not bak_to_get:
            if bakfile_number:
                console.print("Invalid bakfile #")
            elif bak_to_get is None:
                console.print(f"No bakfiles found for {Path(filename).resolve()}")
            return  # __get_bakfile_entry() handles failures, so just exit
    print(bak_to_get.bakfile_loc)


def bak_diff_cmd(filename: (bakfile.BakFile, Path), command=None, bakfile_number: int=0):
    '''
    Expects a config value for its exec along the lines of:
        diff %old %new
    or:
        diff -r %old %new
    which will be substituted with the bakfile and the original file.
    '''
    # TODO write tests for this (mildly tricky)
    console = Console()
    bak_to_diff = filename if isinstance(filename, bakfile.BakFile) else \
        __get_bakfile_entry(filename,
                            diff=not FASTMODE,
                            select_prompt=(
                                ("Enter a number to diff a .bakfile, or:\n(V)iew (C)ancel", "C")),
                            bakfile_number=bakfile_number,
                            console=console)
    if not command:
        command = cfg['bak_diff_exec']
        if not command or any((i not in command.lower() for i in ['%old', '%new'])):
            command = 'diff %old %new'
    if bak_to_diff is None:
        if not bakfile_number:
            console.print(f"No bakfiles found for {filename}")
        return
    if not bak_to_diff:
        return

    command = command.split(" ")
    command[command.index('%old')] = bak_to_diff.bakfile_loc
    command[command.index('%new')] = bak_to_diff.orig_abspath
    call(command)


def bak_config_command(get_op: bool, setting: str, value: tuple = ()):
    # TODO make a proper Click help formatter for this and certain other functions
    # (Click does weird things with tabs and newlines, and this nonsense is
    # required just to obtain the unsatisfactory result we've got.)
    if setting not in cfg.SETTABLE_VALUES:
        click.echo("Invalid setting. Valid choices include:\n\t\t\t"
                   + "\n\t\t\t".join(option for option in cfg.SETTABLE_VALUES))
        return
    if any((get_op, value == ())):
        try:
            click.echo(cfg.get(setting, literal=True))
        except KeyError:
            click.echo(f"Unknown option {setting}")
    else:
        try:
            cfg[setting] = ' '.join(value)
        except KeyNotFoundError as err:
            click.echo(err)
