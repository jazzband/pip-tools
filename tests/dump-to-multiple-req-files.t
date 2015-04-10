Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-dump="$TESTDIR/../bin/pip-dump"
  $ mkdir requirements

Setup:

  $ echo "python-dateutil" > requirements.txt
  $ pip install -r requirements.txt >/dev/null 2>&1
  $ echo "Flask" > more-requirements.txt
  $ echo "Werkzeug" >> more-requirements.txt
  $ echo "Jinja2==2.6" >> more-requirements.txt
  $ pip install -r more-requirements.txt >/dev/null 2>&1
  $ echo "pep8" > requirements/develop.txt
  $ pip install -r requirements/develop.txt >/dev/null 2>&1
  $ echo "bpython" > requirements-prod-debug.txt
  $ echo "Pygments" >> requirements-prod-debug.txt
  $ pip install -r requirements-prod-debug.txt >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-dump

It should've updated requirements.txt with pinned versions of all requirements:

  $ cat requirements.txt | grep -v argparse
  blessings==* (glob)
  curtsies==* (glob)
  greenlet==* (glob)
  itsdangerous==* (glob)
  python-dateutil==* (glob)
  requests==* (glob)
  six==* (glob)

  $ cat more-requirements.txt
  Flask==* (glob)
  Jinja2==* (glob)
  Werkzeug==* (glob)

  $ cat requirements/develop.txt
  pep8==* (glob)

  $ cat requirements-prod-debug.txt
  bpython==* (glob)
  Pygments==* (glob)

Cleanup our playground:

  $ rm -rf FOO
