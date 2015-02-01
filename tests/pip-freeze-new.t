Create a new playground first:

  $ virtualenv --python="$(which python)" FOO > /dev/null 2>&1
  $ . FOO/bin/activate
  $ pip install --upgrade --force-reinstall 'pip==6.0.6' > /dev/null 2>&1
  $ alias pip-dump="$TESTDIR/../bin/pip-dump"

Setup:

  $ echo "python-dateutil" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1

Check the output of 'pip freeze'

  $ pip freeze -lr requirements.txt
  You are using pip version 6.0.6, however version * is available. (glob)
  You should consider upgrading via the 'pip install --upgrade pip' command.
  python-dateutil==2.4.0
  ## The following requirements were added by pip freeze:
  six==1.9.0

Next, let's see what pip-dump does:

  $ pip-dump
  You are using pip version 6.0.6, however version * is available. (glob)
  You should consider upgrading via the 'pip install --upgrade pip' command.
  You are using pip version 6.0.6, however version * is available. (glob)
  You should consider upgrading via the 'pip install --upgrade pip' command.

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt
  python-dateutil==* (glob)
  six==* (glob)

Cleanup our playground:

  $ rm -rf FOO

