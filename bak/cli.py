import functools
from pathlib import Path


import click
from click_default_group import DefaultGroup

from bak import commands
from bak import BAK_VERSION as bak_version
from bak.configuration import bak_cfg as cfg

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
                    click.echo(
                        f"Error: bak cannot operate on directories ({arg})")
                    return
                else:
                    kwargs[args_key] = arg
            # Account for optional params and params that default to None or False
            except (IndexError, KeyError, TypeError):
                pass
            return func(*args, **kwargs)
        return on_call
    return on_decorator


BASIC_HELP_TEXT = "bak FILENAME (creates a bakfile)\n\nalias: bak create\n\n" +\
    "See also: bak COMMAND --help"


@click.group(cls=DefaultGroup, default='\0', no_args_is_help=True, help=BASIC_HELP_TEXT,
             invoke_without_command=True)
# default command behavior is duplicated here because it's cleaner from a Click perspective,
# which is to say that it gets the desired behavior across the board. ugly but it works!
@click.option("--version", required=False, is_flag=True, help="Print current version and exit.")
def bak(version:bool=False):
    if version:
        create_bak_cmd(None, version)


@bak.command("\0", hidden=True)
@normalize_path()
@click.option("--version", required=False, is_flag=True, help="Print current version and exit.")
@click.argument("filename", required=False, type=click.Path(exists=True))
def _create(filename, version):
    create_bak_cmd(filename, version)


@bak.command("create", hidden=True)
@normalize_path()
@click.option("--version", required=False, is_flag=True)
@click.argument("filename", required=False, type=click.Path(exists=True))
def create(filename, version):
    create_bak_cmd(filename, version)


def create_bak_cmd(filename, version):
    if version:
        click.echo(f"bak version {bak_version}")
    elif not filename:
    # Ensures that 'bak --help' is printed if it doesn't get a filename
        __print_help()
    else:
        filename = Path(filename).expanduser().resolve()
        commands.create_bakfile(filename)


@bak.command("up", help="Replace a .bakfile with a fresh copy of the parent file")
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
@click.argument("bakfile_number", metavar="[#]", required=False, type=int)
def bak_up(filename, bakfile_number):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    filename = Path(filename).expanduser().resolve()
    if not commands.bak_up_cmd(filename, bakfile_number):
        # TODO descriptive failures
        click.echo("An error occurred.")


@bak.command("down", help="Restore from a .bakfile (.bakfiles deleted without '--keep')")
@click.option("--keep", "-k",
              is_flag=False,
              default=0,
              multiple=True,
              type=str,
              help="Keep .bakfiles (optionally accepts a bakfile #; can be used multiple times.\n" +\
                    "Also accepts 'all'")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="No confirmation prompt")
@click.option('-d', '-o', '--destination', default=None, type=str)
@click.argument("filename", required=True)
@click.argument("bakfile_number", metavar="[#]", required=False, type=int)
def bak_down(filename: str, keep: bool, quietly: bool, destination: str, bakfile_number: int=0):
    if not filename:
        click.echo("A filename or operation is required.\n"
                   "\tbak --help")
    filename = Path(filename).expanduser().resolve()
    if destination:
        destination = Path(destination).expanduser().resolve()
    if not isinstance(keep, tuple):
        if keep in [-1, 'all']:
            keep = True
        elif keep == 0:
            keep = False
    else:
        keep = list(keep)
    commands.bak_down_cmd(filename, destination, keep, quietly, bakfile_number)


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

@bak.command("del", help="Delete a single .bakfile by number (see `bak list FILENAME`)"
                         "\n\n\talias: `bak rm`")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="Delete .bakfile without confirming")
@click.argument("filename", required=True, type=click.Path(exists=False))
@click.argument("number", metavar="#", required=False, type=int)
def bak_del(filename, number, quietly):
    filename = Path(filename).expanduser().resolve()
    if not commands.bak_del_cmd(filename, number, quietly):
        # TODO this is just a copy of `bak off`, so...
        click.echo("Operation cancelled or failed.")

@bak.command("rm", hidden=True, help="Delete a single .bakfile by number (see `bak list FILENAME`)"
                         "\n\n\talias of `bak del`")
@click.option("--quietly", "-q",
              is_flag=True,
              default=False,
              help="Delete .bakfile without confirming")
@click.argument("filename", required=True, type=click.Path(exists=False))
@click.argument("number", metavar="#", required=False, type=int)
def _bak_rm(filename, number, quietly):
    bak_del(filename, number, quietly)

@bak.command("open", help="View or edit a .bakfile in an external program")
@click.option("--using", "--in", "--with",
              help="Program to open (default: $PAGER or less)",
              required=False, hidden=True)
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
@click.argument("bakfile_number", metavar="[#]", required=False, type=int)
def bak_print(filename, using, bakfile_number):
    filename = Path(filename).expanduser().resolve()
    commands.bak_print_cmd(filename, using, bakfile_number)


@bak.command("where",
             help="Outputs the real path of a .bakfile. "
             "Useful for piping, and not much else.",
             short_help="Output the real path of a .bakfile")
@click.argument("filename",
                required=True,
                type=click.Path())
@click.argument("bakfile_number", metavar="[#]", required=False, type=int)
@normalize_path()
def bak_get(filename, bakfile_number=0):
    to_where_you_once_belonged = Path(
        filename).expanduser().resolve()
    commands.bak_getfile_cmd(to_where_you_once_belonged, bakfile_number)


@bak.command("diff",
             help="diff a file against its .bakfile")
@click.option("--using", "--with",
              help="Program to use instead of system diff",
              required=False)
@normalize_path()
@click.argument("filename", required=True, type=click.Path(exists=True))
@click.argument("bakfile_number", metavar="[#]", required=False, type=int)
def bak_diff(filename, using, bakfile_number=0):
    filename = Path(filename).expanduser().resolve()
    commands.bak_diff_cmd(filename, command=using, bakfile_number=bakfile_number or 0)


@bak.command("list",
             help="List all .bakfiles, or a particular file's")
@click.option("--colors/--nocolors", "-c/-C",
              help="Colorize output",
              is_flag=True,
              default=cfg['bak_list_colors'] and not cfg['fast_mode'])
@click.option("--relpaths", "--rel", "-r",
              help="Display relative paths instead of abspaths",
              required=False,
              is_flag=True,
              default=commands.BAK_LIST_RELPATHS)
@click.option("--compare", "--diff", "-d",
              help="Compare .bakfiles with current file, identify exact copies",
              required=False,
              is_flag=True,
              default=False)
@click.argument("filename",
                required=False,
                type=click.Path(exists=True))
@normalize_path()
def bak_list(colors, relpaths, compare, filename):
    if filename:
        filename = Path(filename).expanduser().resolve()
    commands.show_bak_list(filename=filename or None,
                           relative_paths=relpaths, colors=colors, compare=compare)


TAB = '\t'
CFG_HELP_TEXT = '\b\nGet/set config values. Valid settings include:\n\n\t' + \
               f'\b\n{(TAB + cfg.newline).join(cfg.SETTABLE_VALUES)}' + \
                '\b\n\nNOTE: diff-exec\'s value should be enclosed in quotes, and' \
                '\nformatted like:\b\n\n\t\'diff %old %new\' \b\n\n(%old and %new will be substituted ' \
                'with the bakfile and the original file, respectively)'


@bak.command("config",
             short_help="get/set config options", help=CFG_HELP_TEXT)
@click.option("--get/--set", default=True)
@click.argument("setting", required=True)
@click.argument("value", required=False, nargs=-1, type=str)
def bak_config(get, setting, value):
    commands.bak_config_command(get, setting, value)
