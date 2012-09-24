Setup:

  $ 
  $ echo "requests" > foo.txt
  $ echo "pip_tools\nwsgiref\nvim-bridge\ncram\n" > bar.txt

Running pip-dump will update the given files:

  $ pip-dump foo.txt bar.txt 2>/dev/null
  $ cat foo.txt
  * (glob)
  requests==0.14.0
  $ cat bar.txt
  -e git+git@github.com:nvie/pip-tools.git@*#egg=pip_tools-dev (glob)
  cram==0.5
  vim-bridge==0.5
  wsgiref==0.1.2

Easy!

Rerunning pip-dump now will change nothing:

  $ pip-dump foo.txt bar.txt 2>/dev/null
  $ cat foo.txt
  * (glob)
  requests==0.14.0
  $ cat bar.txt
  -e git+git@github.com:nvie/pip-tools.git@*#egg=pip_tools-dev (glob)
  cram==0.5
  vim-bridge==0.5
  wsgiref==0.1.2

