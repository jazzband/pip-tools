# Setup test environment.

virtualenv --python="$(which python)" VENV >/dev/null
PATH=$PWD/VENV/bin:$PATH
pip install 'pip>=6' > /dev/null 2>&1
pip install six >/dev/null 2>&1
export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
alias pip="pip --isolated"
pip install -e $TESTDIR/.. > /dev/null

mkdir -p .pip-tools
export PIPTOOLS_ROOT=$PWD/.pip-tools

# Export utf8 locale for click on Python 3.
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Use git without any user config.
orig_git=$(command -v git)
cat > VENV/bin/git <<EOF
#!/bin/sh
export GIT_CONFIG_NOSYSTEM=1
export HOME=/dev/null
$orig_git "\$@"
EOF
chmod +x VENV/bin/git
