[![Build status](https://secure.travis-ci.org/nvie/pip-tools.png?branch=master)](https://secure.travis-ci.org/nvie/pip-tools)

pip-tools = pip-compile + pip-sync + pip-review
===============================================

A set of two command line tools to help you keep your `pip`-based packages
fresh, even when you've pinned them.

[You _do_ pin them, right?][0]

![pip-tools overview for phase II](https://github.com/downloads/nvie/pip-tools/pip-tools-phase-II-overview.png)


Installation
============

To install, simply use pip:

```console
$ pip install pip-tools
```

Decide for yourself whether you want to install the tools system-wide, or
inside a virtual env.  Both are supported.


Testing
=======

To test with your active Python version:

```console
$ ./run-tests.sh
```

To test under all (supported) Python versions:

```console
$ tox
```

The tests run quite slow, since they actually interact with PyPI, which
involves downloading packages, etc.  So please be patient.


[![Flattr this][2]][1]

[0]: http://nvie.com/posts/pin-your-packages/
[1]: https://flattr.com/thing/882478/Pin-Your-Packages
[2]: http://api.flattr.com/button/button-static-50x60.png
[3]: https://bitheap.org/cram/
