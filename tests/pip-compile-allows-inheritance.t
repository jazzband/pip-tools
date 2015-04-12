Create a new playground first:

  $ . $TESTDIR/setup.sh

First, create our *.in files.

  $ echo "python-dateutil" > base.in
  $ echo "-r base.in" > develop.in
  $ echo "times" >> develop.in

COMPILING & SYNCING
===================

Run pip-compile to generate the requirements.txt file. Resulting
file should contain python-dateutil from base.in and it's dependencies
as well.

  $ pip-compile develop.in
  Dependencies updated.

  $ cat develop.txt
  python-dateutil==* (glob)
  pytz==* (glob)
  six==* (glob)
  times==* (glob)
