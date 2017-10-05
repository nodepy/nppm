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

import collections
import jsonschema
import os
import pip
import re
import six
import string
import toml

import semver from './semver'
import refstring from './refstring'

# Django's URL validation regex.
url_regex = re.compile(
  r'^(?:http|ftp)s?://' # http:// or https://
  r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
  r'localhost|' #localhost...
  r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
  r'(?::\d+)?' # optional port
  r'(?:/?|[/?]\S+)$', re.IGNORECASE)


class PythonDependency(object):
  type = 'python'

  def __init__(self, spec):
    self.spec = pip.req.InstallRequirement.from_line(spec)

  def __repr__(self):
    return 'PythonDependency(name={!r}, specifier={!r})'\
      .format(self.name, self.specifier)

  @property
  def name(self):
    return self.req.name

  @property
  def req(self):
    return self.spec.req

  @property
  def specifier(self):
    return str(self.spec.req.specifier)

class RegistryDependency(collections.namedtuple('C', 'name version registry private')):
  type = 'registry'

class GitDependency(collections.namedtuple('C', 'name url ref recursive private')):
  type = 'git'

class PathDependency(collections.namedtuple('C', 'name path link private')):
  type = 'path'


class PackageManifest(object):
  """
  This class describes a `nodepy-package.toml` package manifest in memory.
  Check out the #schema for a description of supported fields. Additional
  fields are only accepted when the name of that field also appears in the
  *engines* object, for example

  ```json
  {
    "engines": {
      "python": ">=3.4.1",
      "craftr": ">=3.1.0"
    },
    "craftr": {
      // ...
    }
  }
  ```

  These additional fields are stored in the #engine_props dictionary of the
  #PackageManifest.
  """

  schema = {
    "type": "object",
    "required": ["package"],
    "properties": {
      "package": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "version": {"type": "string"},
          "description": {"type": "string"},
          "repository": {"type": "string"},
          "license": {"type": "string"},
          "private": {"type": "boolean"},
          "resolve_root": {"type": "string"},
          "main": {"type": "string"},
        },
        "required": ["name", "version"]
      },
      "authors": {
        "type": "object",
        "additionalProperties": {
          "type": "object",
          "properties": {
            "email": {"type": "string"},
            "homepage": {"type": "string"}
          }
        }
      },
      "dependencies": {
        "type": "object",
        "properties": {
          "nodepy": {
            "type": "object",
            # TODO: These do not seem to be checked.
            "additionalProperties": {"anyOf": [
              {"type": "string"},
              {
                "type": "object",
                "properties": {
                  "git": {"type": "string"},
                  "ref": {"type": "string"},
                  "recursive": {"type": "boolean"},
                  "private": {"type": "boolean"}
                },
                "additionalProprties": False,
                "required": ["git"]
              },
              {
                "type": "object",
                "properties": {
                  "path": {"type": "string"},
                  "link": {"type": "boolean"},
                  "private": {"type": "boolean"}
                },
                "additionalProprties": False,
                "required": ["path"]
              },
              {
                "type": "object",
                "properties": {
                  "version": {"type": "string"},
                  "registry": {"type": "string"}
                },
                "additionalProprties": False,
                "required": ["version"]
              }
            ]}
          },
          "python": {
            "type": "object",
            "additionalProperties": {"type": "string"}
          }
        }
      },
      "scripts": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "bin": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "engines": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "extensions": {
        "type": "array",
        "items": {"type": "string"}
      },
      "dist": {
        "type": "object",
        "properties": {
          "include_files": {"type": "array", "items": {"type": "string"}},
          "exclude_files": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False
      }
    },
    "additionalProperties": {"type": "object"}
  }

  valid_characters = frozenset(string.ascii_lowercase + string.ascii_uppercase
                               + string.digits + '-._@/')

  def __init__(self, filename, directory, name, version, description=None,
      authors=None, license=None, dependencies=None, python_dependencies=None,
      scripts=None, bin=None, engines=None, engine_props=None, dist=None,
      repository=None, private=False, resolve_root=None, main=None,
      extensions=None):
    if len(name) < 2 or len(name) > 127:
      raise ValueError('packag name must be at least 2 and maximum 127 characters')
    if name.startswith('_') or name.startswith('.'):
      raise ValueError('package name can not start with _ or .')
    if set(name).difference(self.valid_characters):
      raise ValueError('package name contains invalid characters')
    refstring.parse_package(name)
    if repository is not None and not url_regex.match(repository):
      raise ValueError('invalid repository: "{}" is not a URL'.format(repository))
    self.filename = filename
    self.directory = directory
    self.name = name
    self.version = version
    self.authors = authors
    self.repository = repository
    self.description = description
    self.license = license
    self.dependencies = [] if dependencies is None else dependencies
    self.python_dependencies = {} if python_dependencies is None else python_dependencies
    self.scripts = {} if scripts is None else scripts
    self.bin = {} if bin is None else bin
    self.engine_props = {} if engine_props is None else engine_props
    self.dist = {} if dist is None else dist
    self.private = private
    self.resolve_root = resolve_root
    self.main = main
    self.extensions = extensions

  def __eq__(self, other):
    if isinstance(other, PackageManifest):
      return (self.filename, self.directory, self.name, self.version) == \
          (other.filename, other.directory, other.name, other.version)
    return False

  def __ne__(self, other):
    return not (self == other)

  def __repr__(self):
    return '<PackageManifest "{}">'.format(self.identifier)

  @property
  def identifier(self):
    return '{}@{}'.format(self.name, self.version)


class InvalidPackageManifest(Exception):
  """
  Raised from #parse() and #parse_dict() when the JSON data is does not
  match the #PackageManifest.schema and the additional constraints, or if
  the parsed file is not valid JSON.
  """

  def __init__(self, filename, cause):
    self.filename = filename
    self.cause = cause

  def __str__(self):
    if self.filename:
      return 'In file "{}": {}'.format(self.filename, self.cause)
    return str(self.cause)


def parse(filename, directory=None):
  """
  Parses a manifest file and returns it. If *directory* is #None, it will
  be derived from the *filename*.

  # Raises
  InvalidPackageManifest: If the `nodepy-package.toml` file is invalid.
  """

  if not directory:
    directory = os.path.dirname(filename) or '.'
  with open(filename, 'r') as fp:
    try:
      data = toml.load(fp)
    except json.JSONDecodeError as exc:
      raise InvalidPackageManifest(filename, exc)
    return parse_dict(data, filename, directory, copy=False)


def parse_dict(data, filename=None, directory=None, copy=True):
  """
  Takes a Python dictionary that represents a manifest from a JSON source
  and converts it to a #PackageManifest. The *filename* and *directory* can
  be set to #None depending on whether you want the respective members in
  the #PackageManifest to be #None.
  """

  try:
    jsonschema.validate(data, PackageManifest.schema)
  except jsonschema.ValidationError as exc:
    raise InvalidPackageManifest(filename, exc)

  if copy:
    data = data.copy()

  kwargs = {}

  # Validate the package name.
  try:
    refstring.parse_package(data['package']['name'])
    kwargs['name'] = data['package']['name']
  except ValueError as exc:
    raise InvalidPackageManifest(filename, exc)

  try:
    semver.Version(data['package']['version'])
    kwargs['version'] = data['package']['version']
  except ValueError as exc:
    raise InvalidPackageManifest(filename, exc)

  for k in 'private,resolve_root,main,extensions'.split(','):
    if k in data['package']:
      kwargs[k] = data['package'][k]

  dependencies = []
  for dep, sel in data.get('dependencies', {}).get('nodepy', {}).items():
    if isinstance(sel, str):
      sel = {'version': sel}
    if 'version' in sel:
      dep_data = RegistryDependency(dep, semver.Selector(sel['version']),
                                    sel.get('registry'),
                                    sel.get('private', False))
    elif 'git' in sel:
      dep_data = GitDependency(dep, sel['git'], sel.get('ref', None),
                               sel.get('recursive', True),
                               sel.get('private', False))
    elif 'path' in sel:
      dep_data = PathDependency(dep, sel['path'], sel.get('link', False),
                                sel.get('private', False))
    else:
      raise RuntimeError('jsonschema should\'ve validated this')
    dependencies.append(dep_data)
  kwargs['dependencies'] = dependencies
  kwargs['python_dependencies'] = data.get('dependencies', {}).get('python', {})

  engines = {}
  for eng, sel in data.get('engines', {}).items():
    engines[eng] = semver.Selector(sel)
  kwargs['engines'] = engines

  engine_props = {}
  for key in tuple(data.keys()):
    if key not in PackageManifest.schema['properties']:
      if key not in engines:
        msg = 'unexpected additional field: "{}"'
        raise InvalidPackageManifest(filename, msg.format(key))
      engine_props[key] = data.pop(key)
  kwargs['engine_props'] = engine_props

  for k in 'authors,description,repository,license,scripts,bin,dist'.split(','):
    if k in data:
      kwargs[k] = data[k]

  try:
    return PackageManifest(filename, directory, **kwargs)
  except ValueError as exc:
    six.raise_from(InvalidPackageManifest(filename, exc), exc)
