from datetime import datetime


class BakFile():
    original_file: str
    orig_abspath: str
    bakfile_loc: str
    date_created: datetime
    date_modified: datetime

    def __init__(self,
                 original: str,
                 orig_abspath: str,
                 bakfile: str,
                 created: datetime,
                 modified: datetime):
        self.original_file, \
            self.orig_abspath, \
            self.bakfile_loc, \
            self.date_created, \
            self.date_modified = \
            original, orig_abspath, bakfile, created, modified

    def export(self):
        return((
            self.original_file,
            self.orig_abspath,
            self.bakfile_loc,
            self.date_created,
            self.date_modified
        ))
