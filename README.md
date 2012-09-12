pip-review
==========

This command line tool helps to keep your `pip`-based packages fresh, even when
you've pinned them.  You _do_ pin them, right?  {TODO: Link to blog post}

It's useful to run this on a regular basis, to keep your dependencies fresh,
but explicitly pinned, too.

Show a list of packages that could be updated:

    $ pip-review
    requests==0.13.4 available (you have 0.13.2)
    redis==2.4.13 available (you have 2.4.9)
    rq==0.3.2 available (you have 0.3.0)

Or, when all is fine:

    $ pip-review
    Everything up-to-date


TODO
====
* Nag about version mismatches between what's installed and what's in
  `requirements.txt` (keeps `requirements.txt` up-to-date)
* Automatically have it update your `requirements.txt` with all the new
  versions
* Respect bounds that are stated in `requirements.txt` (for example, when
  your project requires `lxml>=2.3,<2.4`, don't nag about 2.4.5 being
  available).
