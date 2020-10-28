import os
from datetime import datetime

import click
from click_default_group import DefaultGroup

import cmd
import data

bakfile_db = data.bak_db.BakDBHandler(os.environ["BAK_DB_LOC"])


def __print_help():
    with click.get_current_context() as ctx:
        click.echo(bak.get_help(ctx))


@click.group(cls=DefaultGroup, default='create', default_if_no_args=True)
def bak():
    pass

# Ensures that 'bak --help' is printed if it doesn't get a filename


@bak.command()
@click.argument("filename", required=False)
def create(filename):
    if not filename:
        __print_help()
    elif not os.path.exists(filename):
        print("File not found: ", filename)
        __print_help()
    else:
        cmd.create_bakfile(filename, bakfile_db.db_loc)


@bak.command("up")
@click.argument("filename", required=True)
def bak_up(filename):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    cmd.bak_up_cmd(filename, bakfile_db.db_loc)


if __name__ == "__main__":
    bak()
