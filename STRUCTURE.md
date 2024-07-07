
#

`bak` the program and `bakfile` the underlying library share this repository. Almost everything you might want to extend or reuse is part of `bakfile`. I believe you could write a wholesale `bak` replacement off of it, existing DB and all.

```text
src/
|--lib/                 bakfile; Implementation spread across several files (not depicted)
|  |--enums/            bakfile submodule providing its namesake (not meant to be imported)
|--|--versioning.rs     supplies versioning for bakfile, the library
|  |--lib.rs            exports
|--bin/                 at the moment, just `bak`
|--|--bak/    
|--|--|--cmd.rs         clap (command line interface library) boilerplate and helpers
|--|--|--exec.rs        bak command implementations
|--|--|--main.rs        bak executable
|--|--|--versioning.rs  supplies versioning for bak, the executable
```
