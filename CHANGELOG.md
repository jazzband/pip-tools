# 3.9.0 (2019-07-17)

Features:
- Print provenance information when `pip-compile` fails
([#837](https://github.com/jazzband/pip-tools/pull/837)). Thanks @jakevdp

Bug Fixes:
- Output all logging to stderr instead of stdout
([#834](https://github.com/jazzband/pip-tools/pull/834)). Thanks @georgek
- Fix output file update with `--dry-run` option in `pip-compile`
([#842](https://github.com/jazzband/pip-tools/pull/842)). Thanks @shipmints and @atugushev

# 3.8.0 (2019-06-06)

Features:
- Options `--upgrade` and `--upgrade-package` are no longer mutually exclusive
([#831](https://github.com/jazzband/pip-tools/pull/831)). Thanks @adamchainz

Bug Fixes:
- Fix `--generate-hashes` with bare VCS URLs
([#812](https://github.com/jazzband/pip-tools/pull/812)). Thanks @jcushman
- Fix issues with `UnicodeError` when installing `pip-tools` from source in some systems
([#816](https://github.com/jazzband/pip-tools/pull/816)). Thanks @AbdealiJK
- Respect `--pre` option in the input file
([#822](https://github.com/jazzband/pip-tools/pull/822)). Thanks @atugushev
- Option `--upgrade-package` now works even if the output file does not exist
([#831](https://github.com/jazzband/pip-tools/pull/831)). Thanks @adamchainz


# 3.7.0 (2019-05-09)

Features:
- Show progressbar on generation hashes in `pip-compile` verbose mode
([#743](https://github.com/jazzband/pip-tools/pull/743)). Thanks @atugushev
- Add options `--cert` and `--client-cert` to `pip-sync`
([#798](https://github.com/jazzband/pip-tools/pull/798)). Thanks @atugushev
- Add support for `--find-links` in `pip-compile` output
([#793](https://github.com/jazzband/pip-tools/pull/793)). Thanks @estan and @atugushev
- Normalize «command to run» in `pip-compile` headers
([#800](https://github.com/jazzband/pip-tools/pull/800)). Thanks @atugushev
- Support URLs as packages
([#807](https://github.com/jazzband/pip-tools/pull/807)). Thanks @jcushman, @nim65s and @toejough

Bug Fixes:
- Fix replacing password to asterisks in `pip-compile`
([#808](https://github.com/jazzband/pip-tools/pull/808)). Thanks @atugushev

# 3.6.1 (2019-04-24)

Bug Fixes:
- Fix `pip>=19.1` compatibility
([#795](https://github.com/jazzband/pip-tools/pull/795)). Thanks @atugushev

# 3.6.0 (2019-04-03)

Features:
- Show less output on `pip-sync` with `--quiet` option
([#765](https://github.com/jazzband/pip-tools/pull/765)). Thanks @atugushev
- Support the flag `--trusted-host` in `pip-sync`
([#777](https://github.com/jazzband/pip-tools/pull/777)). Thanks @firebirdberlin

# 3.5.0 (2019-03-13)

Features:
- Show default index url provided by `pip`
([#735](https://github.com/jazzband/pip-tools/pull/735)). Thanks @atugushev
- Add an option to allow enabling/disabling build isolation
([#758](https://github.com/jazzband/pip-tools/pull/758)). Thanks @atugushev

Bug Fixes:
- Fix the output file for `pip-compile` with an explicit `setup.py` as source file
([#731](https://github.com/jazzband/pip-tools/pull/731)). Thanks @atugushev
- Fix order issue with generated lock file when `hashes` and `markers` are used together
([#763](https://github.com/jazzband/pip-tools/pull/763)). Thanks @milind-shakya-sp

# 3.4.0 (2019-02-19)

Features:
- Add option `--quiet` to `pip-compile`
([#720](https://github.com/jazzband/pip-tools/pull/720)). Thanks @bendikro
- Emit the original command to the `pip-compile`'s header
([#733](https://github.com/jazzband/pip-tools/pull/733)). Thanks @atugushev

Bug Fixes:
- Fix `pip-sync` to use pip script depending on a python version
([#737](https://github.com/jazzband/pip-tools/pull/737)). Thanks @atugushev

# 3.3.2 (2019-01-26)

Bug Fixes:
- Fix `pip-sync` with a temporary requirement file on Windows
([#723](https://github.com/jazzband/pip-tools/pull/723)). Thanks @atugushev
- Fix `pip-sync` to prevent uninstall of stdlib and dev packages
([#718](https://github.com/jazzband/pip-tools/pull/718)). Thanks @atugushev

# 3.3.1 (2019-01-24)

- Re-release of 3.3.0 after fixing the deployment pipeline
([#716](https://github.com/jazzband/pip-tools/issues/716)). Thanks @atugushev

# 3.3.0 (2019-01-23)
(Unreleased - Deployment pipeline issue, see 3.3.1)

Features:
- Added support of `pip` 19.0
([#715](https://github.com/jazzband/pip-tools/pull/715)). Thanks @atugushev
- Add `--allow-unsafe` to update instructions in the generated `requirements.txt`
([#708](https://github.com/jazzband/pip-tools/pull/708)). Thanks @richafrank

Bug Fixes:
- Fix `pip-sync` to check hashes
([#706](https://github.com/jazzband/pip-tools/pull/706)). Thanks @atugushev

# 3.2.0 (2018-12-18)

Features:
- Apply version constraints specified with package upgrade option (`-P, --upgrade-package`)
([#694](https://github.com/jazzband/pip-tools/pull/694)). Thanks @richafrank

# 3.1.0 (2018-10-05)

Features:
- Added support of `pip` 18.1
([#689](https://github.com/jazzband/pip-tools/pull/689)). Thanks @vphilippon

# 3.0.0 (2018-09-24)

Major changes:
- Update `pip-tools` for native `pip` 8, 9, 10 and 18 compatibility, un-vendoring `pip` to use the user-installed `pip`
([#657](https://github.com/jazzband/pip-tools/pull/657) and [#672](https://github.com/jazzband/pip-tools/pull/672)).
Thanks to @techalchemy, @suutari, @tysonclugg and @vphilippon for contributing on this.

Features:
- Removed the dependency on the external library `first`
([#676](https://github.com/jazzband/pip-tools/pull/676)). Thanks @jdufresne

# 2.0.2 (2018-04-28)

Bug Fixes:
- Added clearer error reporting when skipping pre-releases
([#655](https://github.com/jazzband/pip-tools/pull/655)). Thanks @WoLpH

# 2.0.1 (2018-04-15)

Bug Fixes:
- Added missing package data from vendored pip, such as missing cacert.pem file. Thanks @vphilippon

# 2.0.0 (2018-04-15)
 
Major changes:
- Vendored `pip` 9.0.3 to keep compatibility for users with `pip` 10.0.0
([#644](https://github.com/jazzband/pip-tools/pull/644)). Thanks @vphilippon

Features:
- Improved the speed of pip-compile --generate-hashes by caching the hashes from an existing output file
([#641](https://github.com/jazzband/pip-tools/pull/641)). Thanks @justicz
- Added a `pip-sync --user` option to restrict attention to user-local directory
([#642](https://github.com/jazzband/pip-tools/pull/642)). Thanks @jbergknoff-10e
- Removed the hard dependency on setuptools
([#645](https://github.com/jazzband/pip-tools/pull/645)). Thanks @vphilippon

Bug fixes:
- The pip environment markers on top-level requirements in the source file (requirements.in)
are now properly handled and will only be processed in the right environment
([#647](https://github.com/jazzband/pip-tools/pull/647)). Thanks @JoergRittinger

# 1.11.0 (2017-11-30)

Features:
- Allow editable packages in requirements.in with `pip-compile --generate-hashes` ([#524](https://github.com/jazzband/pip-tools/pull/524)). Thanks @jdufresne
- Allow for CA bundles with `pip-compile --cert` ([#612](https://github.com/jazzband/pip-tools/pull/612)). Thanks @khwilson
- Improved `pip-compile` duration with large locally available editable requirement by skipping a copy to the cache
([#583](https://github.com/jazzband/pip-tools/pull/583)). Thanks @costypetrisor
- Slightly improved the `NoCandidateFound` error message on potential causes ([#614](https://github.com/jazzband/pip-tools/pull/614)). Thanks @vphilippon

Bug Fixes:
- Add `-markerlib` to the list of `PACKAGES_TO_IGNORE` of `pip-sync` ([#613](https://github.com/jazzband/pip-tools/pull/613)).

# 1.10.2 (2017-11-22)

Bug Fixes:
- Fixed bug causing dependencies from invalid wheels for the current platform to be included ([#571](https://github.com/jazzband/pip-tools/pull/571)).
- `pip-sync` will respect environment markers in the requirements.txt ([600](https://github.com/jazzband/pip-tools/pull/600)). Thanks @hazmat345
- Converted the ReadMe to have a nice description rendering on PyPI. Thanks @bittner

# 1.10.1 (2017-09-27)

Bug Fixes:
- Fixed bug breaking `pip-sync` on Python 3, raising `TypeError: '<' not supported between instances of 'InstallRequirement' and 'InstallRequirement'` ([#570](https://github.com/jazzband/pip-tools/pull/570)).

# 1.10.0 (2017-09-27)

Features:
- `--generate-hashes` now generates hashes for all wheels,
not only wheels for the currently running platform ([#520](https://github.com/jazzband/pip-tools/pull/520)). Thanks @jdufresne
- Added a `-q`/`--quiet` argument to the pip-sync command to reduce log output.

Bug Fixes:
- Fixed bug where unsafe packages would get pinned in generated requirements files
when `--allow-unsafe` was not set. ([#517](https://github.com/jazzband/pip-tools/pull/517)). Thanks @dschaller
- Fixed bug where editable PyPI dependencies would have a `download_dir` and be exposed to `git-checkout-index`,
(thus losing their VCS directory) and `python setup.py egg_info` fails. ([#385](https://github.com/jazzband/pip-tools/pull/385#) and [#538](https://github.com/jazzband/pip-tools/pull/538)). Thanks @blueyed and @dfee
- Fixed bug where some primary dependencies were annotated with "via" info comments. ([#542](https://github.com/jazzband/pip-tools/pull/542)). Thanks @quantus
- Fixed bug where pkg-resources would be removed by pip-sync in Ubuntu. ([#555](https://github.com/jazzband/pip-tools/pull/555)). Thanks @cemsbr
- Fixed bug where the resolver would sometime not stabilize on requirements specifying extras. ([#566](https://github.com/jazzband/pip-tools/pull/566)). Thanks @vphilippon
- Fixed an unicode encoding error when distribution package contains non-ASCII file names ([#567](https://github.com/jazzband/pip-tools/pull/567)). Thanks @suutari
- Fixed package hashing doing unnecessary unpacking ([#557](https://github.com/jazzband/pip-tools/pull/557)). Thanks @suutari-ai

# 1.9.0 (2017-04-12)

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

# 1.8.2 (2017-03-28)

- Regression fix: editable reqs were loosing their dependencies after first round ([#476](https://github.com/jazzband/pip-tools/pull/476))
  Thanks @mattlong
- Remove duplicate index urls in generated requirements.txt ([#468](https://github.com/jazzband/pip-tools/pull/468))
  Thanks @majuscule

# 1.8.1 (2017-03-22)

- Recalculate secondary dependencies between rounds (#378)
- Calculated dependencies could be left with wrong candidates when
  toplevel requirements happen to be also pinned in sub-dependencies (#450)
- Fix duplicate entries that could happen in generated requirements.txt (#427)
- Gracefully report invalid pip version (#457)
- Fix capitalization in the generated requirements.txt, packages will always be lowercased (#452)

# 1.8.0 (2016-11-17)

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


# 1.7.1 (2016-10-20)

- Add `--allow-unsafe` option (#377)


# 1.7.0 (2016-07-06)

- Add compatibility with pip >= 8.1.2 (#374)
  Thanks so much, @jmbowman!


# 1.6.5 (2016-05-11)

- Add warning that pip >= 8.1.2 is not supported until 1.7.x is out


# 1.6.4 (2016-05-03)

- Incorporate fix for atomic file saving behaviour on the Windows platform
  (see #351)


# 1.6.3 (2016-05-02)

- PyPI won't let me upload 1.6.2


# 1.6.2 (2016-05-02)

- Respect pip configuration from pip.{ini,conf}
- Fixes for atomic-saving of output files on Windows (see #351)


# 1.6.1 (2016-04-06)

Minor changes:
- pip-sync now supports being invoked from within and outside an activated
  virtualenv (see #317)
- pip-compile: support -U as a shorthand for --upgrade
- pip-compile: support pip's --no-binary and --binary-only flags

Fixes:
- Change header format of output files to mention all input files


# 1.6 (2016-02-05)

Major change:
- pip-compile will by default try to fulfill package specs by looking at
  a previously compiled output file first, before checking PyPI.  This means
  pip-compile will only update the requirements.txt when it absolutely has to.
  To get the old behaviour (picking the latest version of all packages from
  PyPI), use the new `--upgrade` option.

Minor changes:
- Bugfix where pip-compile would lose "via" info when on pip 8 (see #313)
- Ensure cache dir exists (see #315)


# 1.5 (2016-01-23)

- Add support for pip >= 8
- Drop support for pip < 7
- Fix bug where `pip-sync` fails to uninstall packages if you're using the
  `--no-index` (or other) flags


# 1.4.5 (2016-01-20)

- Add `--no-index` flag to `pip-compile` to avoid emitting `--index-url` into
  the output (useful if you have configured a different index in your global
  ~/.pip/pip.conf, for example)
- Fix: ignore stdlib backport packages, like `argparse`, when listing which
  packages will be installed/uninstalled (#286)
- Fix pip-sync failed uninstalling packages when using `--find-links` (#298)
- Explicitly error when pip-tools is used with pip 8.0+ (for now)


# 1.4.4 (2016-01-11)

- Fix: unintended change in behaviour where packages installed by `pip-sync`
  could accidentally get upgraded under certain conditions, even though the
  requirements.txt would dictate otherwise (see #290)


# 1.4.3 (2016-01-06)

- Fix: add `--index-url` and `--extra-index-url` options to `pip-sync`
- Fix: always install using `--upgrade` flag when running `pip-sync`


# 1.4.2 (2015-12-13)

- Fix bug where umask was ignored when writing requirement files (#268)


# 1.4.1 (2015-12-13)

- Fix bug where successive invocations of pip-sync with editables kept
  uninstalling/installing them (fixes #270)


# 1.4.0 (2015-12-13)

- Add command line option -f / --find-links
- Add command line option --no-index
- Add command line alias -n (for --dry-run)
- Fix a unicode issue


# 1.3.0 (2015-12-08)

- Support multiple requirement files to pip-compile
- Support requirements from stdin for pip-compile
- Support --output-file option on pip-compile, to redirect output to a file (or stdout)


# 1.2.0 (2015-11-30)

- Add CHANGELOG :)
- Support pip-sync'ing editable requirements
- Support extras properly (i.e. package[foo] syntax)

(Anything before 1.2.0 was not recorded.)
