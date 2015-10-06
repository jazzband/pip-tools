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


Installation
============

To install, simply use pip:

```console
$ pip install pip-review
```

Decide for yourself whether you want to install the tool system-wide, or
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


Origins
=======

`pip-review` was originally part of [pip-tools][0] but 
[has been discontinued][1] as such. See [Pin Your Packages][2] by Vincent
Driessen for the original introduction. Since there are still use cases, the
tool now lives on as a separate package.


[0]: https://github.com/nvie/pip-tools/
[1]: https://github.com/nvie/pip-tools/issues/185
[2]: http://nvie.com/posts/pin-your-packages/
[3]: https://bitheap.org/cram/
