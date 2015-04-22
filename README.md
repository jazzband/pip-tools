[![Build status](https://secure.travis-ci.org/nvie/pip-tools.png?branch=future)](https://secure.travis-ci.org/nvie/pip-tools)

pip-tools = pip-compile + pip-sync + pip-review
===============================================

A set of command line tools to help you keep your `pip`-based packages fresh,
even when you've pinned them.  [You do pin them, right?][0]

![pip-tools overview for phase II](https://cloud.github.com/downloads/nvie/pip-tools/pip-tools-phase-II-overview.png)

[0]: http://nvie.com/posts/pin-your-packages/


Installation
============

To install, simply use [pipsi](https://github.com/mitsuhiko/pipsi):

```console
$ pipsi install pip-tools
```

Or if you specifically want the features available from the future branch:
```console
$ pip install git+https://github.com/nvie/pip-tools.git@future
```

Decide for yourself whether you want to install the tools system-wide, or
inside a virtual env.  Both are supported.
