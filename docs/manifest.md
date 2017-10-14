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

```toml
repository = "https://github.com/nodepy/nodepy"
```

#### `license`

*Required when publishing a package on the registry.* The license of the
package source code.

```toml
license = "MIT"
```

#### `resolve_root`

*Optional.* A directory relative to the `package.json` that is considered the
root directory when importing modules from this package. Should be used if you
want to keep all source files under a sub-directory of your package.

```toml
resolve_root = "lib/"
```

#### `private`

*Optional.* Prevent publication of the package with `nppm publish`. This is used
for packages that want to take advantage of the nppm dependency management but
are not actuall supposed to be placed into the public registry. An example
of this would be a package that generates the documentation of another project.

```toml
private = true
```

#### `main`

*Optional.* This field describes the name of the module to load when your
package is required by another module. If this field is not specified, the
`Context._index_files` are tried instead (which are `index` and `__init__`).

```toml
main = "./index.py"
```

#### `extensions`

*Optional.* A list if extension modules that will be required once for the
package, then events will be dispatched to those extensions. The specified
module names must be `require()`-able from directory that contains the
`nodepy-package.toml`.

Check out the `nodepy.base.Extension` class for information on the extension
interface.

```toml
extensions = [ "@nodepy/werkzeug-reloader-patch", "./ext.py" ]
```

### `[authors]`

*Optional.* A table that specifies the authors of this package. The keys of
this table are the author names, the values are sub tables with additional
information about the author.

* `email` (an email string, or array of email strings)
* `homepage`

```toml
[authors]
"Niklas Rosenstein" = { email = "rosensteinniklas@gmail.com" }
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

### `[dependencies.nodepy]`

*Optional.* An object that specifies the dependencies of the package. Every
dependency can be specified by a semver string, or a table with additional
details.

Dependencies can be selected based on a the current environment by using the
`cfg(...)` filter, which is appended as a sub-table. More on the `cfg(...)`
filter at the end of this document.

```toml
[dependencies.nodepy]

[dependencies.nodepy.'cfg(development)']
```

#### Dependency Types

##### Registry Reference

Registry references are resolved across all configured registries. Simply by
assigning a version-selector string to the dependency name in the TOML
configuration creates such a registry-dependency reference.

```toml
[dependencies.nodepy]
utils = "~0.11.0"

[dependencies.nodepy.'@mycompany/toolbox']
version = "~1.4.2"
registry = "https://mycompany-intranet.com/nodepy-registry"
```

_Options_

* `version`: The SemVer selector for the dependency.
* `registry`: An optional URL pointing to a Node.py package registry. If
  specified, the default registries are not checked.
* `private`: Defaults to `false`. If `true`, the dependency will be installed
  in the local `.nodepy_modules/` directory rather than being placed into the
  root modules directory. Usually, dependencies are only installed privately
  if a version collision is detected. Example if `utils` was marked private:

    ```
    .nodepy_modules/
      myproject/
        .nodepy_modules/
          utils/
    ```

##### Git Repository Reference

Packages can be installed from a Git repository by specifying the repository
URL and a reference to clone from. Note that SHA refs are not supported.

```toml
[dependencies.nodepy.utils]
git = "https://github.com/me/nodepy-utils"
ref = "v0.11.0"
```

_Options_

* `git`: The Git repository clone URL.
* `ref`: The Git ref to clone.
* `recursive`: Clone the repository recursively. Defaults to `true`.
* `private`: See above.

##### Local Reference

Packages can be installed from a path on the filesystem. The packages can also
be installed in *develop* mode where a link is created to the original package
directory rather than copying all files into the modules directory.

```toml
[dependencies.nodepy.utils]
path = "./submodules/utils"
link = true
```

_Options_

* `path`: The path to install the dependency from. A relative path is resolved
  from the package's root directory (independent from `[package].resolve_root`).
* `link`: If `true`, the package will be linked into the modules directory
  rather than performing a normal installation. This is equal to installing
  the package using the `-e, --develop` option via `nodepy-pm`.
* `private`: See above.

### `[dependencies.python]`

*Optional.* Similar to the `[dependencies.nodepy]` table, but it specifies
actual Python modules that the package requires. These modules can be
installed via Node.py PM using [Pip].

```toml
[dependencies.python]
Flask = "==0.12"
Flask-HTTPAuth = "==3.2.2"
mongoengine = "==0.11.0"

[dependencies.python.'cfg(development)']
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
