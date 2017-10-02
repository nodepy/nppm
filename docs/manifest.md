+++
title = "nodepy-package.toml"
+++

Node.py package manifest specification.

```python
manifest = require('@nodepy/nodepy-pm/lib/manifest')
try:
  m = manifest.parse('nodepy-package.toml')
except (FileNotFoundError, manifest.InvalidPackageManifest) as exc:
  print(exc)
  m = None
```

  [SemVer]: http://semver.org/

## Specification

### `[package]`

#### `name`

*Required.* The name of the package. This may be a scope identifier
of the format `@scope/package-name`, or simply `package-name`. Allowed
characters for the scope and package name are digits, ASCII letters and `-_.`.

```toml
name = "@scope-name/package-name"
```

#### `version`

*Required.* A [SemVer] of the package's version.

```toml
version = "0.0.1-security"
```

#### `repository`

*Optional.* URL to the source code repository where the package is developed.
If specified, the URL must be valid.

```json
{ "repository": "https://github.com/nodepy/nodepy" }
```

#### `license`

*Required when publishing a package on the registry.* The license of the
package source code.

```json
{ "license": "MIT" }
```

#### `resolve_root`

*Optional.* A directory relative to the `package.json` that is considered the
root directory when importing modules from this package. Should be used if you
want to keep all source files under a sub-directory of your package.

```json
{
  "resolve_root": "lib/"
}
```


### `private`

*Optional.* Prevent publication of the package with `nppm publish`. This is used
for packages that want to take advantage of the nppm dependency management but
are not actuall supposed to be placed into the public registry. An example
of this would be a package that generates the documentation of another project.

```toml
private = true
```

### `main`

*Optional.* This field describes the name of the module to load when your
package is required by another module. If this field is not specified, the
`Context._index_files` are tried instead (which are `index` and `__init__`).

```toml
main = "./index.py"
```

### `extensions`

*Optional.* A list if extension modules that will be required once for the
package, then events will be dispatched to those extensions. The specified
module names must be `require()`-able from directory that contains the
`nodepy-package.toml`.

Check out the `nodepy.base.Extension` class for information on the extension
interface.

```toml
extensions = [ "@nodepy/werkzeug-reloader-patch", "./ext.py" ]
```

### `[engines]`

*Optional.* A table that maps engine-names to version numbers. These version
numbers should be [SemVer] too, but that is not a requirement. The actual
engine that runs the package will check the version number. The default engine
is `python` which compares against the Python version number.

TODO: PyPy, JPython, Stackless, etc. should match to different engine names.

```toml
[engines]
python = ">=3.0.0"
nodepy = ">=0.1.0"
```

### `[scripts]`

*Optional.* An object that associates event names with Node.py modules
which are executed during various events of the package lifecycle.

```toml
[scripts]
post-install = "./bin/install.py"
pre-uninstall = "./bin/uninstall.py"
pre-dist = "./bin/dist.py"
run = "./bin/run.py"
```

Currently supported fields are:

- pre-script
- pre-install, post-install
- pre-uninstall
- pre-dist, post-dist
- pre-publish, post-publish

__Todo__

- post-uninstall
- pre-version, post-version
- pre-test, test, post-test
- pre-stop, stop, post-stop
- pre-start, start, post-start
- pre-restart, restart, post-restart

### `[bin]`

*Optional.* An object that associates script names with a request string
that is then executed as the main module when the script is executed.

```toml
[bin]
myapp = "./cli.py"
```

### `[dependencies]`

*Optional,* An object that specifies the dependencies of the package. Every
dependency can be specified by a semver string, or an inline-table with
additional details.

```toml
[dependencies]
@nodepy/nodepy-pm = "~0.1.0"
@myscope/myutils = { path = "./subpkgs/myutils", link = True }
some_package = { git = "https://github.com/someorg/some_package.git", ref = "v6.3.0" }
@mycompany/companytools = { version = "^4.2.0", registry = "https://nodepy-registry.intranet/" }
```

Development dependencies can be specified by adding a filter.

```toml
[dependencies.'cfg(development)']
@NiklasRosenstein/yassg = "~0.6.0"
```

You can also use normal tables for non-standard package information.

```toml
[dependencies.'@myscope/myutils']
path = "./subpkgs/myutils"
link = true

[dependencies.some_package]
git = "https://github.com/someorg/some_package.git"
ref = "v6.3.0"

[dependencies.'@mycompany/companytools']
version = version = "^4.2.0"
registry = "https://nodepy-registry.intranet/"
```

### `[python_dependencies]`

*Optional.* Similar to the `[dependencies]` table, but it specifies actual
Python modules that the package requires. These modules can be installed
via Node.py PM using [Pip].

```toml
[python_dependencies]
Flask = "==0.12"
Flask-HTTPAuth = "==3.2.2"
mongoengine = "==0.11.0"

[python_dependencies.'cfg(development)']
mkdocs = ">=0.16.1"
```

### `[dist]`

*Optional.* A table that specifies options for generating an archived
distribution of the package with `nppm dist`.

```toml
[dist]
include_files = []
exclude_files = [".hg*"]
exclude_gitignored_files = true
```

#### `include_files`

*Optional.* A list of patterns that match the files to include.
Matching patterns include files possibly excluded by `exclude_files`.

#### `exclude_files`

*Optional.* A list of patterns that match the files to exclude from the
archive. Note that when installing packages with [nppm], it will add
default exclude patterns to this list. The actual patterns may change
with versions of nppm. When this document was last updated, nppm added
the following patterns:

- `.nodepy_modules/`
- `.svn/*`
- `.git`
- `.git/*`
- `.DS_Store`
- `*.pyc`
- `*.pyo`
- `dist/*`

  [Pip]: https://pypi.python.org/pypi/pip
  [nppm]: https://github.com/nodepy/nodepy

#### `exclude_gitignored_files`

*Optional.* Defaults to `true`. If enabled and a `.gitignore` file is preset,
the patterns listen in that file will be added to the `exclude_files` list.
The `.gitignore` file will automatically be added to the `include_files` list.

> Note that currently only the top-level `.gitignore` file is taken into
> account.
