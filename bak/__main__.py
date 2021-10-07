from os import geteuid
from sys import exit as exitapp

from click import confirm

def run_bak():
    if geteuid() == 0:
        if not confirm("WARNING: You are running bak as root! "
                    "This will create separate config and bakfiles for root, "
                    "and is probably not what you're trying to do.\n\n"
                    "If bak needs superuser privileges to copy or overwrite a file, "
                    "it will invoke sudo cp by itself.\n\n"
                    "Are you sure you want to continue as root?"):
            exitapp()

    from bak.cli import bak as _bak
    _bak()

if __name__ == "__main__":
    run_bak()
