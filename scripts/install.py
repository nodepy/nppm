"""
Installs Node.py PM from source.
"""

if require.main != module:
  raise RuntimeError('must not be required')

import argparse
import codecs
import os
import nodepy.runtime
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


def read_proc(proc, encoding=None, prefix=''):
  reader = codecs.getreader(encoding or sys.getdefaultencoding())
  for line in reader(proc.stdout):
    print(prefix + line.rstrip('\n'))


def main():
  args = parser.parse_args()
  dirs = get_directories('global' if args.g else 'root')

  print("installing nodepy-pm Pip dependencies...")
  cmd = ['--prefix', dirs['pip_prefix']]
  for key, value in module.package.payload['python_dependencies'].items():
    cmd.append(key + value)

  with brewfix():
    # We use a subprocess here as otherwise we run into nodepy/nodepy#48,
    # "underlying buffer has been detached" when Pip uses the spinner or
    # download progress bar.
    proc = subprocess.Popen([sys.executable, '-m', 'pip', 'install'] + cmd,
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    read_proc(proc, prefix='  ')
    res = proc.wait()

  if res != 0:
    print('fatal: pip exited with return code {}'.format(res))
    sys.exit(res)

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
  if args.develop:
    cmd.append('--develop')
  cmd.append(str(module.directory.parent))

  # We need to set this option as otherwise the dependencies that we JUST
  # bootstrapped will be considered as already satsified, even though they
  # will not be after NPPM was installed in root or global level.
  cmd.append('--pip-separate-process')

  print("starting self-installation...")

  cmd = nodepy.runtime.exec_args + ['--python-path', dirs['pip_lib']] \
      + [str(module.directory.parent.joinpath('index'))] + cmd

  proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    stdin=subprocess.PIPE)
  read_proc(proc, prefix='  ')
  return proc.wait()


sys.exit(main())
