Create a new playground first:

  $ virtualenv --python="$(which python)" FOO > /dev/null 2>&1
  $ . FOO/bin/activate
  $ pip install --upgrade --force-reinstall 'pip==1.5.6' > /dev/null 2>&1
  $ alias pip-dump="$TESTDIR/../bin/pip-dump"

Setup:

  $ echo "python-dateutil" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1

Check the output of 'pip freeze'

  $ pip freeze -lr requirements.txt
  python-dateutil==2.4.0
  ## The following requirements were added by pip --freeze:
  six==1.9.0

Next, let's see what pip-dump does:

  $ pip-dump

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt
  python-dateutil==* (glob)
  six==* (glob)

Cleanup our playground:

  $ rm -rf FOO

