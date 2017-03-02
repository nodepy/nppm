# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import atexit
import json
import os
import pip
import setuptools
import sys

from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install

# These are the dependencies required by Node.py.
install_requires = {
  'click': '>=6.7',
  'localimport': '>=1.5.1',
  'six': '>=1.10.0'
}

# Add to these dependencies the ones needed by PPYM.
with open('ppym/package.json') as fp:
  install_requires.update(json.load(fp)['python-dependencies'])

# Join the dependencies into Pip install arguments.
install_requires = [a+b for a, b in install_requires.items()]


def readme():
  """
  This helper function uses the `pandoc` command to convert the `README.md`
  into a `README.rst` file, because we need the long_description in ReST
  format. This function will only generate the `README.rst` if any of the
  `setup dist...` commands are used, otherwise it will return an empty string
  or return the content of the already existing `README.rst` file.
  """

  if os.path.isfile('README.md') and any('dist' in x for x in sys.argv[1:]):
    if os.system('pandoc -s README.md -o README.rst') != 0:
      print('-----------------------------------------------------------------')
      print('WARNING: README.rst could not be generated, pandoc command failed')
      print('-----------------------------------------------------------------')
      if sys.stdout.isatty():
        input("Enter to continue... ")
    else:
      print("Generated README.rst with Pandoc")

  if os.path.isfile('README.rst'):
    with open('README.rst') as fp:
      return fp.read()
  return ''


def install_deps():
  """
  Installs the dependencies of Node.py and PPYM in a separate invokation
  of Pip. This is necessary so that we can install PPYM after Node.py, because
  older versions of Pip do not establish a proper dependency installation
  order.
  """

  cmd = ['install'] + install_requires
  print('Installing Node.py and PPYM dependencies in a separate context ...')
  print("  Command: pip {}".format(' '.join(cmd)))

  res = pip.main(cmd)
  if res != 0:
    print("  Error: 'pip install' returned {}".format(res))
    sys.exit(res)


def install_ppym(develop=False):
  """
  Executes the PPYM `bootstrap` module to install PPYM globally.
  """

  # TODO: The bootstrap install script must support a develop-mode installation.
  sys.path_importer_cache.clear()
  import nodepy
  try:
    nodepy.main(['ppym/bootstrap', '--no-bootstrap', '--install', '--global'])
  except SystemExit as exc:
    if exc.code != 0:
      raise


class develop(_develop):
  def run(self):
    install_deps()
    _develop.run(self)
    install_ppym(develop=True)


class install(_install):
  def run(self):
    install_deps()
    _install.run(self)
    install_ppym()


setuptools.setup(
  name = 'node.py',
  version = '0.0.8',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'Node.py Python runtime',
  long_description = readme(),
  url = 'https://github.com/nodepy/nodepy',
  py_modules = ['nodepy'],
  install_requires = install_requires,
  entry_points = {
    'console_scripts': [
      'node.py = nodepy:main'
    ]
  },
  cmdclass = {
    'develop': develop,
    'install': install
  }
)
