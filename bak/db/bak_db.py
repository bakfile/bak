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
                 """, bakfile.export())

    def del_bakfile_entry(self, filename):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE original_file=:orig
                """, (filename,))

    def update_bakfile_entry(self, bakfile: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE original_file=:orig
                """, (bakfile.original_file,))
        self.add_bakfile_entry(bakfile)

    # TODO handle disambiguation
    def get_bakfile_entry(self, filename):
        with sqlite3.connect(self.db_loc) as db_conn:
            c = db_conn.execute(
                """
                    SELECT * FROM bakfiles WHERE original_file=:orig
                """, (filename,))
            return BakFile(*c.fetchone())
