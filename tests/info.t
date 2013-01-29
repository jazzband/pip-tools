Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-info="$TESTDIR/../bin/pip-info"

Next, let's see what pip-info does:

  $ pip-info pep8
  Package name: 	pep8
  Home page: 	http://pep8.readthedocs.org/
  Documentation: 	None
  Summary: 	Python style guide checker
  Version: 	* (glob)
  PyPI page: 	http://pypi.python.org/pypi/pep8
