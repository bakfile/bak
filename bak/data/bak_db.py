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
                                                   original_abspath,
                                                   bakfile,
                                                   date_created,
                                                   date_modified)
                            """)
            db_conn.commit()

    def create_bakfile_entry(self, bakfile_obj: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                INSERT INTO bakfiles VALUES
                (:orig, :abs, :bakfile, :created, :modified)
                 """, bakfile_obj.export())
            db_conn.commit()
            os.popen(f'cp {bakfile_obj.original_file} '
                     f'{bakfile_obj.bakfile_loc}')

    def del_bakfile_entry(self, filename):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE original_file=:orig
                """, (filename,))

    def update_bakfile_entry(self, bakfile: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT bakfile FROM bakfiles WHERE original_abspath=:orig",
                (bakfile.orig_abspath,))
            old_bakfile = cursor.fetchone()[0]
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE original_file=:orig
                """, (bakfile.original_file,))
        os.popen(f'rm {old_bakfile}')
        self.create_bakfile_entry(bakfile)

    # TODO handle disambiguation
    def get_bakfile_entry(self, filename):
        with sqlite3.connect(self.db_loc) as db_conn:
            c = db_conn.execute(
                """
                    SELECT * FROM bakfiles WHERE original_file=:orig
                """, (filename,))
            return BakFile(*c.fetchone())
