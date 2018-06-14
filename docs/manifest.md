+++
title = "The Package Manifest (nodepy.json)"
+++

Node.py package information is saved in a `nodepy.json` file. To load and
validate such files, use the `nppm/manifest` module.

```python
import {parse as parse_manifest, InvalidPackageManifest}
  from 'nppm/manifest'

try:
  manifest = parse_manifest('nodepy.json')
except (FileNotFoundError, manifest.InvalidPackageManifest) as exc:
  manifest = None
  print(exc)
```

  [SemVer]: http://semver.org/

## Specification

Below is an example manifest that illustrates the available fields that
are understood by the Node.py package manager:

```json
{
  "name": "@scope/package-name",
  "version": "2.13.1-semver",
  "license": "MIT",
  "description": "A short description of the package here",
  "keywords": ["some keywords", "to find your package"],
  "categories": ["CLI", "Library", "Networking"],
  "publish": true,
  "main": "./lib/index",
  "resolve_root": "./lib",
  "extensions": ["some-package"],
  "authors": ["author@mail.com"],
  "engines": ["nodepy>=2.0.0", "python>=3.4"],
  "include": ["lib/**", "scripts/**", "README.md", "LICENSE.txt"],
  "exclude": ["build/**"],
  "scripts": {
    "post-install": "./scripts/post-install.py",
    "pre-uninstall": "./scripts/pre-uninstall.py",
    "start": "./lib/main.py",
    "hello": "$ echo hello!"
  },
  "bin": {
    "my-executable-name${py}": "./lib/main.py"
  },
  "dependencies": {
    "werkzeug-reloader-patch": "~1.13.2"
  },
  "cfg(dev).dependencies": {
    "nodepy-nose": "--pure --registry=yourcom git+https://github.com/nodepy/nodepy-nose.git@v0.0.4"
  },
  "pip_dependencies": {
    "Flask": ">=12.1.0",
    "hammock": ">=2.6.0"
  },
  "cfg(dev).pip_dependencies": {
    "mkdocs": ">=0.16.1",
    "mkdocs-material": ">=1.12.0"
  },
  "registries": {
    "workplace": {
      "url": "https://nodepy-registry.yourcom.local/"
    }
  }
}
```

#### `keywords`

> Note: Any strings can be used as keywords. There can only be a maximum of
> 15 keywords per package.

#### `categories`

The list of available categories can be accessed via the `nppm/manifest`
module (`require('nppm/manifest').categories`). Below is a copy of the
supported categories (WIP):

* CLI
* Library
* Framework
* Application
* System
* Networking
* GUI

> Note: You can only specify up to 5 categories per package.

#### `engines`

> Note: Currently, engine validation is not actually performed.

#### `include` / `exclude`

An exhaustive list of filenames or glob-patterns to include or exclude
into the source package. Note that if a `.gitignore` file is found in
the same directory as the `nodepy.json` manifest, it is only taken into
account when `exclude` takes effect.

Additionally, the following entries are `exclude`-ed by default:

* `.nodepy_modules/`
* `.svn/*`
* `.git`
* `.git/*`
* `.DS_Store`
* `*.py[co]`
* `dist/*`

> Note: Specifying `include` overrides the effect of `exclude.

#### `scripts`

Allows you to specify scripts that are run at certain points, or scripts that
can be run with the `nodepypm run <script>` command. Currently supported
callback scripts are:

* `pre-script`: Called before any script is executed.
* `pre-install`, `post-install`: Called before and after the package was
  installed, respectively. The `post-install` script has access to the
  nppm `installer` object via a global variable.
* `pre-uninstall`: Called before the package is being uninstalled.
* `pre-dist`, `post-dist`: Called before and after a source or binary
  distribution of the package is created, respectively.
* `pre-publish`, `post-publish`: Called before and after a source or binary
  distribution of the package is published to a package registry, respectively.

> Note: On the todolist are `post-uninstall, pre-version, post-version,
> pre-test, test, post-test, pre-stop, stop, post-stop, pre-start, start,
> post-start, pre-restart, restart, post-restart`.

#### `bin`

Allows you to specify one or more command-line applications that will be
installed with the package. Note that packages can be installed with the
`--pure` option, which skip the installation of executable binaries.

The `${py}` placeholder is optional and will be expanded to the three
values `'', 'X', 'X.Y'` where X and Y are the Python major and minor
version.

### `dependencies`

An object that specifies the dependencies of the package. Every dependency
must be a string that could also be passed to the package manager's
commandline. The following formats are supported:

* SemVer: Eg. `~0.13.2`
* Directory/Archive: Eg. `vendor/nodepy-nose-0.0.4.zip` or `./vendor/my-module`
* Git: Eg. `git+https://github.com/nodepy/nodepy-nose.git@ref-name` (where
  the `@ref-name` part is optional and specifies the Git ref to clone)

Additionally, flags can be added at the beginning of the dependency string.
The following flags are supported:

* `--pure`: Install the package as a pure source dependency and skip
  installing binaries from the `bin` section. Note that binaries may 
  still be installed if there is other means that the dependency is
  being installed.
* `--internal`: Install the package as an internal dependency of this
  package, making it invisible to outside packages. Note that dependencies
  that can not be otherwise satisified will be automatically installed as
  an internal dependency.
* `--link`: Don't copy the package to the modules directory but instead place
  a link file that redirects nodepy to the package's original directory. This
  only works with installing from a path.
* `--optional`: Mark the dependency as optional, preventing the installation
  process from failing if the dependency can not be installed. Note that it
  will still try to satisfy the dependency and eventually fallback to an
  internal dependency if necessary.
* `--recursive`: Used only on Git dependencies. Causes the repository to be
  cloned recursively.
* `--registry=<name>`: Specify the name of the registry from which the
  dependency should be resolved. Note that this will disable any alternatives
  procedures for resolving the dependency. The registry must be configured in
  the same package manifest under the `registries` key or otherwise be present
  in the global package manager configuration (`~/.nodepy/pm-config.ini`).
  Passing this option for a non-registry based dependency is an error.

You can use the `nppm/manifest:Requirement` class and its `.from_line()`
method to parse such dependency specifications.

### `pip_dependencies`

Similar to the `dependencies` field, but it specifies actual Python modules
that the package requires. The package manager will install these packages
via [Pip].

### `cfg(...)`

This is a special field that can be used to specify dependencies based on
the environment (eg. development vs. production) or platform. If the field
name is in plain `cfg(...)` format, it must be an object that contains
additional fields. These fields will automatically merge with or overwrite
existing entries in the manifest given that the `...` matches the current
configuration.

Alternatively, it can also be used in the `cfg(...).<field>` format, in 
which case it will have the same effect as using the standard format and
specifying the `<field>` inside the object.

The `...` portion must be at least one variable or comparison operator. Filters
can be joined by `&&` and `||` operators and may be grouped using parentheses.
Currently available variables are:

* `dev`: True if the package is being treated in development mode.
* `prod`: True if the package is being treated in production mode.
* `win32`
* `darwin`
* `linux`

This is the formal grammar of the filter string:

    <expr> ::= <test> || <and> || <or> || <group>
    <and> ::= <expr> 'and' <expr>
    <or> ::= <expr> 'or' <expr>
    <group> ::= '(' <expr> ')'
    <test> ::= <var> <op> <value> || <var>
    <var> ::= {A-Za-z0-9}+
    <op> := '==' || '!=' || '<' || '<=' || '>' || '>='
    <value> ::= {^&|<>=()}+
