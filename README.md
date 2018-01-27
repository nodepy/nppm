## nodepy-pm

![](https://img.shields.io/badge/License-MIT-yellow.svg)
[![Build Status](https://travis-ci.org/nodepy/nodepy-pm.svg?branch=master)](https://travis-ci.org/nodepy/nodepy-pm)

  [Node.py]: https://nodepy.org/

This is the [Node.py] Package Manager. It is recommended to install the package
manager with the remote install script available at
https://nodepy.org/install-pm.

    $ nodepy https://nodepy.org/install-pm

If you want to install from this repository instead, clone it and run:

    $ nodepy ./scripts/install

During development, it might be desirable to install nodepy-pm locally in
editable (development) mode:

    $ nodepy ./scripts/install -le

### Troubleshooting

__FileNotFoundError: No such file or directory: '...\\installed-files.txt'__

This is a bug [that will be fixed with Pip 9.0.2](https://github.com/pypa/pip/issues/373#issuecomment-302632300).
In the meantime, to fix this issues, ensure that you have the `wheel` package
installed.

    pip install wheel [--user]
