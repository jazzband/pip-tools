Setup:

  $ echo "requests" > requirements.txt
  $ echo "ipython" > dev-requirements.txt
  $ echo "pip_tools\nwsgiref\nvim-bridge\ncram\n" > .pipignore
  $ cp .pipignore .pipignore.orig

When no files are specified, pip-dump will assume requirements.txt,
*requirements.txt and .pipignore, in that order:

  $ pip-dump 2>/dev/null
  $ cat requirements.txt
  requests==[0-9.]+ (re)
  $ cat dev-requirements.txt
  ipython==[0-9.]+ (re)

The .pipignore file is never updated:

  $ diff -q .pipignore .pipignore.orig

