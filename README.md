pip-tools = pip-review + pip-dump
=================================

A set of two command line tools to help you keep your `pip`-based packages
fresh, even when you've pinned them.  [You _do_ pin them, right?][0]

It's useful to run this on a regular basis, to keep your dependencies fresh,
but explicitly pinned, too.

pip-review
==========

`pip-review` checks PyPI to see if there are updates available for packages
that are currently installed.  It only works on your **active environment**, it
does not check or touch `requirements.txt`.

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

`pip-dump` dumps the exact versions of installed packages in your **active
environment** to your `requirements.txt` file.  If you have more than one file
matching the `*requirements.txt` pattern (for example `dev-requirements.txt`),
it will update each of them smartly.  You can also put package names you don't
want to dump in requirement files in a file named `.pipignore`.

Example:

    $ cat requirements.txt
    Flask
    $ pip-dump
    $ cat requirements.txt
    Flask==0.9
    Jinja2==2.6
    Werkzeug==0.8.3


TODO
====
* Nag about version mismatches between what's installed and what's in
  `requirements.txt` (keeps `requirements.txt` up-to-date)
* Automatically have it update your `requirements.txt` with all the new
  versions
* Respect bounds that are stated in `requirements.txt` (for example, when
  your project requires `lxml>=2.3,<2.4`, don't nag about 2.4.5 being
  available).

[![Flattr this][2]][1]

[0]: http://nvie.com/posts/pin-your-packages/
[1]: https://flattr.com/thing/882478/Pin-Your-Packages
[2]: http://api.flattr.com/button/button-static-50x60.png
