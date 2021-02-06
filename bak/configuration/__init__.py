# Straight file. Read config into variables. Probably no need for a data structure.
import os

from pathlib import Path
from re import sub

from config import Config, KeyNotFoundError

class BakConfiguration(dict):
# Establish default config values
    DEFAULT_VALUES = {
        'bakfile_location': 'null',
        'bak_database_location': 'null',
        'bak_diff_exec': 'null',
        'bak_list_relative_paths': 'false',
        'bak_list_colors': 'true'
    }
    cfg: Config
    config_file: str
    data_dir: Path
    config_dir: Path

    def __init__(self):
# Establish config file and database locations
        try:
            self.data_dir = Path(os.environ["XDG_DATA_HOME"]).expanduser().resolve()
        except KeyError:
            self.data_dir = Path("~/.local/share").expanduser().resolve()
        try:
            self.config_dir = Path(os.environ["XDG_CONFIG_HOME"]).expanduser().resolve()
        except KeyError:
            self.config_dir = Path("~/.config").expanduser().resolve()

        self.config_file = self.config_dir / 'bak.cfg'
        _cfg = Config(str(self.config_file))

        reload = False
        for cfg_value in self.DEFAULT_VALUES:
            if cfg_value not in _cfg.as_dict():
                with open(self.config_file, 'w') as _file:
                    _file.write(f"{cfg_value}: {self.DEFAULT_VALUES[cfg_value]}\n")
                    _file.close()
                    reload = True
        if reload:
            _cfg = Config(str(self.config_file))

        self.cfg = _cfg
        super().__init__()

    def __getitem__(self, item):
        return self.cfg[item]

    def __setitem__(self, item: str, value: str):
        if item not in self.DEFAULT_VALUES:
            err = f"{item} is not a valid bak setting. Valid settings include:\n"
            for setting in self.DEFAULT_VALUES:
                err += f"\n\t\t\t{setting}"
            raise KeyNotFoundError(err)
        else:
            if str(value).lower not in ('true', 'false'):
                if value is None:
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

bak_cfg = BakConfiguration()
