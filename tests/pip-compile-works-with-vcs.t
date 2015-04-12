Create a new playground first:

  $ . $TESTDIR/setup.sh

First, create our *.in files.

  $ echo "python-dateutil" > requirements.in
  $ echo "-e git+git://github.com/svetlyak40wt/nose-progressive.git@with-all-my-patches" >> requirements.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file. Resulting
file should contain same VCS urls as the original one.

  $ pip-compile
  Dependencies updated.

  $ cat requirements.txt
  -e git+git://github.com/svetlyak40wt/nose-progressive.git@*#egg=nose-progressive (glob)
  python-dateutil==* (glob)
  six==* (glob)
