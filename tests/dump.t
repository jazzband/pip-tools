Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-dump="$TESTDIR/../bin/pip-dump"

Setup:

  $ echo "python-dateutil" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-dump

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt | grep -v argparse
  python-dateutil==* (glob)
  six==* (glob)
