# bak

[![](https://gist.github.com/veracioux/5281aa92b29e89c0da0086207640dfd2/raw/1a35f46b3b1ae00baed35911789faedb6fe8519f/bak_demo.svg)](https://asciinema.org/a/442668)

**bak** is a command-line utility for creating and restoring backup copies of single files - `.bak` files - without clutter.

- [Description and Usage](#description-and-usage)
- [Additional Commands](#additional-commands-and-flags)
- [Installation and Requirements](#installation-and-requirements)
- [Current State](#current-state)
- [Contributing](#contributing)

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

All of **bak**'s commands will disambiguate between multiple copies of the same file. In other words, you can `bak my_thing.txt` as many times as you want, until you're finished working, if you'd prefer to keep multiples instead of using `bak up`. At the moment, all you've got to go by are timestamps when it asks you to pick a .bakfile, but this will improve.

**NOTE:** `bak down` will fall back on `sudo cp` if necessary. Please don't run `sudo bak`. This may create parallel config and bakfiles in root's XDG directories.

## Additional commands and flags

`bak down --keep my_file` - Restores from .bakfile, does not delete .bakfile  
`bak diff my_file` Compare a .bakfile using `diff` (configurable)  
`bak list`/`bak list my_file` - List all .bakfiles, or just `my_file`'s  
`bak open my_file` View a .bakfile in $PAGER (configurable)  
`bak open --using exec my_file` View a .bakfile using `exec`  (alias `--in`)

> examples:

        bak open --using cat my_file.json
        bak open --in nvim my_file.json

`bak where my_file` Get the abspath of a .bakfile, in case, for some reason, you want to pipe it somewhere

> example (for illustrative purposes; use 'bak diff' instead):

    diff `bak where my_file.json` my_file.json

## Installation and Requirements

**NOTE:** This repository's default branch has been changed to `unstable` for development. For general use, I advise installing the `master` branch. This will be easier when I get around to proper packaging.

Requires Python3.6 or higher, presumably. Python3.5 has been EOL for 3 months, as of this writing, so if your distro is pegged to it... ouch.

### Installation

As the program is currently in an alphaish state, I have decided not to create distro packages *yet*. I will provide GitHub releases whenever I bump the alpha-alpha version number.

However, if you're comfortable with Python, you can install this repository with the provided `setup.py` *or* with pip (just run pip on the local directory.)

If you'd like to hack on `bak`, I suggest the latter; I'm in the habit of making a project venv, and then doing  
`pip3 install --editable .`

In `bak`'s case, I usually test system-level usage with a simple and naive `setup.py install --force`

## Current state

(updated Jan. 20, 2020)  
This is a very pre-alpha version, as in, this is a spaghetti proof-of-concept. Perhaps ~~5-6~~ ~~12-15~~ 20 hours have been spent on development so far. As such, it's only "working" in the strictest sense.

At the moment, **bak** stores its database and your bakfiles in `$XDG_DATA_HOME/bak`. If `$XDG_DATA_HOME` is not set, its specified default is used, and your stuff ends up in `~/.local/share/bak`.

The config file exists, but could be more intuitive. It's at `$XDG_CONFIG_HOME/bak.cfg` or `~/.config/bak.cfg` and currently accepts values for:

- The location of your .bakfiles and bakfile DB (I don't recommend changing this)
- The program to use by default for `bak open`
- The program to use by default for `bak diff` (at the moment, this must support typical `diff` syntax, as in `diff <file1> <file2>`)
- Whether `bak list` should display relative paths (defaults to False)

If the above sections suggest that a command is implemented, it's working at the most basic level. There are few sanity checks. Expect and please report bugs, as well as feature requests. If you're brave enough to work on a project in the early, mediocre phase, go nuts with the PRs.

Also, there's ~~no~~ very little exception handling (yet.)

## Contributing

By and large, I welcome PRs, though I never promise merges.

With an MIT license and GitHub, the licensing situation is a lot more straightforward than in some other cases: you clone this repo, you're getting the code from the author, and the license has the word "irrevocable" in it. Then you're offering a modified version *back* to the author, with the same license file, still containing the word "irrevocable." What's there to sue about?

So go nuts, if you're so inclined. I have no particular expectations for this project.
