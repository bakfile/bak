from setuptools import setup, find_packages

require = ['click==7.1.2',
           'click-default-group==1.2.2',
           'rich==9.1.0',
           'ydiff==1.2']

setup(name='bak',
      version='0.0.1a',
      description='the .bak manager',
      author='ChanceNCounter',
      author_email='ChanceNCounter@icloud.com',
      packages=find_packages(),
      include_package_data=True,
      install_requires=require,
      entry_points='''
      [console_scripts]
      bak=bak.__main__:bak''',
      license='MIT License',
      url='https://github.com/bakfile/bak')
