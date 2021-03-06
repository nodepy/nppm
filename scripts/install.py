# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Installs Node.py PM from source.
"""

from __future__ import print_function

if require.main != module:
  raise RuntimeError('must not be required')

import argparse
import codecs
import os
import nodepy.main, nodepy.runtime
import shutil
import subprocess
import sys

try:
  from shlex import quote
except ImportError:
  from pipes import quote

import brewfix from '../lib/brewfix'
import { get_directories } from '../lib/env'

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--local', action='store_true',
  help='Install Node.py PM locally instead.')
parser.add_argument('-g', '--global', dest='g', action='store_true',
  help='Install Node.py PM globally (in the user\'s home directory), rather '
       'than into the root of the Python installation. Note that this option '
       'has no effect inside a virtualenv.')
parser.add_argument('-U', '--upgrade', action='store_true',
  help='Overwrite the existing installation of Node.py PM.')
parser.add_argument('-e', '--develop', action='store_true',
  help='Install Node.py PM in develop mode, effectively linking it into the '
       'global package directory rather than copying it. Use this only if '
       'you want to update PM via Git or are developing it.')
parser.add_argument('-f', '--force', action='store_true')
parser.add_argument('--no-bootstrap', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true')


def read_proc(proc, encoding=None, prefix=''):
  reader = codecs.getreader(encoding or sys.getdefaultencoding())
  for line in reader(proc.stdout):
    print(prefix + line.rstrip('\n'))


def bootstrap_pip_deps(dirs, location, verbose=False):
  print('Bootstrapping Python dependencies ...')
  cmd = [sys.executable, '-m', 'pip', 'install']
  if location == 'local':
    cmd += ['--prefix', dirs['pip_prefix'], '--ignore-installed']
  elif location == 'global':
    cmd += ['--user']
  elif location != 'root':
    assert False, repr(location)
  if verbose:
    cmd.append('--verbose')
  for key, value in module.package.payload['pip_dependencies'].items():
    cmd.append(key + value)
  print('$', ' '.join(map(quote, cmd)))
  print()

  with brewfix():
    # We use a subprocess here as otherwise we run into nodepy/nodepy#48,
    # "underlying buffer has been detached" when Pip uses the spinner or
    # download progress bar.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    read_proc(proc, prefix='  ')
    res = proc.wait()

  if res != 0:
    print('fatal: pip exited with return code {}'.format(res))
    sys.exit(res)


def main():
  args = parser.parse_args()
  if args.local and args.g:
    print('fatal: -l, --local and -g, --global can not be mixed')
    return 1

  location = 'local' if args.local else ('global' if args.g else 'root')
  dirs = get_directories(location)

  if not args.no_bootstrap:
    bootstrap_pip_deps(dirs, location, args.verbose)

  # If we're not installing into the root location, the Pip installed
  # libraries will not be automatically found by the Node.py runtime, yet
  # (due to the sources not yet being copied to the install directory).
  sys.path.append(dirs['pip_lib'])

  # This is necessary on Python 2.7 (and possibly other versions) as
  # otherwise importing the newly installed Python modules will fail.
  sys.path_importer_cache.clear()

  # Let Node.py PM install itself.
  cmd = ['install']
  if args.upgrade:
    cmd.append('--upgrade')
  if args.g:
    cmd.append('--global')
  elif not args.local:
    cmd.append('--root')
  if args.develop:
    cmd.append('--develop')
  if args.force:
    cmd.append('--force')
  cmd.append(str(module.directory.parent))

  # We need to set this option as otherwise the dependencies that we JUST
  # bootstrapped will be considered as already satsified, even though they
  # will not be after NPPM was installed in root or global level.
  cmd.append('--pip-separate-process')

  print()
  print("Self-installing nppm ...")
  print('$', ' '.join(map(quote, ['nppm'] + cmd)))
  print()

  prefix_cmd = list(nodepy.runtime.exec_args)
  if args.local:
    # Adding this path when the global or user-local is used will cause
    # localimport>2 to disable all modules already imported and found in that
    # system or user library path. This will cause issues like "nodepy.utils"
    # loosing its "machinery" member (if nodepy is installed in that path).
    prefix_cmd += ['--python-path', dirs['pip_lib']]
  prefix_cmd += [str(module.directory.parent.joinpath('index'))]

  proc = subprocess.Popen(prefix_cmd + cmd, stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
  read_proc(proc, prefix='  ')
  return proc.wait()


sys.exit(main())
