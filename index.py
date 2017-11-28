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

from __future__ import print_function
from nodepy.utils import json
from operator import itemgetter
from six.moves import input

import click
import collections
import functools
import getpass
import nodepy
import os
import pip.req
import six
import sys

import manifest, {load as load_manifest} from './lib/manifest'
import semver from './lib/semver'
import refstring from './lib/refstring'
import logger from './lib/logger'
import _install from './lib/install'
import {RegistryClient} from './lib/registry'
import PackageLifecycle from './lib/package-lifecycle'
import env, {PACKAGE_MANIFEST} from './lib/env'

def _read_gitref():
  gitref = module.directory.joinpath('.gitref')
  if gitref.is_file():
    with gitref.open('r') as fp:
      return fp.read().strip()
  return '<unknown-gitref>'


__version__ = module.package.payload['version']
VERSION = "{} ({}) [{}]".format(__version__, _read_gitref(), nodepy.main.VERSION)





class Less(object):
  # http://stackoverflow.com/a/3306399/791713
  def __init__(self, num_lines):
    self.num_lines = num_lines
  def __ror__(self, other):
    s = six.text_type(other).split("\n")
    for i in range(0, len(s), self.num_lines):
      print("\n".join(s[i:i+self.num_lines]))
      input("Press <Enter> for more")


def get_install_location(global_, root):
  if global_ and root:
    error('-g,--global and --root can not be used together')
  elif global_:
    if env.is_virtualenv():
      print('Note: detected virtual environment, upgrading -g,--global to --root')
      return 'root'
    return 'global'
  elif root:
    return 'root'
  else:
    return 'local'


def get_installer(global_, root, upgrade, pip_separate_process,
                  pip_use_target_option, recursive, verbose=False,
                  registry=None):
  location = get_install_location(global_, root)
  return _install.Installer(
    registry=registry,
    upgrade=upgrade,
    install_location=location,
    pip_separate_process=pip_separate_process,
    pip_use_target_option=pip_use_target_option,
    recursive=recursive,
    verbose=verbose
  )


def error(message, code=1):
  print('Error:', message)
  sys.exit(code)


def exit_with_return(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    res = func(*args, **kwargs)
    sys.exit(res)
  return wrapper


def report_manifest_issues(filename, payload):
  for field in manifest.validate(payload):
    name = field.cfg or ''
    if name and name[-1] != '.':
      name += '>'
    name += field.name
    for msg in field.warnings:
      print('WARNING: {}@{} {}'.format(filename, name, msg))
    for msg in field.errors:
      print('CRITICAL: {}@{} {}'.format(filename, name, msg))


@click.group(help=VERSION)
def main():
  pass


@main.command()
def version():
  """
  Print the nppm and Node.py version.
  """

  print(VERSION)


@main.command(help='''
  Install Node.py and/or Python packages. If no packages are specified, the
  dependencies of the current Node.py package are installed and the package
  is installed locally in develop mode (as a link).

  To specify a Python package, prefix the package name with a tilde (~)
  character. Example:

  \b
    nodepy-pm install --save @nodepy/werkzeug-reloader-patch ~Flask
  ''')
@click.argument('packages', nargs=-1)
@click.option('-U', '--upgrade', is_flag=True)
@click.option('-e', '--develop', is_flag=True,
  help='Install the specified packages in develop mode (as link). Applies '
       'only to packages installed from a local directory.')
@click.option('-g', '--global/--local', 'global_', is_flag=True,
  help='Install into the user\'s home directory (platform dependent). '
       'Implies --internal (use --no-internal to prevent this behaviour).')
@click.option('--root', is_flag=True,
  help='Install into the Python\'s root directory (platform dependent). '
       'Implies --internal (use --no-internal to prevent this behaviour).')
@click.option('-I', '--ignore-installed', is_flag=True,
  help='Passed to Pip when installing Python dependencies. Ignores '
       'packages that are already installed in other directories.')
@click.option('-P', '--packagedir', default='.',
  help='The directory to read/write the nodepy.json to or from.')
@click.option('-R', '--recursive', is_flag=True,
  help='Satisfy dependencies of already satisfied dependencies.')
@click.option('--pip-separate-process', is_flag=True)
@click.option('--pip-use-target-option', is_flag=True,
  help='Use --target instead of --prefix when installing dependencies '
       'via Pip. This is to circumvent a Bug in Pip where installing with '
       '--prefix fails. See nodepy/ppym#9.')
@click.option('--info', is_flag=True)
@click.option('--dev/--production', 'dev', default=None,
  help='Specify whether to install development dependencies or not. The '
       'default value depends on the installation type (--dev when no packages '
       'are specified, otherwise determined from the NODEPY_ENV variable).')
@click.option('--save', is_flag=True,
  help='Save the installed dependencies into the "dependencies" or '
       '"python-dependencies" field, respectively.')
@click.option('--save-dev', is_flag=True,
  help='Save the installed dependencies into the "dev-dependencies" or '
       '"dev-python-dependencies" field, respectively.')
@click.option('--save-ext', is_flag=True,
  help='Save the installed dependencies into the "extensions" field. '
       'Installed Python modules are ignored for this one. Implies --save.')
@click.option('-v', '--verbose', is_flag=True)
@click.option('-F', '--from', 'registry',
  help='Specify explicitly which registry to look for Node.py packages '
       'with. If not specified, all registries will be checked unless they '
       'specify the `default=false` option.')
@click.option('--internal/--no-internal', default=None,
  help='Install the dependencies of specified packages as internal '
       'dependencies (resulting in a non-flat dependency tree by default). '
       'Applies only to the dependencies specified on the command-line and '
       'not recursively.')
@click.option('--pure', is_flag=True, default=False,
  help='Install the packages pure, do not install their scripts.')
@exit_with_return
def install(packages, upgrade, develop, global_, root, ignore_installed,
            packagedir, recursive, pip_separate_process, pip_use_target_option,
            info, dev, save, save_dev, save_ext, verbose, registry, internal,
            pure):
  """
  Installs one or more Node.Py or Pip packages.
  """

  # FIXME: Validate registry URL as HTTPS.

  manifest_filename = os.path.join(packagedir, PACKAGE_MANIFEST)

  if save_ext:
    if save_dev:
      print('Warning: --save-ext should not be combined with --save-dev')
      print('  Extensions must be available during runtime.')
    else:
      # Implying --save
      save = True

  if (global_ or root) and internal is None:
    print('Note: implying --internal due to {}.'.format('--global' if global_ else '--root'))
    internal = True

  if save and save_dev:
    print('Error: decide for either --save or --save-dev')
    return 1

  if os.path.isfile(manifest_filename):
    manifest_data = load_manifest(manifest_filename)
    report_manifest_issues(manifest_filename, manifest_data)
  else:
    manifest_data = None

  if (save or save_dev or save_ext) and manifest_data is None:
    print('Error: can not --save, --save-dev or --save-ext without "{}"'.format(PACKAGE_MANIFEST))
    print('  You can use `nodepypm init` to create a package manifest.')
    return 1

  # If not packages are specified, we install the dependencies of the
  # current package.
  if dev is None:
    dev = not packages

  # Initialize our installer utility.
  installer = get_installer(global_, root, upgrade, pip_separate_process,
      pip_use_target_option, recursive, verbose, registry=None)
  installer.ignore_installed = ignore_installed

  if info:
    for key in sorted(installer.dirs):
      print('{}: {}'.format(key, installer.dirs[key]))
    return 0

  # Install dependencies of the current packages.
  if not packages:
    installer.upgrade = True
    success, _manifest = installer.install_from_directory('.', develop=True, dev=dev)
    if not success:
      return 1
    installer.relink_pip_scripts()
    return 0

  # Parse the packages specified on the command-line.
  pip_packages = []
  npy_packages = []
  for pkg in packages:
    if pkg.startswith('~'):
      pip_packages.append(manifest.PipRequirement.from_line(pkg[1:]))
    else:
      req = manifest.Requirement.from_line(pkg, expect_name=True)
      req.inherit_values(link=develop, registry=registry, internal=internal, pure=pure)
      npy_packages.append(req)

  # Install Python dependencies.
  python_deps = {}
  python_additional = []
  for spec in pip_packages:
    if (save or save_dev) and not spec.req:
      return error("'{}' is not something we can install via NPPM with --save/--save-dev".format(pkg.spec))
    if spec.req:
      python_deps[spec.name] = str(spec.specifier)
    else:
      python_additional.append(str(spec))
  if (python_deps or python_additional):
    if not installer.install_python_dependencies(python_deps, args=python_additional):
      print('Installation failed')
      return 1

  # Install Node.py dependencies.
  req_names = {}
  for req in npy_packages:
    success, info = installer.install_from_requirement(req)
    if not success:
      error('Installation failed')
    if req.name:
      assert info[0] == pkg.name, (info, pkg)
    req_names[req] = info[0]
    if req.type == 'registry':
      req.selector = semver.Selector('~' + str(info[1]))

  installer.relink_pip_scripts()


  if save_dev:
    if 'cfg(dev)' in manifest_data:
      deps = lambda: manifest_data['cfg(dev)'].setdefault('dependencies', {})
      pip_deps = lambda: manifest_data['cfg(dev)'].setdefault('pip_dependencies', {})
    else:
      deps = lambda: manifest_data.setdefault('cfg(dev).dependencies', {})
      pip_deps = lambda: manifest_data.setdefault('cfg(dev).pip_dependencies', {})
  elif save:
    deps = lambda: manifest_data.setdefault('dependencies', {})
    pip_deps = lambda: manifest_data.setdefault('pip_dependencies', {})

  if (save or save_dev) and npy_packages:
    print('Saved dependencies:')
    for req in npy_packages:
      deps()[req_names[req]] = str(req)
      print("  {}: {}".format(req_names[req], str(req)))

  if (save or save_dev) and python_deps:
    for pkg_name, dist_info in installer.installed_python_libs.items():
      if not dist_info:
        print('warning: could not find .dist-info of module "{}"'.format(pkg_name))
        pip_deps()[pkg_name] = ''
        print('  "{}": ""'.format(pkg_name))
      else:
        pip_deps()[dist_info['name']] = '>=' + dist_info['version']
        print('  "{}": "{}"'.format(dist_info['name'], dist_info['version']))

  if save_ext and npy_packages:
    extensions = manifest_data.setdefault('extensions', [])
    for req_name in sorted(req_names.values()):
      if req_name not in extensions:
        extensions.append(req_name)

  if (save or save_dev or save_ext) and (npy_packages or python_deps):
    with open(manifest_filename, 'w') as fp:
      json.dump(manifest_data, fp, indent=2)

  print()
  return 0


@main.command()
@click.argument('package')
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
@exit_with_return
def uninstall(package, global_, root):
  """
  Uninstall a module with the specified name from the local package directory.
  To uninstall the module from the global package directory, specify
  -g/--global.
  """

  if package == '.' or os.path.exists(package):
    filename = os.path.join(package, PACKAGE_MANIFEST)
    manifest = load_manifest(filename)
    report_manifest_issues(filename, manifest)
    package = manifest['name']

  location = get_install_location(global_, root)
  installer = _install.Installer(install_location=location)
  installer.uninstall(package)


@main.command()
@exit_with_return
def dist():
  """
  Create a .tar.gz distribution from the package.
  """

  PackageLifecycle().dist()


@main.command()
@click.argument('filename')
@click.option('-f', '--force', is_flag=True)
@click.option('-u', '--user')
@click.option('-p', '--password')
@click.option('--to', help='Registry to publish to.')
@click.option('--dry', is_flag=True)
@exit_with_return
def upload(filename, force, user, password, dry, to):
  """
  Upload a file to the current version to the registry. If the package does
  not already exist on the registry, it will be added to your account
  automatically. The first package that is uploaded must be the package
  source distribution that can be created with 'nppm dist'.
  """

  print('error: nodepy-pm upload is currently not supported')
  return 1
  #PackageLifecycle().upload(filename, user, password, force, dry, to)


@main.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-u', '--user')
@click.option('-p', '--password')
@click.option('--to', help='Registry to publish to.')
@click.option('--dry', is_flag=True)
@exit_with_return
def publish(force, user, password, dry, to):
  """
  Combination of `nppm dist` and `nppm upload`. Also invokes the `pre-publish`
  and `post-publish` scripts.
  """

  print('error: nodepy-pm publish is currently not supported')
  return 1
  #PackageLifecycle().publish(user, password, force, dry, to)


@main.command()
@click.argument('directory', default='.')
@exit_with_return
def init(directory):
  """
  Initialize a new nodepy.json manifest.
  """

  filename = os.path.join(directory, PACKAGE_MANIFEST)
  if os.path.isfile(filename):
    print('error: "{}" already exists'.format(filename))
    return 1

  questions = [
    ('Package Name', 'name', None),
    ('Package Version', 'version', '1.0.0'),
    ('?Description', 'description', None),
    ('?Author E-Mail(s)', 'authors', None),
    ('?License', 'license', 'MIT')
  ]

  results = collections.OrderedDict()
  for qu in questions:
    msg = qu[0]
    opt = msg.startswith('?')
    if opt: msg = msg[1:]
    if qu[2]:
      msg += ' [{}]'.format(qu[2])
    while True:
      reply = input(msg + '? ').strip() or qu[2]
      if reply or opt: break
    if reply and reply != '-':
      results[qu[1]] = reply

  if 'author' in results:
    results['authors'] = [results.pop('author')]

  print('This is your new nodepy.json:')
  print()
  result = json.dumps(results, indent=2)
  print(result)
  print()
  reply = input('Are you okay with this? [Y/n] ').strip().lower()
  if reply not in ('', 'y', 'yes', 'ok'):
    return

  with open(filename, 'w') as fp:
    fp.write(result)


@main.command()
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
@click.option('--pip', is_flag=True)
@exit_with_return
def bin(global_, root, pip):
  """
  Print the path to the bin directory.
  """

  location = get_install_location(global_, root)
  dirs = env.get_directories(location)
  if pip:
    print(dirs['pip_bin'])
  else:
    print(dirs['bin'])


@main.command()
@click.option('-g', '--global', 'global_', is_flag=True)
@click.option('--root', is_flag=True)
def dirs(global_, root):
  """
  Print install target directories.
  """

  location = get_install_location(global_, root)
  dirs = env.get_directories(location)
  print('Packages:\t', dirs['packages'])
  print('Bin:\t\t', dirs['bin'])
  print('Pip Prefix:\t', dirs['pip_prefix'])
  print('Pip Bin:\t', dirs['pip_bin'])
  print('Pip Lib:\t', dirs['pip_lib'])


@main.command(context_settings={'ignore_unknown_options': True})
@click.argument('script')
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@exit_with_return
def run(script, args):
  """
  Run a script that is specified in the nodepy.json manifest.
  """

  if not PackageLifecycle(allow_no_manifest=True).run(script, args):
    error("no script '{}'".format(script))


if require.main == module:
  main()
