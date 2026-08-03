# Electrum-LTC - Lightweight Litecoin client

```
Licence: MIT Licence
Author: Litecoin Foundation
Language: Python (>= 3.10)
Homepage: https://electrum-ltc.org/
```

[![Build Status](https://github.com/litecoin-foundation/electrum-ltc/actions/workflows/builds.yml/badge.svg?branch=master)](https://github.com/litecoin-foundation/electrum-ltc/actions/workflows/builds.yml)
[![Test coverage statistics](https://coveralls.io/repos/github/litecoin-foundation/electrum-ltc/badge.svg?branch=master)](https://coveralls.io/github/litecoin-foundation/electrum-ltc?branch=master)
[![Help translate Electrum online](https://d322cqt584bo4o.cloudfront.net/electrum/localized.svg)](https://crowdin.com/project/electrum)


## Getting started

_(If you've come here looking to simply run Electrum-LTC,
[you may download it here](https://electrum-ltc.org/#download).)_

Electrum-LTC itself is pure Python, and so are most of the required dependencies,
but not everything. The following sections describe how to run from source, but here
is a TL;DR:

First, install `uv` if you have not already:
```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```
Restart your shell if the `uv` command is not immediately available.

```
$ sudo apt-get install libsecp256k1-dev
$ uv venv
$ ELECTRUM_ECC_DONT_COMPILE=1 uv pip install ".[gui,crypto]"
$ uv run ./run_electrum
```

### Not pure-python dependencies

#### Qt GUI

If you want to use the Qt interface, install the Qt dependencies:
```
$ uv pip install PyQt6
```

#### QR code scanning

QR code recognition uses QtMultimedia and [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp/):
```
$ sudo apt-get install python3-pyqt6.qtmultimedia libzxing3 (or libzxing4)
```

#### libsecp256k1

For elliptic curve operations,
[libsecp256k1](https://github.com/bitcoin-core/secp256k1)
is a required dependency.

If you "pip install" Electrum-LTC, by default libsecp will get compiled locally,
as part of the `electrum-ecc` dependency. This can be opted-out of,
by setting the `ELECTRUM_ECC_DONT_COMPILE=1` environment variable.
For the compilation to work, besides a C compiler, you need at least:
```
$ sudo apt-get install automake libtool
```
If you opt out of the compilation, you need to provide libsecp in another way, e.g.:
```
$ sudo apt-get install libsecp256k1-dev
```

#### cryptography

Due to the need for fast symmetric ciphers,
[cryptography](https://github.com/pyca/cryptography) is required.
Install from your package manager (or from pip):
```
$ uv pip install cryptography
```

For fast blockchain verification,
[scrypt](https://github.com/holgern/py-scrypt) is required.
Install from your package manager (or from pip):

```
$ uv pip install scrypt
```

#### hardware-wallet support

If you would like hardware wallet support,
[see this](https://github.com/spesmilo/electrum-docs/blob/master/hardware-linux.rst).


### Running from tar.gz

If you downloaded the official package (tar.gz), you can run
Electrum-LTC from its root directory without installing it on your
system; all the pure python dependencies are included in the 'packages'
directory. To run Electrum-LTC from its root directory, just do:
```
$ ./run_electrum
```

You can also install Electrum-LTC into a virtual environment:
```
$ uv venv
$ uv pip install .
$ uv run electrum-ltc
```

This will download and install the Python dependencies used by
Electrum-LTC instead of using the 'packages' directory.
It will also place an executable named `electrum-ltc` in `.venv/bin`.


### Development version (git clone)

_(For OS-specific instructions, see [here for Windows](contrib/build-wine/README_windows.md),
and [for macOS](contrib/osx/README_macos.md))_

Check out the code from GitHub:
```
$ git clone https://github.com/litecoin-foundation/electrum-ltc.git
$ cd electrum-ltc
$ git submodule update --init
```

Run install (this should install dependencies):
```
$ uv venv
$ uv pip install -e ".[gui,crypto]"
```

Create translations (optional):
```
$ sudo apt-get install gettext
$ ./contrib/locale/build_locale.sh electrum/locale/locale electrum/locale/locale
```

Finally, to start Electrum:
```
$ uv run ./run_electrum
```

### Run tests

Run unit tests with `pytest`:
```
$ uv pip install -r contrib/requirements/requirements-ci.txt
$ uv pip install -e ".[tests,qml_gui]"
$ uv run python -m pytest tests -v
```
(can be parallelized with `-n auto` option, using [`pytest-xdist`](https://github.com/pytest-dev/pytest-xdist) plugin)

To run a single file, specify it directly like this:
```
$ uv run python -m pytest tests/test_bitcoin.py -v
```

## Creating Binaries

- [Linux (tarball)](contrib/build-linux/sdist/README.md)
- [Linux (AppImage)](contrib/build-linux/appimage/README.md)
- [macOS](contrib/osx/README.md)
- [Windows](contrib/build-wine/README.md)
- [Android](contrib/android/Readme.md)


## Contributing

Any help testing the software, reporting or fixing bugs, reviewing pull requests
and recent changes, writing tests, or helping with outstanding issues is very welcome.
Implementing new features, or improving/refactoring the codebase, is of course
also welcome, but to avoid wasted effort, especially for larger changes,
we encourage discussing these on the issue tracker first.

Please improve translations on [Crowdin](https://crowdin.com/project/electrum).


Electrum-LTC is based on Electrum, created by Thomas Voegtlin.
Available under the MIT License.
