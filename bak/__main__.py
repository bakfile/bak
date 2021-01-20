import os
from datetime import datetime
from shutil import copy2

import click
from click_default_group import DefaultGroup

from bak import commands


def __print_help():
    with click.get_current_context() as ctx:
        click.echo(bak.get_help(ctx))


basic_help_text = "bak FILENAME (creates a bakfile)\n\n" +\
    "See also: bak COMMAND --help"


@click.group(cls=DefaultGroup, default='\0', default_if_no_args=True, help=basic_help_text)
def bak():
    pass


@bak.command("\0", hidden=True)
@click.argument("filename", required=False, type=click.Path(exists=True))
# Ensures that 'bak --help' is printed if it doesn't get a filename
def create(filename):
    if not filename:
        __print_help()
    else:
        commands.create_bakfile(filename)


@bak.command("up", help="Replace a .bakfile with a fresh copy of the parent file")
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_up(filename):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
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
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_down(filename, keep, quietly):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    commands.bak_down_cmd(filename, keep, quietly)


@bak.command("off", help="Use when finished to delete .bakfiles")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="Delete all related .bakfiles without confirming")
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_off(filename, quietly):
    if not commands.bak_off_cmd(filename, quietly):
        # TODO better output here
        click.echo("Operation cancelled or failed.")

@bak.command("open", help="View or edit a .bakfile in an external program")
@click.option("--using", "--in", "--with",
              help="Program to open (default: $PAGER or less)",
              required=False, hidden=True)
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_print(filename, using):
    commands.bak_print_cmd(filename, using)

@bak.command("get-bak",
             help="Outputs the real path of a .bakfile. "
             "Useful for piping, and not much else.",
             short_help="Output the real path of a .bakfile")
@click.argument("to_where_you_once_belonged",
                required=True,
                type=click.Path(exists=True))
def bak_get(to_where_you_once_belonged):
    commands.bak_getfile_cmd(to_where_you_once_belonged)


@bak.command("diff",
             help="diff a file against its .bakfile")
@click.option("--using", "--with",
              help="Program to use instead of system diff",
              required=False)
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_diff(filename, using):
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
def bak_list(relpaths, filename):
    commands.show_bak_list(filename=filename or None, relative_paths=relpaths)

if __name__ == "__main__":
    bak()
