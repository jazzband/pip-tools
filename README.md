[![Build status](https://secure.travis-ci.org/nvie/pip-tools.png?branch=master)](https://secure.travis-ci.org/nvie/pip-tools)

pip-tools = pip-review + pip-dump
=================================

A set of two command line tools to help you keep your `pip`-based packages
fresh, even when you've pinned them.

[You _do_ pin them, right?][0]

![pip-tools overview](http://cloud.github.com/downloads/nvie/pip-tools/pip-tools.png)


pip-review
==========

`pip-review` checks PyPI and reports available updates.  It uses the list of
currently installed packages to check for updates, it does not use any
requirements.txt

Example, report-only:

```console
$ pip-review
requests==0.13.4 available (you have 0.13.2)
redis==2.4.13 available (you have 2.4.9)
rq==0.3.2 available (you have 0.3.0)
```

Example, actually install everything:

```console
$ pip-review --auto
... <pip install output>
```

Example, run interactively, ask to upgrade for each package:

```console
$ pip-review --interactive
requests==0.14.0 available (you have 0.13.2)
Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit y
...
redis==2.6.2 available (you have 2.4.9)
Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit n
rq==0.3.2 available (you have 0.3.0)
Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit y
...
```


pip-dump
========

`pip-dump` dumps the exact versions of installed packages in your active
environment to your `requirements.txt` file.  If you have more than one file
matching the `*requirements.txt` pattern (for example `dev-requirements.txt`),
it will update each of them smartly.

Example:

```console
$ cat requirements.txt
Flask
$ cat dev-requirements.txt
ipython
$ pip-dump
$ cat requirements.txt
Flask==0.9
Jinja2==2.6
Werkzeug==0.8.3
$ cat dev-requirements.txt
ipython==0.13
```

Packages that you don't want to dump but want to have installed
locally nonetheless can be put in an optional file called `.pipignore`.


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
