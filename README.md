pip-tools = pip-review + pip-dump
=================================

A set of two command line tools to help you keep your `pip`-based packages
fresh, even when you've pinned them.  [You _do_ pin them, right?][0]

It's useful to run this on a regular basis, to keep your dependencies fresh,
but explicitly pinned, too.

pip-review
==========

`pip-review` checks PyPI and reports available updates.  It uses the list of
currently installed packages to check for updates, it does not use any
requirements.txt

Example:

    $ pip-review
    requests==0.13.4 available (you have 0.13.2)
    redis==2.4.13 available (you have 2.4.9)
    rq==0.3.2 available (you have 0.3.0)

Or, when all is fine:

    $ pip-review
    Everything up-to-date


pip-dump
========

`pip-dump` dumps the exact versions of installed packages in your active
environment to your `requirements.txt` file.  If you have more than one file
matching the `*requirements.txt` pattern (for example `dev-requirements.txt`),
it will update each of them smartly.

Example:

    $ cat requirements.txt
    Flask
    $ pip-dump
    $ cat requirements.txt
    Flask==0.9
    Jinja2==2.6
    Werkzeug==0.8.3

Packages that you don't want to dump but want to have installed
locally nonetheless can be put in an optional file called `.pipignore`.


Installation
============

To install, simply use pip:

    $ pip install pip-tools

Decide for yourself whether you want to install the tools system-wide, or
inside a virtual env.  Both are supported.


Testing
=======

The tools are lightly tested, with [cram][3].  To run the tests, run:

    $ cram tests

The tests run a bit slow, since they actually interact with PyPI, which
involves downloading packages, etc.  I didn't bother to stub it.


[![Flattr this][2]][1]

[0]: http://nvie.com/posts/pin-your-packages/
[1]: https://flattr.com/thing/882478/Pin-Your-Packages
[2]: http://api.flattr.com/button/button-static-50x60.png
[3]: https://bitheap.org/cram/
