# bak

**bak** is a command-line utility for creating and restoring backup copies of single files - `.bak` files - without clutter.

As residents of the terminal, we all make a lot of on-the-fly, in-place, single-file backups. Config files, dotfiles, "I'm only pretty sure I know what I'm doing" files, before you break them, you do this:

`cp my_thing.file my_thing.file.bak`

The problem, of course, is remembering to delete that file when you're finished.

**bak**'s goal is simply to obviate this process. Using **bak**, you'll be able to manage your bakfiles with four simple commands:

`bak my_file` - Create a bakfile in a configured location (default: XDG data directory if present, ~/.bak if not  
`bak up my_file` - Overwrite current `my_file.bak`, rather than creating a second .bakfile. Without file argument, overwrites most recent .bakfile.)  
`bak down my_file` - Deletes `my_file` and restores it from `my_file.bak`  
`bak off my_file` - Deletes `my_file.bak`, confirming by default (`bak off -q` to suppress)

Don't worry, they're easy to remember after a minute:

`bak`: bak.  
`bak up`: I've made changes, back them up.  
`bak down`: I've screwed up, undo the damage.  
`bak off`: I'm done working. Go away, **bak**, and take your .bakfile with you.

## Advanced features (Not yet implemented as of Oct. 28, 2020)
**bak** is also slated to support a number of flags, as well as rich output, such as:

`bak list` - List all .bakfiles, with a bit of metadata to help with disambiguation  
`bak list my_file` - List all .bakfiles *of the specified file*, with metadata  
`bak down --keep my_file` - Restores from .bakfile, does not delete .bakfile  
`bak diff my_file <bakfile>` - Self-explanatory. Without .bakfile argument, diffs `my_file` against its most recent .bakfile. By default, uses [ydiff](https://github.com/ymattw/ydiff). Can be configured to use the difftool of your choice.

## Current state
This is a very pre-alpha version, as in, this is a spaghetti proof-of-concept. Perhaps 5-6 hours have been spent on development so far. As such, it's only "working" in the strictest sense.

At the moment, **bak** requires two environment variables which it will not set on its own. In the future, this information will be read from user config. These are:

`$BAK_DB_LOC`: Where to keep the bakfile database (it's tiny.) This will ultimately default either to `~/.bak` or $XDG_DATA_HOME.  
`$BAK_DIR`: Where to keep the bakfiles themselves. When $BAK_DB_LOC gets a sensible default, this will probably be a subfolder in the same location, such as `~/.bak/bakfiles`.

Currently, I'd do:

```
export BAK_DB_LOC=~/.bak
export BAK_DIR=~/.bak/bakfiles
```

`bak filename`, `bak up filename`, `bak down filename` and `bak off filename` all work, at the most basic level. There are no sanity checks. If you run `bak filename` more than once, `bak off` and `bak up` will only delete the first, so be careful. This will change.

Also, there's no exception handling yet.
