Create a new playground first:

  $ . $TESTDIR/setup.sh

Let's create a simple requirements.in file:

  $ echo "raven==1.9.3" > requirements.in

Compiling yields the obvious result: it will lookup the dependencies, pick the
latest versions of them that yield no conflict, and pin them:

  $ pip-compile
  Dependencies updated.
  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.4.0

But what if we want to use simplejson==2.3.3 (which is also supported by
raven)?  Let's say we change the requirements.in file to reflect that:

  $ echo "raven==1.9.3" > requirements.in
  $ echo "simplejson==2.3.3" >> requirements.in

Now, recompiling should NOT change the file back to simplejson==2.4.0!

  $ pip-compile
  Dependencies updated.
  $ cat requirements.txt
  raven==1.9.3
  simplejson==2.3.3
