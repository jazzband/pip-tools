Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install --upgrade --force-reinstall 'pip' > /dev/null 2>&1
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-review="$TESTDIR/../bin/pip-review"

Setup. Let's pretend we have some outdated package versions installed:

  $ pip install python-dateutil==1.5 >/dev/null 2>&1

Also install library, which caused warning message:

  $ pip install http://www.effbot.org/media/downloads/cElementTree-1.0.5-20051216.tar.gz >/dev/null 2>&1

Next, let's see what pip-review does:

  $ pip-review
  cElementTree==1.0.2-20050302 is available (you have 1.0.5.post20051216)
  python-dateutil==* is available (you have 1.5) (glob)
  wheel==* is available (you have 0.24.0) (glob)

Or in raw mode:

  $ pip-review --raw
  cElementTree==1.0.2-20050302
  python-dateutil==* (glob)
  wheel==* (glob)

We can also install these updates automatically:

  $ pip-review --auto >/dev/null 2>&1
  $ pip-review
  cElementTree==* is available (you have 1.0.5.post20051216) (glob)

Cleanup our playground:

  $ rm -rf FOO
