Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"

Let's create a simple requirements.in file:

  $ echo "raven==1.9.3" > requirements.in

Compiling yields the obvious result: it will lookup the dependencies, pick the
latest versions of them that yield no conflict, and pin them:

  $ pip-compile >/dev/null 2>&1
  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.4.0

But what if we want to use simplejson==2.3.3 (which is also supported by
raven)?  Let's say we change the requirements.txt file to reflect that:

  $ echo "raven==1.9.3" > requirements.txt
  $ echo "simplejson==2.3.3" >> requirements.txt

Now, recompiling should NOT change the file back to simplejson==2.4.0!

  $ pip-compile >/dev/null 2>&1
  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.3.3

In other words: the behaviour of pip-compile depends on what's already in
requirements.txt.
