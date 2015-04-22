[![Build status](https://secure.travis-ci.org/nvie/pip-tools.png?branch=future)](https://secure.travis-ci.org/nvie/pip-tools)

pip-tools = pip-compile + pip-sync + pip-review
===============================================

A set of command line tools to help you keep your `pip`-based packages fresh,
even when you've pinned them.  [You do pin them, right?][0]

![pip-tools overview for phase II](https://cloud.github.com/downloads/nvie/pip-tools/pip-tools-phase-II-overview.png)

[0]: http://nvie.com/posts/pin-your-packages/


Installation
============

```console
$ pip install --upgrade pip  # pip-tools needs pip==6.1 or higher (!)
$ pip install pip-tools
```

Or if you specifically want the features available from the future branch:
```console
$ pip install git+https://github.com/nvie/pip-tools.git@future
```
