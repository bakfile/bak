import os
import sqlite3
from pathlib import Path

from .bakfile import BakFile


class BakDBHandler:
    db_loc: Path

    def __init__(self, db_loc: Path):
        self.db_loc = db_loc

        if not self.db_loc.exists():
            db_conn = sqlite3.connect(self.db_loc)
            db_conn.execute("""
                            CREATE TABLE bakfiles (original_file,
                                                   original_abspath,
                                                   bakfile,
                                                   date_created,
                                                   date_modified,
                                                   restored)
                            """)
            db_conn.commit()

    def create_bakfile_entry(self, bakfile_obj: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                INSERT INTO bakfiles VALUES
                (:orig, :abs, :bakfile, :created, :modified, :restored)
                 """, bakfile_obj.export())
            db_conn.commit()

    def del_bakfile_entry(self, bak_entry: BakFile):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE original_abspath=:orig
                """, (bak_entry.orig_abspath,))
            db_conn.commit()

    def update_bakfile_entry(self,
                             old_bakfile: BakFile,
                             new_bakfile: (BakFile, None) = None):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                DELETE FROM bakfiles WHERE bakfile=:bakfile_loc
                """, (old_bakfile.bakfile_loc,))
            db_conn.commit()
            if new_bakfile:
                os.remove(old_bakfile.bakfile_loc)
                self.create_bakfile_entry(new_bakfile)
            else:
                self.create_bakfile_entry(old_bakfile)
                self.set_restored_flag(old_bakfile, False)

    def set_restored_flag(self, bakfile, status=True):
        with sqlite3.connect(self.db_loc) as db_conn:
            db_conn.execute(
                """
                UPDATE bakfiles SET restored=:status WHERE bakfile=:bakfile_loc
                """, (status, bakfile.bakfile_loc)
            )

    # TODO handle disambiguation
    def get_bakfile_entries(self, filename):
        with sqlite3.connect(self.db_loc) as db_conn:
            cursor = db_conn.execute(
                """
                    SELECT * FROM bakfiles WHERE original_abspath=:orig ORDER BY date_created
                """, (os.path.abspath(os.path.expanduser(filename)),))
            return [BakFile(*entry) for entry in cursor.fetchall()] or None

    def get_all_entries(self):
        with sqlite3.connect(self.db_loc) as db_conn:
            cursor = db_conn.execute("SELECT * FROM bakfiles ORDER BY original_abspath, date_created")
            return [BakFile(*entry) for entry in cursor.fetchall()]
