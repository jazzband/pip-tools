Setup:

  $ echo "requests" > requirements.txt
  $ echo "pip_tools\nwsgiref\nvim-bridge\ncram\n" > .pipignore
  $ cp .pipignore .pipignore.orig

When no files are specified, pip-dump will assume requirements.txt and
.pipignore:

  $ pip-dump 2>/dev/null
  $ cat requirements.txt
  requests==[0-9.]+ (re)

The .pipignore file is never updated:

  $ diff -q .pipignore .pipignore.orig

