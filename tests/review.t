Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ alias pip-review="$TESTDIR/../bin/pip-review"

Setup. Let's pretend we have some outdated package versions installed:

  $ pip install times==0.2 >/dev/null 2>&1

Also install library, which caused warning message:

  $ pip install http://www.effbot.org/media/downloads/cElementTree-1.0.5-20051216.tar.gz >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-review
  Warning: cannot find svn location for cElementTree==1.0.5-20051216
  cElementTree==1.0.2-20050302 is available (you have 1.0.5-20051216)
  times==0.5 is available (you have 0.2)

Or in raw mode:

  $ pip-review --raw
  Warning: cannot find svn location for cElementTree==1.0.5-20051216
  cElementTree==1.0.2-20050302
  times==0.5

We can also install these updates automatically:

  $ pip-review --auto >/dev/null 2>&1
  $ pip-review
  Warning: cannot find svn location for cElementTree==1.0.2-20050302
  Everything up-to-date
