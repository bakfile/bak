import functools
import os
from datetime import datetime
from pathlib import Path
from shutil import copy2

import click
from click_default_group import DefaultGroup

from bak import commands
from bak import version as bak_version


def __print_help():
    with click.get_current_context() as ctx:
        click.echo(bak.get_help(ctx))


def normalize_path(args_key: str = 'filename'):
    def on_decorator(func):
        @functools.wraps(func)
        def on_call(*args, **kwargs):
            try:
                # expand path
                arg = Path(kwargs[args_key]).expanduser().resolve()
                if arg.is_dir():
                    click.echo(f"Error: bak cannot operate on directories ({arg})")
                    return
                else:
                    kwargs[args_key] = arg
            # Account for optional params and params that default to None or False
            except (IndexError, KeyError, TypeError):
                pass
            return func(*args, **kwargs)
        return on_call
    return on_decorator


basic_help_text = "bak FILENAME (creates a bakfile)\n\n" +\
    "See also: bak COMMAND --help"


@click.group(cls=DefaultGroup, default='\0', default_if_no_args=True, help=basic_help_text)
def bak():
    pass


@bak.command("\0", hidden=True)
@normalize_path()
@click.option("--version", required=False, is_flag=True)
@click.argument("filename", required=False, type=click.Path(exists=True))
# Ensures that 'bak --help' is printed if it doesn't get a filename
def create(filename, version):
    if version:
        click.echo(f"bak version {bak_version}")
    elif not filename:
        __print_help()
    else:
        filename = Path(filename).expanduser().resolve()
        commands.create_bakfile(filename)


@bak.command("up", help="Replace a .bakfile with a fresh copy of the parent file")
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_up(filename):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    filename = Path(filename).expanduser().resolve()
    if not commands.bak_up_cmd(filename):
        # TODO descriptive failures
        click.echo("An error occurred.")


@bak.command("down", help="Restore from a .bakfile (.bakfiles deleted without '--keep')")
@click.option("--keep", "-k",
              is_flag=True,
              default=False,
              help="Keep .bakfiles")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="No confirmation prompt")
@click.argument("filename", required=True)
def bak_down(filename, keep, quietly):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    filename = Path(filename).expanduser().resolve()
    commands.bak_down_cmd(filename, keep, quietly)


@bak.command("off", help="Use when finished to delete .bakfiles")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="Delete all related .bakfiles without confirming")
@click.argument("filename", required=True)
def bak_off(filename, quietly):
    filename = Path(filename).expanduser().resolve()
    if not commands.bak_off_cmd(filename, quietly):
        # TODO better output here
        click.echo("Operation cancelled or failed.")


@bak.command("open", help="View or edit a .bakfile in an external program")
@click.option("--using", "--in", "--with",
              help="Program to open (default: $PAGER or less)",
              required=False, hidden=True)
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_print(filename, using):
    filename = Path(filename).expanduser().resolve()
    commands.bak_print_cmd(filename, using)


@bak.command("get-bak",
             help="Outputs the real path of a .bakfile. "
             "Useful for piping, and not much else.",
             short_help="Output the real path of a .bakfile")
@click.argument("to_where_you_once_belonged",
                required=True,
                type=click.Path(exists=True))
@normalize_path()
def bak_get(to_where_you_once_belonged):
    to_where_you_once_belonged = Path(to_where_you_once_belonged).expanduser().resolve()
    commands.bak_getfile_cmd(to_where_you_once_belonged)


@bak.command("diff",
             help="diff a file against its .bakfile")
@click.option("--using", "--with",
              help="Program to use instead of system diff",
              required=False)
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_diff(filename, using):
    filename = Path(filename).expanduser().resolve()
    commands.bak_diff_cmd(filename, command=using)


@bak.command("list",
             help="List all .bakfiles, or a particular file's")
@click.option("--relpaths",
              help="Display relative paths instead of abspaths",
              required=False,
              is_flag=True,
              default=commands.bak_list_relpaths)
@click.argument("filename",
                #   help="List a particular file's .bakfiles",
                required=False,
                type=click.Path(exists=True))
@normalize_path()
def bak_list(relpaths, filename):
    if filename:
        filename = Path(filename).expanduser().resolve()
    commands.show_bak_list(filename=filename or None, relative_paths=relpaths)


if __name__ == "__main__":
    bak()
