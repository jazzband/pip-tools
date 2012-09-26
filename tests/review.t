Create a new playground first:

  $ virtualenv FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ alias pip-review="$TESTDIR/../bin/pip-review"

Setup. Let's pretend we have some outdated package versions installed:

  $ pip install times==0.2 >/dev/null 2>&1

Next, let's see what pip-dump does:

  $ pip-review
  times==0.5 is available (you have 0.2)

Or in raw mode:

  $ pip-review --raw
  times==0.5

We can also install these updates automatically:

  $ pip-review --auto >/dev/null 2>&1
  $ pip-review
  Everything up-to-date
