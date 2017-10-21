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
from nodepy.vendor import toml
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

import manifest from './lib/manifest'
import semver from './lib/semver'
import refstring from './lib/refstring'
import config from './lib/config'
import logger from './lib/logger'
import _install from './lib/install'
import {RegistryClient} from './lib/registry'
import PackageLifecycle from './lib/package-lifecycle'
import env, {PACKAGE_MANIFEST} from './lib/env'

__version__ = module.package.payload['package']['version']
VERSION = "{} [{}]".format(__version__, nodepy.main.VERSION)

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
       'Implies --private (use --no-private to prevent this behaviour).')
@click.option('--root', is_flag=True,
  help='Install into the Python\'s root directory (platform dependent). '
       'Implies --private (use --no-private to prevent this behaviour).')
@click.option('-I', '--ignore-installed', is_flag=True,
  help='Passed to Pip when installing Python dependencies. Ignores '
       'packages that are already installed in other directories.')
@click.option('-P', '--packagedir', default='.',
  help='The directory to read/write the nodepy-package.toml to or from.')
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
@click.option('-f', '--force', is_flag=True,
  help='Overwrite existing installed packages if it becomes necessary (eg. '
       'when a package link is broken, the package can no longer be found but '
       'its install directory still exists).')
@click.option('--private/--no-private', default=None,
  help='Install the dependencies of specified packages as private '
       'dependencies (resulting in a non-flat dependency tree by default). '
       'Applies only to the dependencies specified on the command-line and '
       'not recursively.')
@exit_with_return
def install(packages, upgrade, develop, global_, root, ignore_installed,
            packagedir, recursive, pip_separate_process, pip_use_target_option,
            info, dev, save, save_dev, save_ext, verbose, registry, force,
            private):
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

  if save and save_dev:
    print('Error: decide for either --save or --save-dev')
    return 1
  if save or save_dev:
    if not os.path.isfile(manifest_filename):
      print('Error: can not --save or --save-dev without "{}"'.format(PACKAGE_MANIFEST))
      print('  You can use `nodepy-pm init` to create a package manifest.')
      return 1
    with open(manifest_filename) as fp:
      manifest_data = toml.load(fp, _dict=collections.OrderedDict)

  # If not packages are specified, we install the dependencies of the
  # current package.
  if dev is None:
    dev = not packages

  # Initialize our installer utility.
  installer = get_installer(global_, root, upgrade, pip_separate_process,
      pip_use_target_option, recursive, verbose, registry=None)
  installer.ignore_installed = ignore_installed
  installer.force = force

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
      pip_packages.append(manifest.PythonDependency(pkg[1:]))
    elif pkg.startswith('git+'):
      if '@' in pkg:
        pkg, _, ref = pkg.rpartition('@')
      else:
        ref = None
      npy_packages.append(manifest.GitDependency(None, pkg[4:], ref, True, private))
    elif os.path.exists(pkg):
      npy_packages.append(manifest.PathDependency(None, pkg, develop, private))
    else:
      ref = refstring.parse(pkg)
      if ref.module or ref.member:
        print('Error: invalid dependency reference:', ref)
        return 1
      npy_packages.append(manifest.RegistryDependency(
        str(ref.package),
        ref.version or semver.Selector('*'),
        registry,
        private
      ))

  # Install Python dependencies.
  python_deps = {}
  python_additional = []
  for pkg in pip_packages:
    if (save or save_dev) and not pkg.req:
      return error("'{}' is not something we can install via NPPM with --save/--save-dev".format(pkg.spec))
    if pkg.req:
      python_deps[pkg.name] = pkg.specifier
    else:
      python_additional.append(str(pkg.spec))
  if (python_deps or python_additional):
    if not installer.install_python_dependencies(python_deps, args=python_additional):
      print('Installation failed')
      return 1

  # Install Node.py dependencies.
  installed_info = {}
  for pkg in npy_packages:
    if pkg.type == 'registry':
      registry = RegistryClient(pkg.registry, pkg.registry) if pkg.registry else None
      success, info = installer.install_from_registry(pkg.name, pkg.version, dev, registry)
      if success:
        assert info[0] == pkg.name, (info, pkg)
        installed_info[pkg] = info
    elif pkg.type == 'git':
      success, info = installer.install_from_git(pkg.url, pkg.ref, pkg.recursive, pkg.private)
      if success:
        installed_info[pkg] = info
    elif pkg.type == 'path':
      if os.path.isfile(pkg.path):
        if develop:
          print('Warning: Can not install in develop mode from archive "{}"'
            .format(pkg.path))
        success, mnf = installer.install_from_archive(pkg.path, dev=dev)
      else:
        success, mnf = installer.install_from_directory(pkg.path, develop, dev=dev)
      if success:
        installed_info[pkg] = (mnf.name, mnf.version)
    else:
      raise RuntimeError('unexpected pkg type:', pkg)
    if not success:
      error('Installation failed')

  installer.relink_pip_scripts()

  if (save or save_dev):
    deps = manifest_data.setdefault('dependencies', {})
  if (save or save_dev) and npy_packages:
    print('Saved dependencies:')
    data = deps.setdefault('nodepy', {})
    if save_dev: data = data.setdefault("cfg(development)", {})
    for pkg in npy_packages:
      info = installed_info[pkg]
      data[info[0]] = pkg.to_toml(name=info[0], version=info[1])
      print("  {}: {}".format(info[0], data[info[0]]))

  if (save or save_dev) and python_deps:
    data = deps.setdefault('python', {})
    if save_dev: data = data.setdefault("cfg(development)", {})
    print('Saved python dependencies:')
    for pkg_name, dist_info in installer.installed_python_libs.items():
      if not dist_info:
        print('warning: could not find .dist-info of module "{}"'.format(pkg_name))
        data[pkg_name] = ''
        print('  "{}": ""'.format(pkg_name))
      else:
        data[dist_info['name']] = '>=' + dist_info['version']
        print('  "{}": "{}"'.format(dist_info['name'], dist_info['version']))

  if save_ext and save_deps:
    extensions = manifest_data.setdefault('package', {}).setdefault('extensions', [])
    for ext_name in sorted(map(itemgetter(0), save_deps)):
      if ext_name not in extensions:
        extensions.append(ext_name)

  if (save or save_dev) and (npy_packages or python_deps):
    with open(manifest_filename, 'w') as fp:
      toml.dump(manifest_data, fp, preserve=True)

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

  location = get_install_location(global_, root)
  installer = _install.Installer(install_location=location)
  installer.uninstall(package)


@main.command()
@exit_with_return
def dist():
  """
  Create a .tar.gz distribution from the package.
  """

  PackageLifecycle([]).dist()


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
  #PackageLifecycle([]).upload(filename, user, password, force, dry, to)


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
  PackageLifecycle([]).publish(user, password, force, dry, to)


@main.command()
@click.argument('registry', required=False, default='default')
@click.option('--agree-tos', is_flag=True)
@click.option('--save', is_flag=True, help='Save username in configuration.')
@exit_with_return
def register(registry, agree_tos, save):
  """
  Register a new user on the package registry. Specify the registry to
  register to using the REGISTRY argument. Defaults to 'default'.
  """

  print('error: nodepy-pm register is currently not supported')
  return 1

  reg = RegistryClient.get(registry)
  print('Registry:', reg.name)
  print('URL:     ', reg.base_url)
  if not agree_tos:
    print()
    print('You have to agree to the Terms of Use before you can')
    print('register an account. Download and display terms now? [Y/n] ')
    reply = input().strip().lower() or 'yes'
    if reply not in ('yes', 'y'):
      print('Aborted.')
      return 0
    print()
    reg.terms() | Less(30)
    print()
    print('Do you agree to the above terms? [Y/n]')
    reply = input().strip().lower() or 'yes'
    if reply not in ('yes', 'y'):
      print('Aborted.')
      return 0

  username = input('Username? ')
  if len(username) < 3 or len(username) > 30:
    print('Username must be 3 or more characters.')
    return 1
  password = getpass.getpass('Password? ')
  if len(password) < 6 or len(password) > 64:
    print('Password must be 6 or more characters long.')
    return 1
  if getpass.getpass('Confirm Password? ') != password:
    print('Passwords do not match.')
    return 1
  email = input('E-Mail? ')
  # TODO: Validate email.
  if len(email) < 4:
    print('Invalid email.')
    return 1

  msg = reg.register(username, password, email)
  print(msg)

  if save:
    regconf['username'] = username
    config.save()
    print('Username saved in', config.filename)


@main.command()
@click.argument('directory', default='.')
@exit_with_return
def init(directory):
  """
  Initialize a new nodepy-package.toml.
  """

  filename = os.path.join(directory, PACKAGE_MANIFEST)
  if os.path.isfile(filename):
    print('error: "{}" already exists'.format(filename))
    return 1

  questions = [
    ('Package Name', 'name', None),
    ('Package Version', 'version', '1.0.0'),
    ('?Description', 'description', None),
    ('?Author (Name <Email>)', 'author', config.get('author')),
    ('?License', 'license', config.get('license')),
    ('?Main', 'main', None)
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

  reply = input('Do you want to use the require-import-syntax extension? [Y/n] ')
  if reply.lower() not in ('n', 'no', 'off'):
    results.setdefault('extensions', []).append('!require-import-syntax')
  else:
    reply = input('Do you want to use the require-unpack-syntax extension? [Y/n] ')
    if reply.lower() not in ('n', 'no', 'off'):
      results.setdefault('extensions', []).append('!require-unpack-syntax')

  with open(filename, 'w') as fp:
    toml.dump({'package': results}, fp, indent=2)
    fp.write('\n')


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
  Run a script that is specified in the nodepy-package.toml.
  """

  if not PackageLifecycle([], allow_no_manifest=True).run(script, args):
    error("no script '{}'".format(script))


if require.main == module:
  main()
