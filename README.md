<p align="center"><img src=".assets/nodepy-logo.png" height="128px"></p>
<h1 align="center">nodepy-pm</h1>
<img align="right" src="https://img.shields.io/badge/License-MIT-yellow.svg">
<p align="center">
  The <a href="https://github.com/nodepy/nodepy">Node.py</a> Package Manager.
</p>

**nodepy-pm** is the Node.py package manager. It is developed, released
and also installed alongside the Node.py runtime. If in any case you want
to install the package manager manually, you can do so by using the
`bootstrap.py` script.

It is suggested to install nodepy-pm using the remote install script available
under https://nodepy.org/install-pm.

    $ nodepy https://nodepy.org/install-pm

If you want to install from this repository instead, clone it and run

    $ nodepy ./scripts/install

During development, it might be desirable to install nodepy-pm locally in
editable (development) mode.

    $ nodepy ./scripts/install -le
