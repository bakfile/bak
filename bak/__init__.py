import os
import config
from shutil import copy2

try:
    config_dir = os.environ["XDG_CONFIG_HOME"]
except KeyError:
    config_dir = os.path.expanduser("~/.config")

config_file = os.path.join(config_dir, 'bak.cfg')

if not os.path.exists(config_file):
    copy2('default.cfg', config_file)
