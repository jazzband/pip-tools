Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"
  $ alias pip-sync="$TESTDIR/../bin/pip-sync"
  $ alias pip-review="$TESTDIR/../bin/pip-review"

First, create our *.in files.

  $ echo "python-dateutil" > requirements.in
  $ echo "-e git+git://github.com/svetlyak40wt/nose-progressive.git@with-all-my-patches" >> requirements.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file. Resulting
file should contain same VCS urls as the original one.

  $ pip-compile >/dev/null 2>&1

  $ cat requirements.txt
  -e git+git://github.com/svetlyak40wt/nose-progressive.git@*#egg=nose-progressive (glob)
  blessings==* (glob)
  nose==* (glob)
  python-dateutil==* (glob)
  six==* (glob)