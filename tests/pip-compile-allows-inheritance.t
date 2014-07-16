Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install 'pip>=1.5' > /dev/null 2>&1
  $ pip install argparse >/dev/null 2>&1
  $ pip install six >/dev/null 2>&1
  $ export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"
  $ alias pip-sync="$TESTDIR/../bin/pip-sync"
  $ alias pip-review="$TESTDIR/../bin/pip-review"

First, create our *.in files.

  $ echo "python-dateutil" > base.in
  $ echo "-r base.in" > develop.in
  $ echo "times" >> develop.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file. Resulting
file should contain python-dateutil from base.in and it's dependencies
as well.

  $ pip-compile develop.in >/dev/null 2>&1

  $ cat develop.txt
  python-dateutil==* (glob)
  pytz==* (glob)
  six==* (glob)
  times==* (glob)
