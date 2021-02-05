# Straight file. Read config into variables. Probably no need for a data structure.
import os

from pathlib import Path

from config import Config

# Establish default config values
DEFAULT_VALUES = {
    'bakfile_location': 'null',
    'bak_database_location': 'null',
    'bak_diff_exec': 'null',
    'bak_list_relative_paths': 'false',
    'bak_list_colors': 'true'
}


# Establish config file and database locations
try:
    data_dir = Path(os.environ["XDG_DATA_HOME"]).expanduser().resolve()
except KeyError:
    data_dir = Path("~/.local/share").expanduser().resolve()
try:
    config_dir = Path(os.environ["XDG_CONFIG_HOME"]).expanduser().resolve()
except KeyError:
    config_dir = Path("~/.config").expanduser().resolve()

config_file = config_dir / 'bak.cfg'
bak_cfg = Config(str(config_file))

reload = False
for cfg_value in DEFAULT_VALUES:
    if cfg_value not in bak_cfg.as_dict():
        with open(config_file, 'w') as _file:
            _file.write(f"{cfg_value}: {DEFAULT_VALUES[cfg_value]}\n")
            _file.close()
            reload = True
if reload:
    bak_cfg = Config(str(config_file))