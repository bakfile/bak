import os
from datetime import datetime

import click
from click_default_group import DefaultGroup

import cmd
import data


def __print_help():
    with click.get_current_context() as ctx:
        click.echo(bak.get_help(ctx))


@click.group(cls=DefaultGroup, default='create', default_if_no_args=True)
def bak():
    pass


@bak.command()
@click.argument("filename", required=False)
# Ensures that 'bak --help' is printed if it doesn't get a filename
def create(filename):
    if not filename:
        __print_help()
    else:
        cmd.create_bakfile(filename)


@bak.command("up")
@click.argument("filename", required=True)
def bak_up(filename):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    if not cmd.bak_up_cmd(filename):
        # TODO descriptive failures
        click.echo("An error occurred.")


@bak.command("down")
@click.option("--keep", "-k", is_flag=True, default=False, help="Keep .bakfiles")
@click.argument("filename", required=True, type=click.Path(exists=True))
def bak_down(filename, keep):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    cmd.bak_down_cmd(filename, keep)


@bak.command("off")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="Delete all related .bakfiles without confirming")
@click.argument("filename", required=True)
def bak_off(filename, quietly):
    if not cmd.bak_off_cmd(filename, quietly):
        # TODO better output here
        click.echo("Operation cancelled or failed.")


if __name__ == "__main__":
    bak()
