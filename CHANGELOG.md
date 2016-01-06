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
