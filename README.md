pip-refresh
===========

This command line tool helps to keep your `pip`-based packages fresh, even when
you've pinned them.  You _do_ pin them, right?

It's useful to run this on a regular basis, to keep your dependencies fresh,
but explicitly pinned, too.

Show a list of packages that could be updated:

    $ pip-refresh
    requests==0.13.4 available (you have 0.13.2)
    redis==2.4.13 available (you have 2.4.9)
    rq==0.3.2 available (you have 0.3.0)

This invocation checks your default (virtual) Python environment.

    $ pip-refresh -r requirements.txt
    requests==0.13.9 available (you have 0.13.4, you require >=0.13,<0.14)
    Flask==0.9 available (you have 0.8, you require any version)

Or, specify any packages explicitly:

    $ pip-refresh foo bar qux
    All packages are up-to-date.

