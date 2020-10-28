import os
from datetime import datetime

import click
from click_default_group import DefaultGroup

import cmd
import data

bakfile_db = data.bak_db.BakDBHandler(os.environ["BAK_DB_LOC"])


@click.group(cls=DefaultGroup, default='create', default_if_no_args=True)
# @click.pass_context
# @click.argument("filename", required=False)
# def bak(ctx, filename=None):
def bak():
    pass
    # if ctx.invoked_subcommand is None:
    #     if not filename:
    #         click.echo("A filename or operation is required.\n"
    #                    "\tbak --help")


@bak.command()
@click.argument("filename", required=True)
def create(filename):
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
