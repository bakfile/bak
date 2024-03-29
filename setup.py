import os
from shutil import copy2
from setuptools import setup, find_packages

from bak import BAK_VERSION

require = ['click==7.1.2',
           'click-default-group==1.2.2',
           'config==0.5.0',
           'rich==9.1.0']

setup(name='bak',
      version=BAK_VERSION,
      description='the .bak manager',
      author='ChanceNCounter',
      author_email='ChanceNCounter@icloud.com',
      packages=find_packages(),
      include_package_data=True,
      install_requires=require,
      entry_points='''
      [console_scripts]
      bak=bak.__main__:run_bak''',
      license='MIT License',
      url='https://github.com/bakfile/bak')

# Ensure config exists
try:
    config_dir = os.environ["XDG_CONFIG_HOME"]
except KeyError:
    config_dir = os.path.expanduser("~/.config")

config_file = os.path.join(config_dir, 'bak.cfg')
default_config = os.path.join(config_dir, 'bak.cfg.default')
system_default_config = os.path.join('/etc/xdg', 'bak.cfg.default')

if not os.path.exists(config_file):
    copy2('bak/default.cfg', config_file)

if not os.path.exists(default_config):
    copy2('bak/default.cfg', default_config) 
    try:
        copy2('bak/default.cfg', system_default_config)
    except PermissionError:
        pass
