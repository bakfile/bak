from datetime import datetime


class BakFile():
    original_file: str
    bakfile_loc: str
    date_created: datetime
    date_modified: datetime

    def __init__(self,
                 original: str,
                 bakfile: str,
                 created: datetime,
                 modified: datetime):
        self.original_file, \
            self.bakfile_loc, \
            self.date_created, \
            self.date_modified = \
            original, bakfile, created, modified

    def export(self):
        return((
            self.original_file,
            self.bakfile_loc,
            self.date_created,
            self.date_modified
        ))
