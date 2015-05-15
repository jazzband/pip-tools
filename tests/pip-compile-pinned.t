Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install 'pip>=1.5' > /dev/null 2>&1
  $ pip install six >/dev/null 2>&1
  $ export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"
  $ alias pip-sync="$TESTDIR/../bin/pip-sync"
  $ alias pip-review="$TESTDIR/../bin/pip-review"

First, create our requirements.in file (manually).  We start by creating
a non-pinned version of it:

  $ echo "python-dateutil" > requirements.in

Let's also create a pin list which is used in resolving the dependencies

  $ echo "six==1.8.0" > pin.txt
  $ echo "python-dateutil==2.4.0" >> pin.txt


COMPILING WITH PIN LIST
=======================

Run pip-compile to generate the requirements.txt file.  As shown, the six
dependency is automatically inferred and added:

  $ pip-compile-pinned --pin-file pin.txt  >/dev/null 2>&1

  $ cat requirements.txt
  python-dateutil==2.4.0
  six==1.8.0


CONFLICT DETECTION
==================

Warn about a conflict situation:

  $ echo "python-dateutil>2.4.0" > requirements.in
  $ pip-compile-pinned --pin-file pin.txt
  error: Conflict: python-dateutil==2.4.0 with python-dateutil>2.4.0
  [1]

When pip-compile ends in an error, requirements.txt should've been untouched:

  $ cat requirements.txt
  python-dateutil==2.4.0
  six==1.8.0


