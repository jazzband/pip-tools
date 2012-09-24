Setup:

  $ echo "requests" > foo.txt
  $ echo "pip_tools\nwsgiref\nvim-bridge\ncram\n" > ignore.txt

Running pip-dump will update the given files:

  $ pip-dump foo.txt ignore.txt 2>/dev/null
  $ cat foo.txt
  requests==0.14.0
  $ cat ignore.txt
  -e git+git@github.com:nvie/pip-tools.git@*#egg=pip_tools-dev (glob)
  cram==0.5
  vim-bridge==0.5
  wsgiref==0.1.2

Easy!

Rerunning pip-dump now will change nothing:

  $ pip-dump foo.txt ignore.txt 2>/dev/null
  $ cat foo.txt
  requests==0.14.0
  $ cat ignore.txt
  -e git+git@github.com:nvie/pip-tools.git@*#egg=pip_tools-dev (glob)
  cram==0.5
  vim-bridge==0.5
  wsgiref==0.1.2

