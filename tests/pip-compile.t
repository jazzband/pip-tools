Create a new playground first:

  $ . $TESTDIR/setup.sh

First, create our requirements.in file (manually).  We start by creating
a non-pinned version of it:

  $ echo "python-dateutil" > requirements.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file.  As shown, the six
dependency is automatically inferred and added:

  $ pip-compile
  Dependencies updated.

  $ cat requirements.txt
  python-dateutil==* (glob)
  six==* (glob)

Note that this did not touch our environment in any way:

  $ pip freeze -l | grep -v six
  [1]

That only happens when we run pip-sync:

  $ pip-sync

  $ pip freeze -l | grep -v six
  python-dateutil==* (glob)

A better (more explicit) way is to pin the versions in requirements.in.  Note
that we're replacing the python-dateutil package in it by an explicitly pinned
version of raven:

  $ echo "raven==1.9.3" > requirements.in

That (old) version of raven required simplejson, which will be recorded when we
run pip-compile now:

  $ pip-compile
  Dependencies updated.

  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.4.0

Now, when we sync the newly Recorded State to the Environment, note that this
did unintall the python-dateutil and six packages that have been previously
been installed:

  $ pip freeze -l | grep -v six
  python-dateutil==* (glob)

  $ pip-sync

  $ pip freeze -l | grep -v six
  raven==1.9.3
  simplejson==2.4.0


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

