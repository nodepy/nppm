<p align="center"><img src="https://i.imgur.com/fy4KZIW.png" height="128px"></p>
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg">
    <a href="https://travis-ci.org/nodepy/nppm"><img src="https://travis-ci.org/nodepy/nppm.svg?branch=master"></a>
</p>

## nppm

[Node.py]: https://nodepy.org/

This is the [Node.py] Package Manager. We recommend installing it using the
remote install script:

    $ nodepy https://nodepy.org/get-nppm.py

## Development

For a development installation, clone the repository and use the local
install script, passing the flags `-le` for a local and editable installation,
meaning that the package will only be linked instead of its files being
copied.

    $ nodepy ./scripts/install -le

## Troubleshooting

__FileNotFoundError: No such file or directory: '...\\installed-files.txt'__

This is a bug [that will be fixed with Pip 9.0.2](https://github.com/pypa/pip/issues/373#issuecomment-302632300).
In the meantime, to fix this issues, ensure that you have the `wheel` package
installed.

    pip install wheel [--user]

## Changes

### v2.1.1 (2019-10-20)

* Fix `ScriptMaker` (now needs to specify an import name in the entrypoint
    that is passed into `distlib`)
* Fix Pip requirement validation which relied on internal Pip APIs (now uses
    `packaging` module, or the version vendored via Pip)

### v2.1.0 (2018-06-14)

* Renamed from `nodepy-pm` to `nppm`
* Implement compatibility with Pip 10
* Add MIT license header to all source files

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
