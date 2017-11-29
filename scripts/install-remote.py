"""
This script is linked from the nodepy/nodepy-pm@master branch under
`https://nodepy.org/install-pm` and can be used to install PM from the
internet.

If you want to install PM directly from source, use the `install.py`
script instead.
"""

from __future__ import print_function

if require.main != module:
  raise RuntimeError('must not be required')

import argparse
import codecs
import contextlib
import errno
import io
import json
import operator
import os
import nodepy.runtime
import shutil
import subprocess
import sys
import tempfile as _tempfile
import zipfile

try:
  from shlex import quote
except ImportError:
  from pipes import quote

try:
  from urllib.request import urlopen
except ImportError:
  from urllib2 import urlopen

parser = argparse.ArgumentParser()
parser.add_argument('ref', nargs='?')
parser.add_argument('-l', '--local', action='store_true',
  help='Install Node.py PM locally instead.')
parser.add_argument('-g', '--global', dest='g', action='store_true',
  help='Install Node.py PM globally (in the user\'s home directory), rather '
       'than into the root of the Python installation. Note that this option '
       'has no effect inside a virtualenv.')
parser.add_argument('-U', '--upgrade', action='store_true',
  help='Overwrite the existing installation of Node.py PM.')
parser.add_argument('-f', '--force', action='store_true')
parser.add_argument('--no-bootstrap', action='store_true')


@contextlib.contextmanager
def tempfile(suffix='', prefix='tmp', dir=None, text=False):
  """
  Creates a temporary file that can be closed without instantly deleting. This
  is useful for writing a temporary file that will then be read by a different
  application.

  Yields a tuple of the file object and its filename.
  """

  fd, filename = _tempfile.mkstemp(suffix, prefix, dir, text)
  try:
    yield os.fdopen(fd, 'w' if text else 'wb'), filename
  finally:
    try:
      os.close(fd)
    except OSError as exc:
      if exc.errno != errno.EBADF:
        raise


@contextlib.contextmanager
def tempdir(suffix='', prefix='', dir=None, ignore_errors_on_delete=False):
  """
  Creates a temporary directory.
  """

  dirname = _tempfile.mkdtemp(suffix, prefix, dir)
  try:
    yield dirname
  finally:
    shutil.rmtree(dirname, ignore_errors_on_delete)


def gh_api(endpoint, raw=False):
  url = 'https://api.github.com/{}'.format(endpoint)
  response = urlopen(url)
  return response if raw else json.load(codecs.getreader('utf8')(response))


def main():
  args = parser.parse_args()

  if not args.ref:
    # Get a list of all version tags.
    versions = []
    for tag in gh_api('repos/nodepy/nodepy-pm/tags'):
      try:
        version = tuple(map(int, tag['name'].lstrip('v').split('.')))
      except ValueError:
        pass
      else:
        versions.append((version, tag))
    if not versions:
      print('fatal: no tags look like versions, try adding a Git ref to\n'
            '       the command (eg. master).')
      return 1

    versions.sort(key=operator.itemgetter(0))
    args.ref = versions[-1][1]['name']

  print('downloading zipball for "{}"...'.format(args.ref))
  archive = gh_api('repos/nodepy/nodepy-pm/zipball/{}'.format(args.ref), raw=True)
  zipf = zipfile.ZipFile(io.BytesIO(archive.read()))

  print('unpacking zipball...')
  with tempdir(suffix='nodepy-pm-{}'.format(args.ref)) as dirname:
    zipf.extractall(dirname)
    installer = next((x for x in zipf.namelist() if x.endswith('scripts/install.py')), None)
    if not installer:
      print('fatal: scripts/install.py not found in downloaded archive.')
      return 1
    installer = os.path.join(dirname, installer)
    cmd = nodepy.runtime.exec_args + [installer]
    cmd += ['--local'] if args.local else []
    cmd += ['--global'] if args.g else []
    cmd += ['--force'] if args.force else []
    cmd += ['--upgrade'] if args.upgrade else []
    cmd += ['--no-bootstrap'] if args.no_bootstrap else []
    print('$', ' '.join(map(quote, cmd)))
    return subprocess.call(cmd)


sys.exit(main())
