Create a new playground first:

  $ cd $TESTDIR/..
  $ pip install virtualenv >/dev/null 2>&1
  $ virtualenv --python="$(which python)" FOO >/dev/null 2>&1
  $ PATH=FOO/bin:$PATH
  $ pip install --upgrade --force-reinstall 'pip' > /dev/null 2>&1
  $ pip install argparse >/dev/null 2>&1
  $ pip install packaging >/dev/null 2>&1
  $ pip install -U --force-reinstall argparse >/dev/null 2>&1
  $ pip install -U --force-reinstall wheel >/dev/null 2>&1
  $ function pip-review { python -m pip_review.__main__ $* ; }

Setup. Let's pretend we have some outdated package versions installed:

  $ pip install python-dateutil==1.5 >/dev/null 2>&1

Also install library, which caused warning message:

  $ pip install http://www.effbot.org/media/downloads/cElementTree-1.0.5-20051216.tar.gz >/dev/null 2>&1

Define a filter to strip the deprecation notice for Python 2.6:

  $ function strip_deprecation_notice {
  >     grep -v 'DEPRECATION: Python 2.6 is no longer supported' || true
  > }

Before our next test, let's just check that the Bash option pipefail works:

  $ set -o pipefail
  $ false | true
  [1]

Next, let's see what pip-review does:

  $ pip-review 2>&1 | strip_deprecation_notice
  python-dateutil==* is available (you have 1.5) (glob)

Or in raw mode:

  $ pip-review --raw 2>&1 | strip_deprecation_notice
  python-dateutil==* (glob)

We can also install these updates automatically:

  $ pip-review --auto >/dev/null 2>&1
  $ pip-review 2>&1 | strip_deprecation_notice
  Everything up-to-date

Next, let's test for regressions with older versions of pip:

  $ pip install --force-reinstall --upgrade pip\<6.0 >/dev/null 2>&1
  $ if python -c 'import sys; sys.exit(0 if sys.version_info < (3, 6) else 1)'; then
  >   rm -rf pip_review.egg-info  # prevents spurious editable in pip freeze
  >   pip-review
  > else
  >   echo Skipped
  > fi
  (Everything up-to-date|Skipped) (re)

Cleanup our playground:

  $ rm -rf FOO
