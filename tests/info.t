Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ pip install ordereddict >/dev/null 2>&1
  $ alias pip-info="$TESTDIR/../bin/pip-info"

Next, let's see what pip-info does:

  $ pip-info pep8
  Package name: \tpep8 (esc)
  Home page: \thttp://pep8.readthedocs.org/ (esc)
  Documentation: \tNone (esc)
  Summary: \tPython style guide checker (esc)
  Version: * (glob)
  PyPI page: \thttp://pypi.python.org/pypi/pep8 (esc)
