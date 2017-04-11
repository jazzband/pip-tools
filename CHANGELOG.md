# 1.9.0rc1

Features:
- Added ability to read requirements from `setup.py` instead of just `requirements.in` ([#418](https://github.com/jazzband/pip-tools/pull/418)). Thanks to @tysonclugg and @majuscule.
- Added a `--max-rounds` argument to the pip-compile command to allow for solving large requirement sets ([#472](https://github.com/jazzband/pip-tools/pull/472)). Thanks @derek-miller.
- Exclude unsafe packages' dependencies when `--allow-unsafe` is not in use ([#441](https://github.com/jazzband/pip-tools/pull/441)). Thanks @jdufresne.
- Exclude irrelevant pip constraints ([#471](https://github.com/jazzband/pip-tools/pull/471)). Thanks @derek-miller.
- Allow control over emitting trusted-host to the compiled requirements. ([#448](https://github.com/jazzband/pip-tools/pull/448)). Thanks @tonyseek.
- Allow running as a Python module (#[461](https://github.com/jazzband/pip-tools/pull/461)). Thanks @AndreLouisCaron.
- Preserve environment markers in generated requirements.txt. ([#460](https://github.com/jazzband/pip-tools/pull/460)). Thanks @barrywhart.

Bug Fixes:
- Fixed the --upgrade-package option to respect the given package list to update ([#491](https://github.com/jazzband/pip-tools/pull/491)).
- Fixed the default output file name when the source file has no extension ([#488](https://github.com/jazzband/pip-tools/pull/488)). Thanks @vphilippon
- Fixed crash on editable requirements introduced in 1.8.2.
- Fixed duplicated --trusted-host, --extra-index-url and --index-url in the generated requirements.

# 1.8.2

- Regression fix: editable reqs were loosing their dependencies after first round ([#476](https://github.com/jazzband/pip-tools/pull/476))
  Thanks @mattlong
- Remove duplicate index urls in generated requirements.txt ([#468](https://github.com/jazzband/pip-tools/pull/468))
  Thanks @majuscule

# 1.8.1

- Recalculate secondary dependencies between rounds (#378)
- Calculated dependencies could be left with wrong candidates when 
  toplevel requirements happen to be also pinned in sub-dependencies (#450)
- Fix duplicate entries that could happen in generated requirements.txt (#427)
- Gracefully report invalid pip version (#457)
- Fix capitalization in the generated requirements.txt, packages will always be lowercased (#452)

# 1.8.0

- Adds support for upgrading individual packages with a new option
  `--upgrade-package`.  To upgrade a _specific_ package to the latest or
  a specific version use `--upgrade-package <pkg>`.  To upgrade all packages,
  you can still use `pip-compile --upgrade`.  (#409)
- Adds support for pinning dependencies even further by including the hashes
  found on PyPI at compilation time, which will be re-checked when dependencies
  are installed at installation time.  This adds protection against packages
  that are tampered with.  (#383)
- Improve support for extras, like `hypothesis[django]`
- Drop support for pip < 8


# 1.7.1

- Add `--allow-unsafe` option (#377)


# 1.7.0

- Add compatibility with pip >= 8.1.2 (#374)
  Thanks so much, @jmbowman!


# 1.6.5

- Add warning that pip >= 8.1.2 is not supported until 1.7.x is out


# 1.6.4

- Incorporate fix for atomic file saving behaviour on the Windows platform
  (see #351)


# 1.6.3

- PyPI won't let me upload 1.6.2


# 1.6.2

- Respect pip configuration from pip.{ini,conf}
- Fixes for atomic-saving of output files on Windows (see #351)


# 1.6.1

Minor changes:
- pip-sync now supports being invoked from within and outside an activated
  virtualenv (see #317)
- pip-compile: support -U as a shorthand for --upgrade
- pip-compile: support pip's --no-binary and --binary-only flags

Fixes:
- Change header format of output files to mention all input files


# 1.6

Major change:
- pip-compile will by default try to fulfill package specs by looking at
  a previously compiled output file first, before checking PyPI.  This means
  pip-compile will only update the requirements.txt when it absolutely has to.
  To get the old behaviour (picking the latest version of all packages from
  PyPI), use the new `--upgrade` option.

Minor changes:
- Bugfix where pip-compile would lose "via" info when on pip 8 (see #313)
- Ensure cache dir exists (see #315)


# 1.5

- Add support for pip >= 8
- Drop support for pip < 7
- Fix bug where `pip-sync` fails to uninstall packages if you're using the
  `--no-index` (or other) flags


# 1.4.5

- Add `--no-index` flag to `pip-compile` to avoid emitting `--index-url` into
  the output (useful if you have configured a different index in your global
  ~/.pip/pip.conf, for example)
- Fix: ignore stdlib backport packages, like `argparse`, when listing which
  packages will be installed/uninstalled (#286)
- Fix pip-sync failed uninstalling packages when using `--find-links` (#298)
- Explicitly error when pip-tools is used with pip 8.0+ (for now)


# 1.4.4

- Fix: unintended change in behaviour where packages installed by `pip-sync`
  could accidentally get upgraded under certain conditions, even though the
  requirements.txt would dictate otherwise (see #290)


# 1.4.3

- Fix: add `--index-url` and `--extra-index-url` options to `pip-sync`
- Fix: always install using `--upgrade` flag when running `pip-sync`


# 1.4.2

- Fix bug where umask was ignored when writing requirement files (#268)


# 1.4.1

- Fix bug where successive invocations of pip-sync with editables kept
  uninstalling/installing them (fixes #270)


# 1.4.0

- Add command line option -f / --find-links
- Add command line option --no-index
- Add command line alias -n (for --dry-run)
- Fix a unicode issue


# 1.3.0

- Support multiple requirement files to pip-compile
- Support requirements from stdin for pip-compile
- Support --output-file option on pip-compile, to redirect output to a file (or stdout)


# 1.2.0

- Add CHANGELOG :)
- Support pip-sync'ing editable requirements
- Support extras properly (i.e. package[foo] syntax)

(Anything before 1.2.0 was not recorded.)
