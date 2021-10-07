# Straight file. Read config into variables. Probably no need for a data structure.
import os

from pathlib import Path
from re import sub
from shutil import copy2
from sys import exit as _exit

from click import echo
from config import Config, KeyNotFoundError


class BakConfiguration(dict):
    # Establish default config values
    DEFAULT_VALUES = {
        'bakfile_location': 'null',
        'bak_database_location': 'null',
        'bak_diff_exec': 'null',
        'bak_list_relative_paths': 'false',
        'bak_list_colors': 'true',
        'fast_mode': 'false'
    }

    SETTABLE_VALUES = {
        'diff-exec': 'bak_diff_exec',
        'relative-paths': 'bak_list_relative_paths',
        'colors': 'bak_list_colors',
        'fast-mode': 'fast_mode'
    }
    cfg: Config
    config_file: str
    data_dir: Path
    config_dir: Path
    newline: str

    values: dict

    def __init__(self):

        self.values = {}
        self.newline = '\n'

        # Establish config file and database locations
        try:
            self.data_dir = Path(
                os.environ["XDG_DATA_HOME"]).expanduser().resolve()
        except KeyError:
            self.data_dir = Path("~/.local/share").expanduser().resolve()
        try:
            self.config_dir = Path(
                os.environ["XDG_CONFIG_HOME"]).expanduser().resolve()
        except KeyError:
            self.config_dir = Path("~/.config").expanduser().resolve()

        self.config_file = self.config_dir / 'bak.cfg'
        if not self.config_file.exists():
            try:
                copy2(Path('/etc/xdg/bak.cfg.default'), self.config_file)
            except FileNotFoundError:
                try:
                    copy2(self.config_dir / 'bak.cfg.default', self.config_file)
                except FileNotFoundError:
                    echo("Error: current user can't find bak's default config file! "
                        "Try copying \n\t~/.config/bak.cfg.default\nfrom your default user's ~"
                        " into this user's, or installing bak another way.")
                    _exit()
        _cfg = Config(str(self.config_file))

        reload = False
        for cfg_value in self.DEFAULT_VALUES.keys():
            if cfg_value not in _cfg.as_dict():
                with open(self.config_file, 'a') as _file:
                    _file.writelines(
                        f"{cfg_value}: {self.DEFAULT_VALUES[cfg_value]}\n")
                    _file.close()
                    reload = True
        if reload:
            _cfg = Config(str(self.config_file))

        self.cfg = _cfg

        super().__init__()

    def __getitem__(self, item):
        if item in self.SETTABLE_VALUES:
            item = self.SETTABLE_VALUES[item]
        return translate_config_value(self.cfg[item])

    def get(self, item, literal=True):
        """
        "Override" dict.get() in specific cases: use this to get the actual value of complex options,
        rather than whatever bak parses it into (like the actual command for `bak diff`, rather than
        an array of commands and arguments)

        Called by `bak config <value>`, just for good measure
        """
        if literal:
            # `and` would work, but why make the second check if this is a regular dict.get()?
            if item in self.SETTABLE_VALUES:
                return self.cfg[self.SETTABLE_VALUES[item]]
        return super().get(item)

    def __setitem__(self, item: str, value: str):
        if item in self.SETTABLE_VALUES:
            item = self.SETTABLE_VALUES[item]
        if item not in self.DEFAULT_VALUES:
            err = f"{item} is not a valid bak setting. Valid settings include:\n"
            for setting in self.DEFAULT_VALUES:
                err += f"\n\t\t\t{setting + self.newline}"
            raise KeyNotFoundError(err)
        if str(value).lower not in ('true', 'false'):
            if value is None or value.lower() == 'none':
                value = 'null'
            else:
                value = f"'{value}'"

            _config = None
            with open(self.config_file, 'r') as _file:
                _config = _file.read()
            _config = sub(f"{item}: .*", f"{item}: {value}", _config)
            with open(self.config_file, 'w') as _file:
                _file.write(_config)
            self.cfg = Config(str(self.config_file))


EQUIVALENT_VALUES = {'false': False,
                     'true': True,
                     'null': None}


def translate_config_value(val):
    if val in EQUIVALENT_VALUES.values():
        return val
    if val not in EQUIVALENT_VALUES:
        return val
    return EQUIVALENT_VALUES[val]


bak_cfg = BakConfiguration()
