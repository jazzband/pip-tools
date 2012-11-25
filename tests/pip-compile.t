Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"
  $ alias pip-sync="$TESTDIR/../bin/pip-sync"
  $ alias pip-review="$TESTDIR/../bin/pip-review"

First, create our requirements.in file (manually).  We start by creating
a non-pinned version of it:

  $ echo "python-dateutil" > requirements.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file.  As shown, the six
dependency is automatically inferred and added:

  $ pip-compile >/dev/null 2>&1

  $ cat requirements.txt
  python-dateutil==* (glob)
  six==* (glob)

Note that this did not touch our environment in any way:

  $ pip freeze -l | grep -v argparse
  [1]

That only happens when we run pip-sync:

  $ pip-sync >/dev/null 2>&1

  $ pip freeze -l | grep -v argparse
  python-dateutil==* (glob)
  six==* (glob)

A better (more explicit) way is to pin the versions in requirements.in.  Note
that we're replacing the python-dateutil package in it by an explicitly pinned
version of raven:

  $ echo "raven==1.9.3" > requirements.in

That (old) version of raven required simplejson, which will be recorded when we
run pip-compile now:

  $ pip-compile >/dev/null 2>&1

  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.4.0

Now, when we sync the newly Recorded State to the Environment, note that this
did unintall the python-dateutil and six packages that have been previously
been installed:

  $ pip freeze -l
  python-dateutil==* (glob)
  six==* (glob)

  $ pip-sync >/dev/null 2>&1

  $ pip freeze -l
  raven==1.9.3
  simplejson==2.4.0


UPDATING
========

Okay, to recap, we have:

  $ cat requirements.in
  raven==1.9.3

  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.4.0

Now, show available updates for packages in requirements.in:

  $ pip-review requirements.in
  - raven==* (glob)

Or show them for all Recorded State:

  $ pip-review
  requirements.in:
  - raven==* (glob)

@Bruno: Don't you think the above pip-review output should also report
review secondary dependencies?  For example, when simplejson==2.6.2 is
available, this should be suggested, right (given that 2.6.2 matches raven deps
criteria)?


Apply an update manually by modifying requirements.in:

  $ echo "raven==2.0.6" > requirements.in

  $ pip-compile >/dev/null 2>&1

  $ grep -v "simplejson==2.4.0" requirements.txt
  raven==2.0.6
  simplejson==* (glob)


Add a new requirement:

  $ echo "requests==0.8.9" >> requirements.in
  $ pip-compile >/dev/null 2>&1
  $ cat requirements.txt
  certifi==* (glob)
  raven==2.0.6
  requests==0.8.9
  simplejson==* (glob)


CONFLICT DETECTION
==================

Warn about a conflict situation:

  $ echo "raven==1.9.3" > requirements.in
  $ echo "simplejson==2.6.2" >> requirements.in
  $ pip-compile
  error: Conflict: simplejson==2.6.2 with simplejson<2.5.0
  [1]

When pip-compile ends in an error, requirements.txt should've been untouched:

  $ cat requirements.txt
  certifi==* (glob)
  raven==2.0.6
  requests==0.8.9
  simplejson==* (glob)

