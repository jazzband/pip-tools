Create a new playground first:

  $ virtualenv FOO >/dev/null
  $ PATH=FOO/bin:$PATH

Setup:

  $ echo "times" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-dump

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt
  python-dateutil==* (glob)
  pytz==* (glob)
  six==* (glob)
  times==* (glob)
  wsgiref==* (glob)
