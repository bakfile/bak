import os
import sqlite3

from .bakfile import BakFile


class BakDBHandler():
    db_loc: str

    def __init__(self, db_loc: str):
        self.db_loc = db_loc

        if not os.path.exists(self.db_loc):
            db_conn = sqlite3.connect(self.db_loc)
            db_conn.execute("""
                            CREATE TABLE bakfiles (original_file,
                                                   bakfile,
                                                   date_created,
                                                   date_modified)
                            """)

    def add_bakfile_entry(self, bakfile: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                INSERT INTO bakfiles VALUES
                (:orig, :bakfile, :created, :modified)
                """, (bakfile.original_file,
                      bakfile.bakfile_loc,
                      bakfile.date_created,
                      bakfile.date_modified))
        pass

    def del_bakfile_entry():
        pass

    def update_bakfile_entry():
        pass

    def get_bakfile_entry():
        pass
