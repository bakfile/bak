# bak

**bak** is a command-line utility for creating and restoring backup copies of single files - `.bak` files - without clutter.

- [bak](#bak)
  - [Description and Usage](#description-and-usage)
  - [Additional commands and flags](#additional-commands-and-flags)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Contributing](#contributing)
  - [Architecture](#architecture)

## Description and Usage

As residents of the terminal, we all make a lot of on-the-fly, in-place, single-file backups. Config files, dotfiles, "I'm only pretty sure I know what I'm doing" files, before you break them, you do this:

`cp my_thing.file my_thing.file.bak`

The problem, of course, is remembering to delete that file when you're finished.

**bak**'s goal is simply to obviate this process. Using **bak**, you'll be able to manage your bakfiles with four simple commands:

`bak my_file` - Create a bakfile in a configured location (default: XDG_DATA_HOME/bak/bakfiles, or XDG's default location)  
`bak up my_file` - Overwrite current `my_file.bak`, rather than creating a second .bakfile.  
`bak down my_file` - Deletes `my_file` and restores it from `my_file.bak`  
`bak off my_file` - Deletes `my_file.bak`, confirming by default (`bak off -q` to suppress)

Don't worry, they're easy to remember after a minute:

`bak`: bak.  
`bak up`: I've made changes, back them up.  
`bak down`: I've screwed up, undo the damage.  
`bak off`: I'm done working. Go away, **bak**, and take your .bakfile with you.

All of **bak**'s commands will disambiguate between multiple copies of the same file. In other words, you can `bak my_thing.txt` as many times as you want, until you're finished working, if you'd prefer to keep multiples instead of using `bak up`.

You can also diff a file against a bakfile, or display a bakfile, either using additional commands (see below) or directly from the disambiguation menu.

## Additional commands and flags

`bak down --keep my_file` - Restores from .bakfile, does not delete .bakfile  
`bak diff my_file` Compare a .bakfile using `diff` (configurable)  
`bak list`/`bak list my_file` - List all .bakfiles, or just `my_file`'s  
`bak open my_file` View a .bakfile using another program, default `cat` (configurablem alias `show`)  
`bak open --using exec my_file` View a .bakfile using `exec`  (aliases `--in`, `--with`)  

> examples:

        bak open --using bat my_file.json
        bak show --in nvim my_file.json

`bak where my_file` Get the abspath of a .bakfile, in case, for some reason, you want to pipe it somewhere

> example (for illustrative purposes; use 'bak diff' instead):

    diff `bak where my_file.json` my_file.json

## Installation

Distro packages will happen in the coming weeks (written Nov. 06, 2025)

Those wishing to build the program from source should use `master`.

If you'd like to hack on `bak`, branch off of and target `dev`.

## Configuration

By default, **bak** stores its database and your bakfiles in `$XDG_DATA_HOME/bak`. If `$XDG_DATA_HOME` is not set, its specified default is used, and your stuff ends up in `~/.local/share/bak`.

The config file is TOML. It's at `$XDG_CONFIG_HOME/bak.conf` or `~/.config/bak.conf`, and currently accepts values for:

- The location of your .bakfiles and bakfile DB
- The program to use by default for `bak open`
- The program to use by default for `bak diff`
- Whether `bak list` should display relative paths (defaults to False, not currently implemented)
- Whether `bak list` should display colorized output (defaults to True, not currently implemented)
- Whether `bak` should run `--quiet` by default
- Whether `bak list` should mark bakfiles when the original file has changed

It also contains a little bit of metadata that `bak` can use to handle updates.

## Contributing

See CONTRIBUTING.md

## Architecture

This project contains two parts: `bak`, the main app, and `bakfile`, its guts presented as a library, so that, in an unlikely hypothetical, somebody could write a different executable to manage or interact with the same bakfiles, sparing the user the need to choose a utility. The layout of each module should speak for itself.

.bakfiles are tracked in a single-table sqlite database. sqlite was chosen when this was a Python project, and kept because it's fast, it works, and it's reliably present on most Unix systems, so, in practice, our system packages aren't carrying any dependencies the user won't already have. Alternatives were considered, most of which boiled down to text files, and rejected either as unwieldy or on the basis that there's no need to change. Because `bak` isn't meant to be scripted, it isn't currently locking its database, but there is an open ticket to do so.

I would very much like to flatten our deptree in the future, because the scope of the ecosystem makes me nervous. Many of our external dependencies could be removed via refactor, or the relevant pieces imported under permissive licenses. I am less confident about removing `clap`, because it's far too large to reimplement, and the alternatives I considered were unable to produce the same results.

Colorized output is not currently implemented due to a broken interaction between `console` and `comfy-table`, which I need to chase down with the latter's devs.