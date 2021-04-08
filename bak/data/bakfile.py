from datetime import datetime
from pathlib import Path


class BakFile:
    original_file: str
    orig_abspath: Path
    bakfile_loc: Path
    date_created: datetime
    date_modified: datetime

    def __init__(self,
                 original: str,
                 orig_abspath: Path,
                 bakfile: Path,
                 created: datetime,
                 modified: datetime,
                 restored: bool):
        self.original_file, \
            self.orig_abspath, \
            self.bakfile_loc, \
            self.date_created, \
            self.date_modified, \
            self.restored = \
            original, orig_abspath, bakfile, created, modified, restored

    def export(self):
        return((
            self.original_file,
            str(self.orig_abspath),
            str(self.bakfile_loc),
            self.date_created,
            self.date_modified,
            self.restored
        ))
