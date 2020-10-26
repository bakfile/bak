# bak

**bak** is a command-line utility for creating and restoring backup copies of single files, without clutter.

As residents of the terminal, we all make a lot of on-the-fly, in-place, single-file backups. Config files, dotfiles, "I'm only pretty sure I know what I'm doing" files, before you break them, you do this:

`cp my_thing.file my_thing.file.bak`

The problem, of course, is remembering to delete that file when you're finished.

**bak**'s goal is simply to obviate this process. Using **bak**, you'll be able to manage your bakfiles with four simple commands:

`bak my_file` - Create a bakfile in a configured location (default: XDG data directory if present, ~/.bak if not  
`bak up my_file` - Overwrite current `my_file.bak`, rather than creating something like `my_file.bak.1`. Without file argument, overwrites most recent .bakfile) 
`bak down my_file` - Deletes `my_file` and restores it from `my_file.bak`  
`bak off my_file` - Deletes `my_file.bak`, prompts if ambiguous. Without file argument, deletes most recent .bakfile  

Don't worry, they're easy to remember after a minute:

`bak`: bak.  
`bak up`: I've made changes, back them up.  
`bak down`: I've screwed up, undo the damage.  
`bak off`: I'm done working. Go away, **bak**.

## Advanced features
---

**bak** is also slated to support a number of flags, as well as rich output, such as:

`bak list` - List all .bakfiles, with a bit of metadata to help with disambiguation  
`bak list my_file` - List all .bakfiles *of the specified file*, with metadata  
`bak down --keep my_file` - Restores from .bakfile, does not delete .bakfile  
`bak diff my_file <bakfile>` - Self-explanatory. Without .bakfile argument, diffs `my_file` against its most recent .bakfile. By default, uses [ydiff](https://github.com/ymattw/ydiff). Can be configured to use the difftool of your choice.