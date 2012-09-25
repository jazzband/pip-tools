Create a new playground first:

  $ virtualenv FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ alias pip-dump="$TESTDIR/../bin/pip-dump"

Setup:

  $ echo "times" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1
  $ echo "Flask\nWerkzeug\nJinja2" > more-requirements.txt
  $ pip install -r more-requirements.txt >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-dump

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt
  python-dateutil==* (glob)
  pytz==* (glob)
  six==* (glob)
  times==* (glob)

  $ cat more-requirements.txt
  Flask==* (glob)
  Jinja2==* (glob)
  Werkzeug==* (glob)
