<!-- towncrier release notes start -->

## v7.5.1

*2025-09-26*

### Bug fixes

- Fixed static parsing of {file}`pyproject.toml` data when the
  {file}`pyproject.toml` is supplied as a relative path -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2215`, {issue}`2221`, {issue}`2233`

- The "via" paths in `pip-compile` output for requirements discovered from
  `pyproject.toml` data are now written in POSIX format -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2221`

- Fixed a bug which removed slashes from URLs in ``-r`` and ``-c`` in the output
  of ``pip-compile`` -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2223`

- Fixed an incompatibility with ``click >= 8.3`` which made ``pip-compile`` display incorrect
  options in the compile command in output headers -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2235`

### Features

- `pip-tools` now officially supports `pip` version 25.2 -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2214`

### Improved documentation

- ReadTheDocs builds for `pip-tools` no longer include htmlzip and pdf outputs -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2218`

### Contributor-facing changes

- `pip-tools` now tests on `pip` version 25.2 -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2214`

- The changelog documentation for contributors now provides hyperlinks to the source of each example change note -- by {user}`jayaddison` (for OpenCulinary).

  *PRs and issues:* {issue}`2217`

- The CPython versions tested in nightly CI runs are now separate from
  branch and PR CI, and don't include very old versions -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2226`


## v7.5.0

*2025-07-30*

### Bug fixes

- Fixed the ordering of format controls to preserve underlying `pip` behavior
  -- by {user}`sethmlarson`.

  *PRs and issues:* {issue}`2082`

- Fixed `NoCandidateFound` exception to be compatible with `pip >= 24.1`
  -- by {user}`chrysle`.

  *PRs and issues:* {issue}`2083`

- `pip-compile` now produces relative paths for editable dependencies
  -- by {user}`macro1`.

  *PRs and issues:* {issue}`2087`

- Fixed crash failures due to incompatibility with `pip >= 25.1`
  -- by {user}`gkreitz` and {user}`sirosen`.

  *PRs and issues:* {issue}`2176`, {issue}`2178`

### Features

- `pip-compile` now treats package versions requested on the command line as
  constraints for the underlying `pip` usage.
  This applies to build deps in addition to normal package requirements.

  -- by {user}`chrysle`

  *PRs and issues:* {issue}`2106`

- `pip-tools` now tests on and officially supports Python 3.12
  -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2188`

- Requirements file paths in `pip-compile` output are now normalized to
  POSIX-style, even when `pip-compile` is run on Windows.
  This provides more consistent output across various platforms.

  -- by {user}`sirosen`

  *PRs and issues:* {issue}`2195`

- `pip-tools` now tests against and supports `pip` up to version `25.1`
  -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2195`

### Removals and backward incompatible breaking changes

- `pip-compile` will now relativize the requirements paths which are recorded in
  its output.
  Paths are made relative to the working directory.
  This provides more consistent results across `pip` versions.

  -- by {user}`sirosen`

  *PRs and issues:* {issue}`2131`, {issue}`2195`

### Packaging updates and notes for downstreams

- `pip-tools` releases are now configured via Trusted Publishing.
  This allows for signature and attestation verification via PyPI.

  -- by {user}`webknjaz`

  *PRs and issues:* {issue}`2149`, {issue}`2209`, {issue}`2210`

### Contributor-facing changes

- `pip-tools`'s CI now runs against pinned `pip` versions, declared in `tox`
  configuration as the "supported" version.
  This does not change the support policy for `pip` versions, but declares what
  is tested and known to work.

  -- by {user}`webknjaz`

  *PRs and issues:* {issue}`2142`

- `pip-tools` now tests against PyPy 3.10 as its supported PyPy version
  -- by {user}`webknjaz`.

  *PRs and issues:* {issue}`2146`

- `pip-tools` now uses Towncrier to manage the changelog
  -- by {user}`sirosen` and {user}`webknjaz`,
  with suggestions from {user}`jayaddison`.

  *PRs and issues:* {issue}`2201`, {issue}`2203`

- `pip-tools` now uses [`sphinx-issues`](https://github.com/sloria/sphinx-issues)
  to link to issues, PRs, commits, and user accounts
  -- by {user}`sirosen`.

  *PRs and issues:* {issue}`2202`


## v7.4.1

*05 Mar 2024*

### Bug Fixes

- Skip constraint path check ({pr}`2038`)
  -- by {user}`honnix`.
- Fix collecting deps for all extras in multiple input packages ({pr}`1981`)
  -- by {user}`dragly`.

## v7.4.0

*16 Feb 2024*

### Features

- Allow force-enabling or force-disabling colorized output ({pr}`2041`)
  -- by {user}`aneeshusa`.
- Add support for command-specific configuration sections ({pr}`1966`)
  -- by {user}`chrysle`.
- Add options for including build dependencies in compiled output ({pr}`1681`)
  -- by {user}`apljungquist`.

### Bug Fixes

- Fix for `src-files` not being used when specified in a config file ({pr}`2015`)
  -- by {user}`csalerno-asml`.
- Fix ignorance of inverted CLI options in config for `pip-sync` ({pr}`1989`)
  -- by {user}`chrysle`.
- Filter out origin ireqs for extra requirements before writing output annotations ({pr}`2011`)
  -- by {user}`chrysle`.
- Make BacktrackingResolver ignore extras when dropping existing constraints ({pr}`1984`)
  -- by {user}`chludwig-haufe`.
- Display `pyproject.toml`'s metatada parsing errors in verbose mode ({pr}`1979`)
  -- by {user}`szobov`.

### Other Changes

- Add mention of pip-compile-multi in Other useful tools README section ({pr}`1986`)
  -- by {user}`peterdemin`.

## v7.3.0

*09 Aug 2023*

### Features

- Add `--no-strip-extras` and warn about strip extras by default ({pr}`1954`)
  -- by {user}`ryanhiebert`.

### Bug Fixes

- Fix revealed default config in header if requirements in subfolder ({pr}`1904`)
  -- by {user}`atugushev`.
- Direct references show extra requirements in .txt files ({pr}`1582`)
  -- by {user}`FlorentJeannot`.

### Other Changes

- Document how to run under `pipx run` ({pr}`1951`)
  -- by {user}`brettcannon`.
- Document that the backtracking resolver is the current default ({pr}`1948`)
  -- by {user}`jeffwidman`.

## v7.2.0

*02 Aug 2023*

### Features

- Add `-c/--constraint` option to `pip-compile` ({pr}`1936`)
  -- by {user}`atugushev`.

### Bug Fixes

- Allow options in config from both `pip-compile` and `pip-sync` ({pr}`1933`)
  -- by {user}`atugushev`.
- Fix rejection of negating CLI boolean flags in config ({pr}`1913`)
  -- by {user}`chrysle`.

### Other Changes

- Add Command Line Reference section to docs ({pr}`1934`)
  -- by {user}`atugushev`.

## v7.1.0

*18 Jul 2023*

### Features

- Validate parsed config against CLI options ({pr}`1910`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix a bug where `pip-sync` would unexpectedly uninstall some packages ({pr}`1919`)
  -- by {user}`atugushev`.

## v7.0.0

*14 Jul 2023*

### Backwards Incompatible Changes

- Default to `--resolver=backtracking` ({pr}`1897`)
  -- by {user}`atugushev`.
- Drop support for Python 3.7 ({pr}`1879`)
  -- by {user}`chrysle`.

### Features

- Add support for `pip==23.2` where refactored out `DEV_PKGS` ({pr}`1906`)
  -- by {user}`atugushev`.
- Add `--no-config` option ({pr}`1896`)
  -- by {user}`atugushev`.

### Bug Fixes

- Sync direct references with hashes ({pr}`1885`)
  -- by {user}`siddharthab`.
- Fix missing `via`s when more than two input files are used ({pr}`1890`)
  -- by {user}`lpulley`.

## v6.14.0

*28 Jun 2023*

### Features

- Support config defaults using `.pip-tools.toml` or `pyproject.toml` ({pr}`1863`)
  -- by {user}`j00bar`.
- Log a warning if the user specifies `-P` and the output file is present but empty ({pr}`1822`)
  -- by {user}`davidmreed`.
- Improve warning for `pip-compile` if no `--allow-unsafe` was passed ({pr}`1867`)
  -- by {user}`chrysle`.

### Other Changes

- Correct in README `pre-commit` hook to run off `requirements.in` ({pr}`1847`)
  -- by {user}`atugushev`.
- Add pyprojects.toml example for using setuptools ({pr}`1851`)
  -- by {user}`shatakshiiii`.

## v6.13.0

*07 Apr 2023*

### Features

- Add support for self-referential extras ({pr}`1791`)
  -- by {user}`q0w`.
- Add support for `pip==23.1` where removed `FormatControl` in `WheelCache` ({pr}`1834`)
  -- by {user}`atugushev`.
- Add support for `pip==23.1` where refactored requirement options ({pr}`1832`)
  -- by {user}`atugushev`.
- Add support for `pip==23.1` where deprecated `--install-option` has been removed ({pr}`1828`)
  -- by {user}`atugushev`.

### Bug Fixes

- Pass `--cache-dir` to `--pip-args` for backtracking resolver ({pr}`1827`)
  -- by {user}`q0w`.

### Other Changes

- Update examples in README ({pr}`1835`)
  -- by {user}`lucaswerkmeister`.

## v6.12.3

*01 Mar 2023*

### Bug Fixes

- Remove extras from user-supplied constraints in backtracking resolver ({pr}`1808`)
  -- by {user}`thomdixon`.
- Fix for sync error when the ireqs being merged have no names ({pr}`1802`)
  -- by {user}`richafrank`.

## v6.12.2

*25 Dec 2022*

### Bug Fixes

- Raise error if input and output filenames are matched ({pr}`1787`)
  -- by {user}`atugushev`.
- Add `pyproject.toml` as default input file format ({pr}`1780`)
  -- by {user}`berislavlopac`.
- Fix a regression with unsafe packages for `--allow-unsafe` ({pr}`1788`)
  -- by {user}`q0w`.

## v6.12.1

*16 Dec 2022*

### Bug Fixes

- Set explicitly packages for setuptools ({pr}`1782`)
  -- by {user}`q0w`.

## v6.12.0

*13 Dec 2022*

### Features

- Add `--no-index` flag to `pip-compile` ({pr}`1745`)
  -- by {user}`atugushev`.

### Bug Fixes

- Treat `--upgrade-packages` PKGSPECs as constraints (not just minimums), consistently ({pr}`1578`)
  -- by {user}`AndydeCleyre`.
- Filter out the user provided unsafe packages ({pr}`1766`)
  -- by {user}`q0w`.
- Adopt PEP-621 for packaging ({pr}`1763`)
  -- by {user}`ssbarnea`.

## v6.11.0

*30 Nov 2022*

### Features

- Add `pyproject.toml` file ({pr}`1643`)
  -- by {user}`otherJL0`.
- Support build isolation using `setuptools/pyproject.toml` requirement files ({pr}`1727`)
  -- by {user}`atugushev`.

### Bug Fixes

- Improve punctuation/grammar with `pip-compile` header ({pr}`1547`)
  -- by {user}`blueyed`.
- Generate hashes for all available candidates ({pr}`1723`)
  -- by {user}`neykov`.

### Other Changes

- Bump click minimum version to `>= 8` ({pr}`1733`)
  -- by {user}`atugushev`.
- Bump pip minimum version to `>= 22.2` ({pr}`1729`)
  -- by {user}`atugushev`.

## v6.10.0

*13 Nov 2022*

### Features

- Deprecate `pip-compile --resolver=legacy` ({pr}`1724`)
  -- by {user}`atugushev`.
- Prompt user to use the backtracking resolver on errors ({pr}`1719`)
  -- by {user}`maxfenv`.
- Add support for Python 3.11 final ({pr}`1708`)
  -- by {user}`hugovk`.
- Add `--newline=[LF|CRLF|native|preserve]` option to `pip-compile` ({pr}`1652`)
  -- by {user}`AndydeCleyre`.

### Bug Fixes

- Fix inconsistent handling of constraints comments with backtracking resolver ({pr}`1713`)
  -- by {user}`mkniewallner`.
- Fix some encoding warnings in Python 3.10 (PEP 597) ({pr}`1614`)
  -- by {user}`GalaxySnail`.

### Other Changes

- Update pip-tools version in the README's pre-commit examples ({pr}`1701`)
  -- by {user}`Kludex`.
- Document use of the backtracking resolver ({pr}`1718`)
  -- by {user}`maxfenv`.
- Use HTTPS in a readme link ({pr}`1716`)
  -- by {user}`Arhell`.

## v6.9.0

*05 Oct 2022*

### Features

- Add `--all-extras` flag to `pip-compile` ({pr}`1630`)
  -- by {user}`apljungquist`.
- Support Exclude Package with custom unsafe packages ({pr}`1509`)
  -- by {user}`hmc-cs-mdrissi`.

### Bug Fixes

- Fix compile cached vcs packages ({pr}`1649`)
  -- by {user}`atugushev`.
- Include `py.typed` in wheel file ({pr}`1648`)
  -- by {user}`FlorentJeannot`.

### Other Changes

- Add pyproject.toml & modern packaging to introduction ({pr}`1668`)
  -- by {user}`hynek`.

## v6.8.0

*30 Jun 2022*

### Features

- Add support for pip's 2020 dependency resolver. Use
  `pip-compile --resolver backtracking` to enable new resolver ({pr}`1539`)
  -- by {user}`atugushev`.

## v6.7.0

*27 Jun 2022*

### Features

- Support for the `importlib.metadata` metadata implementation ({pr}`1632`)
  -- by {user}`richafrank`.

### Bug Fixes

- Instantiate a new accumulator `InstallRequirement` for `combine_install_requirements`
  output ({pr}`1519`)
  -- by {user}`richafrank`.

### Other Changes

- Replace direct usage of the `pep517` module with the `build` module, for loading
  project metadata ({pr}`1629`)
  -- by {user}`AndydeCleyre`.

## v6.6.2

*23 May 2022*

### Bug Fixes

- Update `PyPIRepository::resolve_reqs()` for pip>=22.1.1 ({pr}`1624`)
  -- by {user}`m000`.

## v6.6.1

*13 May 2022*

### Bug Fixes

- Fix support for pip>=22.1 ({pr}`1618`)
  -- by {user}`wizpig64`.

## v6.6.0

*06 Apr 2022*

### Features

- Add support for pip>=22.1 ({pr}`1607`)
  -- by {user}`atugushev`.

### Bug Fixes

- Ensure `pip-compile --dry-run --quiet` still shows what would be done, while omitting
  the dry run message ({pr}`1592`)
  -- by {user}`AndydeCleyre`.
- Fix `--generate-hashes` when hashes are computed from files ({pr}`1540`)
  -- by {user}`RazerM`.

## v6.5.1

*08 Feb 2022*

### Bug Fixes

- Ensure canonicalized requirement names are used as keys, to prevent unnecessary
  reinstallations during sync ({pr}`1572`)
  -- by {user}`AndydeCleyre`.

## v6.5.0

*04 Feb 2022*

### Features

- Add support for pip>=22.0, drop support for Python 3.6 ({pr}`1567`)
  -- by {user}`di`.
- Test on Python 3.11 ({pr}`1527`)
  -- by {user}`hugovk`.

### Other Changes

- Minor doc edits ({pr}`1445`)
  -- by {user}`ssiano`.

## v6.4.0

*12 Oct 2021*

### Features

- Add support for `pip>=21.3` ({pr}`1501`)
  -- by {user}`atugushev`.
- Add support for Python 3.10 ({pr}`1497`)
  -- by {user}`joshuadavidthomas`.

### Other Changes

- Bump pip minimum version to `>= 21.2` ({pr}`1500`)
  -- by {user}`atugushev`.

## v6.3.1

*08 Oct 2021*

### Bug Fixes

- Ensure `pip-tools` unions dependencies of multiple declarations of a package with
  different extras ({pr}`1486`)
  -- by {user}`richafrank`.
- Allow comma-separated arguments for `--extra` ({pr}`1493`)
  -- by {user}`AndydeCleyre`.
- Improve clarity of help text for options supporting multiple ({pr}`1492`)
  -- by {user}`AndydeCleyre`.

## v6.3.0

*21 Sep 2021*

### Features

- Enable single-line annotations with `pip-compile --annotation-style=line` ({pr}`1477`)
  -- by {user}`AndydeCleyre`.
- Generate PEP 440 direct reference whenever possible ({pr}`1455`)
  -- by {user}`FlorentJeannot`.
- PEP 440 Direct Reference support ({pr}`1392`)
  -- by {user}`FlorentJeannot`.

### Bug Fixes

- Change log level of hash message ({pr}`1460`)
  -- by {user}`plannigan`.
- Allow passing `--no-upgrade` option ({pr}`1438`)
  -- by {user}`ssbarnea`.

## v6.2.0

*22 Jun 2021*

### Features

- Add `--emit-options/--no-emit-options` flags to `pip-compile` ({pr}`1123`)
  -- by {user}`atugushev`.
- Add `--python-executable` option for `pip-sync` ({pr}`1333`)
  -- by {user}`MaratFM`.
- Log which python version was used during compile ({pr}`828`)
  -- by {user}`graingert`.

### Bug Fixes

- Fix `pip-compile` package ordering ({pr}`1419`)
  -- by {user}`adamsol`.
- Add `--strip-extras` option to `pip-compile` for producing constraint compatible
  output ({pr}`1404`)
  -- by {user}`ssbarnea`.
- Fix `click` v7 `version_option` compatibility ({pr}`1410`)
  -- by {user}`FuegoFro`.
- Pass `package_name` explicitly in `click.version_option` decorators for compatibility
  with `click>=8.0` ({pr}`1400`)
  -- by {user}`nicoa`.

### Other Changes

- Document updating requirements with `pre-commit` hooks ({pr}`1387`)
  -- by {user}`microcat49`.
- Add `setuptools` and `wheel` dependencies to the `setup.cfg` ({pr}`889`)
  -- by {user}`jayvdb`.
- Improve instructions for new contributors ({pr}`1394`)
  -- by {user}`FlorentJeannot`.
- Better explain role of existing `requirements.txt` ({pr}`1369`)
  -- by {user}`mikepqr`.

## v6.1.0

*14 Apr 2021*

### Features

- Add support for `pyproject.toml` or `setup.cfg` as input dependency file (PEP-517) for
  `pip-compile` ({pr}`1356`)
  -- by {user}`orsinium`.
- Add `pip-compile --extra` option to specify `extras_require` dependencies ({pr}`1363`)
  -- by {user}`orsinium`.

### Bug Fixes

- Restore ability to set compile cache with env var `PIP_TOOLS_CACHE_DIR` ({pr}`1368`)
  -- by {user}`AndydeCleyre`.

## v6.0.1

*15 Mar 2021*

### Bug Fixes

- Fixed a bug with undeclared dependency on `importlib-metadata` at Python 3.6 ({pr}`1353`)
  -- by {user}`atugushev`.

### Dependencies

- Add `pep517` dependency ({pr}`1353`)
  -- by {user}`atugushev`.

## v6.0.0

*12 Mar 2021*

### Backwards Incompatible Changes

- Remove support for EOL Python 3.5 and 2.7 ({pr}`1243`)
  -- by {user}`jdufresne`.
- Remove deprecated `--index/--no-index` option from `pip-compile` ({pr}`1234`)
  -- by {user}`jdufresne`.

### Features

- Use `pep517` to parse dependencies metadata from `setup.py` ({pr}`1311`)
  -- by {user}`astrojuanlu`.

### Bug Fixes

- Fix a bug where `pip-compile` with `setup.py` would not include dependencies with
  environment markers ({pr}`1311`)
  -- by {user}`astrojuanlu`.
- Prefer `===` over `==` when generating `requirements.txt` if a dependency was pinned
  with `===` ({pr}`1323`)
  -- by {user}`IceTDrinker`.
- Fix a bug where `pip-compile` with `setup.py` in nested folder would generate
  `setup.txt` output file ({pr}`1324`)
  -- by {user}`peymanslh`.
- Write out default index when it is provided as `--extra-index-url` ({pr}`1325`)
  -- by {user}`fahrradflucht`.

### Dependencies

- Bump `pip` minimum version to `>= 20.3` ({pr}`1340`)
  -- by {user}`atugushev`.

## v5.5.0

*31 Dec 2020*

### Features

- Add Python 3.9 support ({pr}`1222`)
  -- by {user}`jdufresne`.
- Improve formatting of long "via" annotations ({pr}`1237`)
  -- by {user}`jdufresne`.
- Add `--verbose` and `--quiet` options to `pip-sync` ({pr}`1241`)
  -- by {user}`jdufresne`.
- Add `--no-allow-unsafe` option to `pip-compile` ({pr}`1265`)
  -- by {user}`jdufresne`.

### Bug Fixes

- Restore `PIP_EXISTS_ACTION` environment variable to its previous state when resolve
  dependencies in `pip-compile` ({pr}`1255`)
  -- by {user}`jdufresne`.

### Dependencies

- Remove `six` dependency in favor `pip`'s vendored `six` ({pr}`1240`)
  -- by {user}`jdufresne`.

### Improved Documentation

- Add `pip-requirements.el` (for Emacs) to useful tools to `README` ({pr}`1244`)
  -- by {user}`jdufresne`.
- Add supported Python versions to `README` ({pr}`1246`)
  -- by {user}`jdufresne`.

## v5.4.0

*21 Nov 2020*

### Features

- Add `pip>=20.3` support ({pr}`1216`)
  -- by {user}`atugushev` and {user}`AndydeCleyre`.
- Exclude `--no-reuse-hashes` option from «command to run» header ({pr}`1197`)
  -- by {user}`graingert`.

### Dependencies

- Bump `pip` minimum version to `>= 20.1` ({pr}`1191`)
  -- by {user}`atugushev` and {user}`AndydeCleyre`.

## v5.3.1

*31 Jul 2020*

### Bug Fixes

- Fix `pip-20.2` compatibility issue that caused `pip-tools` to sometime fail to
  stabilize in a constant number of rounds ({pr}`1194`)
  -- by {user}`vphilippon`.

## v5.3.0

*26 Jul 2020*

### Features

- Add `-h` alias for `--help` option to `pip-sync` and `pip-compile` ({pr}`1163`)
  -- by {user}`jan25`.
- Add `pip>=20.2` support ({pr}`1168`)
  -- by {user}`atugushev`.
- `pip-sync` now exists with code `1` on `--dry-run` ({pr}`1172`)
  -- by {user}`francisbrito`.
- `pip-compile` now doesn't resolve constraints from `-c constraints.txt`that are not
  (yet) requirements ({pr}`1175`)
  -- by {user}`clslgrnc`.
- Add `--reuse-hashes/--no-reuse-hashes` options to `pip-compile` ({pr}`1177`)
  -- by {user}`graingert`.

## v5.2.1

*09 Jun 2020*

### Bug Fixes

- Fix a bug where `pip-compile` would lose some dependencies on update a
  `requirements.txt` ({pr}`1159`)
  -- by {user}`richafrank`.

## v5.2.0

*27 May 2020*

### Features

- Show basename of URLs when `pip-compile` generates hashes in a verbose mode ({pr}`1113`)
  -- by {user}`atugushev`.
- Add `--emit-index-url/--no-emit-index-url` options to `pip-compile` ({pr}`1130`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix a bug where `pip-compile` would ignore some of package versions when
  `PIP_PREFER_BINARY` is set on ({pr}`1119`)
  -- by {user}`atugushev`.
- Fix leaked URLs with credentials in the debug output of `pip-compile` ({pr}`1146`)
  -- by {user}`atugushev`.
- Fix a bug where URL requirements would have name collisions ({pr}`1149`)
  -- by {user}`geokala`.

### Deprecations

- Deprecate `--index/--no-index` in favor of `--emit-index-url/--no-emit-index-url`
  options in `pip-compile` ({pr}`1130`)
  -- by {user}`atugushev`.

### Other Changes

- Switch to `setuptools` declarative syntax through `setup.cfg` ({pr}`1141`)
  -- by {user}`jdufresne`.

## v5.1.2

*05 May 2020*

### Bug Fixes

- Fix grouping of editables and non-editables requirements ({pr}`1132`)
  -- by {user}`richafrank`.

## v5.1.1

*01 May 2020*

### Bug Fixes

- Fix a bug where `pip-compile` would generate hashes for `*.egg` files ({pr}`1122`)
  -- by {user}`atugushev`.

## v5.1.0

*27 Apr 2020*

### Features

- Show progress bar when downloading packages in `pip-compile` verbose mode ({pr}`949`)
  -- by {user}`atugushev`.
- `pip-compile` now gets hashes from `PyPI` JSON API (if available) which significantly
  increases the speed of hashes generation ({pr}`1109`)
  -- by {user}`atugushev`.

## v5.0.0

*16 Apr 2020*

### Backwards Incompatible Changes

- `pip-tools` now requires `pip>=20.0` (previously `8.1.x` - `20.0.x`). Windows users,
  make sure to use `python -m pip install pip-tools` to avoid issues with `pip`
  self-update from now on ({pr}`1055`)
  -- by {user}`atugushev`.
- `--build-isolation` option now set on by default for `pip-compile` ({pr}`1060`)
  -- by {user}`hramezani`.

### Features

- Exclude requirements with non-matching markers from `pip-sync` ({pr}`927`)
  -- by {user}`AndydeCleyre`.
- Add `pre-commit` hook for `pip-compile` ({pr}`976`)
  -- by {user}`atugushev`.
- `pip-compile` and `pip-sync` now pass anything provided to the new `--pip-args` option
  on to `pip` ({pr}`1080`)
  -- by {user}`AndydeCleyre`.
- `pip-compile` output headers are now more accurate when `--` is used to escape
  filenames ({pr}`1080`)
  -- by {user}`AndydeCleyre`.
- Add `pip>=20.1` support ({pr}`1088`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix a bug where editables that are both direct requirements and constraints wouldn't
  appear in `pip-compile` output ({pr}`1093`)
  -- by {user}`richafrank`.
- `pip-compile` now sorts format controls (`--no-binary/--only-binary`) to ensure
  consistent results ({pr}`1098`)
  -- by {user}`richafrank`.

### Improved Documentation

- Add cross-environment usage documentation to `README` ({pr}`651`)
  -- by {user}`vphilippon`.
- Add versions compatibility table to `README` ({pr}`1106`)
  -- by {user}`atugushev`.

## v4.5.1

*26 Feb 2020*

### Bug Fixes

- Strip line number annotations such as "(line XX)" from file requirements, to prevent
  diff noise when modifying input requirement files ({pr}`1075`)
  -- by {user}`adamchainz`.

### Improved Documentation

- Updated `README` example outputs for primary requirement annotations ({pr}`1072`)
  -- by {user}`richafrank`.

## v4.5.0

*20 Feb 2020*

### Features

- Primary requirements and VCS dependencies are now get annotated with any source `.in`
  files and reverse dependencies ({pr}`1058`)
  -- by {user}`AndydeCleyre`.

### Bug Fixes

- Always use normalized path for cache directory as it is required in newer versions of
  `pip` ({pr}`1062`)
  -- by {user}`kammala`.

### Improved Documentation

- Replace outdated link in the `README` with rationale for pinning ({pr}`1053`)
  -- by {user}`m-aciek`.

## v4.4.1

*31 Jan 2020*

### Bug Fixes

- Fix a bug where `pip-compile` would keep outdated options from `requirements.txt` ({pr}`1029`)
  -- by {user}`atugushev`.
- Fix the `No handlers could be found for logger "pip.*"` error by configuring the
  builtin logging module ({pr}`1035`)
  -- by {user}`vphilippon`.
- Fix a bug where dependencies of relevant constraints may be missing from output file ({pr}`1037`)
  -- by {user}`jeevb`.
- Upgrade the minimal version of `click` from `6.0` to `7.0` version in `setup.py` ({pr}`1039`)
  -- by {user}`hramezani`.
- Ensure that depcache considers the python implementation such that (for example)
  `cpython3.6` does not poison the results of `pypy3.6` ({pr}`1050`)
  -- by {user}`asottile`.

### Improved Documentation

- Make the `README` more imperative about installing into a project's virtual
  environment to avoid confusion ({pr}`1023`)
  -- by {user}`tekumara`.
- Add a note to the `README` about how to install requirements on different stages to
  [Workflow for layered requirements](https://pip-tools.rtfd.io/en/latest/#workflow-for-layered-requirements)
  section ({pr}`1044`)
  -- by {user}`hramezani`.

## v4.4.0

*21 Jan 2020*

### Features

- Add `--cache-dir` option to `pip-compile` ({pr}`1022`)
  -- by {user}`richafrank`.
- Add `pip>=20.0` support ({pr}`1024`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix a bug where `pip-compile --upgrade-package` would upgrade those passed packages
  not already required according to the `*.in` and `*.txt` files ({pr}`1031`)
  -- by {user}`AndydeCleyre`.

## v4.3.0

*25 Nov 2019*

### Features

- Add Python 3.8 support ({pr}`956`)
  -- by {user}`hramezani`.
- Unpin commented out unsafe packages in `requirements.txt` ({pr}`975`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix `pip-compile` doesn't copy `--trusted-host` from `requirements.in` to
  `requirements.txt` ({pr}`964`)
  -- by {user}`atugushev`.
- Add compatibility with `pip>=20.0`
  ({pr}`953` and
  {pr}`978`)
  -- by {user}`atugushev`.
- Fix a bug where the resolver wouldn't clean up the ephemeral wheel cache ({pr}`968`)
  -- by {user}`atugushev`.

### Improved Documentation

- Add a note to `README` about `requirements.txt` file, which would possibly interfere
  if you're compiling from scratch ({pr}`959`)
  -- by {user}`hramezani`.

## v4.2.0

*12 Oct 2019*

### Features

- Add `--ask` option to `pip-sync` ({pr}`913`)
  -- by {user}`georgek`.

### Bug Fixes

- Add compatibility with `pip>=19.3`
  ({pr}`864`,
  {pr}`904`,
  {pr}`910`,
  {pr}`912` and
  {pr}`915`)
  -- by {user}`atugushev`.
- Ensure `pip-compile --no-header <blank requirements.in>` creates/overwrites
  `requirements.txt` ({pr}`909`)
  -- by {user}`AndydeCleyre`.
- Fix `pip-compile --upgrade-package` removes «via» annotation ({pr}`931`)
  -- by {user}`hramezani`.

### Improved Documentation

- Add info to `README` about layered requirements files and `-c` flag ({pr}`905`)
  -- by {user}`jamescooke`.

## v4.1.0

*26 Aug 2019*

### Features

- Add `--no-emit-find-links` option to `pip-compile` ({pr}`873`)
  -- by {user}`jacobtolar`.

### Bug Fixes

- Prevent `--dry-run` log message from being printed with `--quiet` option in
  `pip-compile` ({pr}`861`)
  -- by {user}`ddormer`.
- Fix resolution of requirements from Git URLs without `-e` ({pr}`879`)
  -- by {user}`andersk`.

## v4.0.0

*25 Jul 2019*

### Backwards Incompatible Changes

- Drop support for EOL Python 3.4 ({pr}`803`)
  -- by {user}`auvipy`.

### Bug Fixes

- Fix `pip>=19.2` compatibility ({pr}`857`)
  -- by {user}`atugushev`.

## v3.9.0

*17 Jul 2019*

### Features

- Print provenance information when `pip-compile` fails ({pr}`837`)
  -- by {user}`jakevdp`.

### Bug Fixes

- Output all logging to stderr instead of stdout ({pr}`834`)
  -- by {user}`georgek`.
- Fix output file update with `--dry-run` option in `pip-compile` ({pr}`842`)
  -- by {user}`shipmints` and.
  {user}`atugushev`

## v3.8.0

*06 Jun 2019*

### Features

- Options `--upgrade` and `--upgrade-package` are no longer mutually exclusive ({pr}`831`)
  -- by {user}`adamchainz`.

### Bug Fixes

- Fix `--generate-hashes` with bare VCS URLs ({pr}`812`)
  -- by {user}`jcushman`.
- Fix issues with `UnicodeError` when installing `pip-tools` from source in some systems ({pr}`816`)
  -- by {user}`AbdealiJK`.
- Respect `--pre` option in the input file ({pr}`822`)
  -- by {user}`atugushev`.
- Option `--upgrade-package` now works even if the output file does not exist ({pr}`831`)
  -- by {user}`adamchainz`.

## v3.7.0

*09 May 2019*

### Features

- Show progressbar on generation hashes in `pip-compile` verbose mode ({pr}`743`)
  -- by {user}`atugushev`.
- Add options `--cert` and `--client-cert` to `pip-sync` ({pr}`798`)
  -- by {user}`atugushev`.
- Add support for `--find-links` in `pip-compile` output ({pr}`793`)
  -- by {user}`estan` and {user}`atugushev`.
- Normalize «command to run» in `pip-compile` headers ({pr}`800`)
  -- by {user}`atugushev`.
- Support URLs as packages ({pr}`807`)
  -- by {user}`jcushman`, {user}`nim65s` and {user}`toejough`.

### Bug Fixes

- Fix replacing password to asterisks in `pip-compile` ({pr}`808`)
  -- by {user}`atugushev`.

## v3.6.1

*24 Apr 2019*

### Bug Fixes

- Fix `pip>=19.1` compatibility ({pr}`795`)
  -- by {user}`atugushev`.

## v3.6.0

*03 Apr 2019*

### Features

- Show less output on `pip-sync` with `--quiet` option ({pr}`765`)
  -- by {user}`atugushev`.
- Support the flag `--trusted-host` in `pip-sync` ({pr}`777`)
  -- by {user}`firebirdberlin`.

## v3.5.0

*13 Mar 2019*

### Features

- Show default index url provided by `pip` ({pr}`735`)
  -- by {user}`atugushev`.
- Add an option to allow enabling/disabling build isolation ({pr}`758`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix the output file for `pip-compile` with an explicit `setup.py` as source file ({pr}`731`)
  -- by {user}`atugushev`.
- Fix order issue with generated lock file when `hashes` and `markers` are used together ({pr}`763`)
  -- by {user}`milind-shakya-sp`.

## v3.4.0

*19 Feb 2019*

### Features

- Add option `--quiet` to `pip-compile` ({pr}`720`)
  -- by {user}`bendikro`.
- Emit the original command to the `pip-compile`'s header ({pr}`733`)
  -- by {user}`atugushev`.

### Bug Fixes

- Fix `pip-sync` to use pip script depending on a python version ({pr}`737`)
  -- by {user}`atugushev`.

## v3.3.2

*26 Jan 2019*

### Bug Fixes

- Fix `pip-sync` with a temporary requirement file on Windows ({pr}`723`)
  -- by {user}`atugushev`.
- Fix `pip-sync` to prevent uninstall of stdlib and dev packages ({pr}`718`)
  -- by {user}`atugushev`.

## v3.3.1

*24 Jan 2019*

- Re-release of 3.3.0 after fixing the deployment pipeline ({issue}`716`)
  -- by {user}`atugushev`.

## v3.3.0

*23 Jan 2019*

(Unreleased - Deployment pipeline issue, see 3.3.1)

### Features

- Added support of `pip` 19.0 ({pr}`715`)
  -- by {user}`atugushev`.
- Add `--allow-unsafe` to update instructions in the generated `requirements.txt` ({pr}`708`)
  -- by {user}`richafrank`.

### Bug Fixes

- Fix `pip-sync` to check hashes ({pr}`706`)
  -- by {user}`atugushev`.

## v3.2.0

*18 Dec 2018*

### Features

- Apply version constraints specified with package upgrade option
  (`-P, --upgrade-package`) ({pr}`694`)
  -- by {user}`richafrank`.

## v3.1.0

*05 Oct 2018*

### Features

- Added support of `pip` 18.1 ({pr}`689`)
  -- by {user}`vphilippon`.

## v3.0.0

*24 Sep 2018*

### Major Changes

- Update `pip-tools` for native `pip` 8, 9, 10 and 18 compatibility, un-vendoring `pip`
  to use the user-installed `pip` ({pr}`657` and {pr}`672`)
  -- by {user}`techalchemy`, {user}`suutari`, {user}`tysonclugg` and.
  {user}`vphilippon`

### Features

- Removed the dependency on the external library `first` ({pr}`676`)
  -- by {user}`jdufresne`.

## v2.0.2

*28 Apr 2018*

### Bug Fixes

- Added clearer error reporting when skipping pre-releases ({pr}`655`)
  -- by {user}`WoLpH`.

## v2.0.1

*15 Apr 2018*

### Bug Fixes

- Added missing package data from vendored pip, such as missing cacert.pem file
  -- by {user}`vphilippon`.

## v2.0.0

*15 Apr 2018*

### Major Changes

- Vendored `pip` 9.0.3 to keep compatibility for users with `pip` 10.0.0 ({pr}`644`)
  -- by {user}`vphilippon`.

### Features

- Improved the speed of `pip-compile --generate-hashes` by caching the hashes from an
  existing output file ({pr}`641`)
  -- by {user}`justicz`.
- Added a `pip-sync --user` option to restrict attention to user-local directory ({pr}`642`)
  -- by {user}`jbergknoff-10e`.
- Removed the hard dependency on setuptools ({pr}`645`)
  -- by {user}`vphilippon`.

### Bug Fixes

- The pip environment markers on top-level requirements in the source file
  (requirements.in) are now properly handled and will only be processed in the right
  environment ({pr}`647`)
  -- by {user}`JoergRittinger`.

## v1.11.0

*30 Nov 2017*

### Features

- Allow editable packages in requirements.in with `pip-compile --generate-hashes` ({pr}`524`)
  -- by {user}`jdufresne`.
- Allow for CA bundles with `pip-compile --cert` ({pr}`612`)
  -- by {user}`khwilson`.
- Improved `pip-compile` duration with large locally available editable requirement by
  skipping a copy to the cache ({pr}`583`)
  -- by {user}`costypetrisor`.
- Slightly improved the `NoCandidateFound` error message on potential causes ({pr}`614`)
  -- by {user}`vphilippon`.

### Bug Fixes

- Add `-markerlib` to the list of `PACKAGES_TO_IGNORE` of `pip-sync` ({pr}`613`).

## v1.10.2

*22 Nov 2017*

### Bug Fixes

- Fixed bug causing dependencies from invalid wheels for the current platform to be
  included ({pr}`571`).
- `pip-sync` will respect environment markers in the `requirements.txt` ({pr}`600`)
  -- by {user}`hazmat345`.
- Converted the ReadMe to have a nice description rendering on PyPI
  -- by {user}`bittner`.

## v1.10.1

*27 Sep 2017*

### Bug Fixes

- Fixed bug breaking `pip-sync` on Python 3, raising
  `TypeError: '<' not supported between instances of 'InstallRequirement' and 'InstallRequirement'` ({pr}`570`).

## v1.10.0

*27 Sep 2017*

### Features

- `--generate-hashes` now generates hashes for all wheels, not only wheels for the
  currently running platform ({pr}`520`)
  -- by {user}`jdufresne`.
- Added a `-q`/`--quiet` argument to the `pip-sync` command to reduce log output.

### Bug Fixes

- Fixed bug where unsafe packages would get pinned in generated requirements files when
  `--allow-unsafe` was not set ({pr}`517`)
  -- by {user}`dschaller`.
- Fixed bug where editable PyPI dependencies would have a `download_dir` and be exposed
  to `git-checkout-index`, (thus losing their VCS directory) and
  `python setup.py egg_info` fails ({pr}`385`) and {pr}`538`)
  -- by {user}`blueyed` and {user}`dfee`.
- Fixed bug where some primary dependencies were annotated with "via" info comments ({pr}`542`)
  -- by {user}`quantus`.
- Fixed bug where pkg-resources would be removed by `pip-sync` in Ubuntu ({pr}`555`)
  -- by {user}`cemsbr`.
- Fixed bug where the resolver would sometime not stabilize on requirements specifying
  extras ({pr}`566`)
  -- by {user}`vphilippon`.
- Fixed an unicode encoding error when distribution package contains non-ASCII file
  names ({pr}`567`)
  -- by {user}`suutari`.
- Fixed package hashing doing unnecessary unpacking ({pr}`557`)
  -- by {user}`suutari-ai`.

## v1.9.0

*12 Apr 2017*

### Features

- Added ability to read requirements from `setup.py` instead of just `requirements.in`
  ({pr}`418`)
  -- by {user}`tysonclugg` and {user}`majuscule`.
- Added a `--max-rounds` argument to the `pip-compile` command to allow for solving large
  requirement sets ({pr}`472`)
  -- by {user}`derek-miller`.
- Exclude unsafe packages' dependencies when `--allow-unsafe` is not in use ({pr}`441`)
  -- by {user}`jdufresne`.
- Exclude irrelevant pip constraints ({pr}`471`)
  -- by {user}`derek-miller`.
- Allow control over emitting trusted-host to the compiled requirements ({pr}`448`)
  -- by {user}`tonyseek`.
- Allow running as a Python module ({pr}`461`)
  -- by {user}`AndreLouisCaron`.
- Preserve environment markers in generated `requirements.txt` ({pr}`460`)
  -- by {user}`barrywhart`.

### Bug Fixes

- Fixed the `--upgrade-package` option to respect the given package list to update ({pr}`491`).
- Fixed the default output file name when the source file has no extension ({pr}`488`)
  -- by {user}`vphilippon`.
- Fixed crash on editable requirements introduced in 1.8.2.
- Fixed duplicated `--trusted-host`, `--extra-index-url` and `--index-url` in the generated
  requirements.

## v1.8.2

*28 Mar 2017*

- Regression fix: editable reqs were losing their dependencies after first round ({pr}`476`)
  -- by {user}`mattlong`.
- Remove duplicate index urls in generated `requirements.txt` ({pr}`468`)
  -- by {user}`majuscule`.

## v1.8.1

*22 Mar 2017*

- Recalculate secondary dependencies between rounds ({pr}`378`)
- Calculated dependencies could be left with wrong candidates when toplevel requirements
  happen to be also pinned in sub-dependencies ({pr}`450`)
- Fix duplicate entries that could happen in generated `requirements.txt` ({pr}`427`)
- Gracefully report invalid pip version ({pr}`457`)
- Fix capitalization in the generated `requirements.txt`, packages will always be
  lowercased ({pr}`452`)

## v1.8.0

*17 Nov 2016*

- Adds support for upgrading individual packages with a new option `--upgrade-package`.
  To upgrade a _specific_ package to the latest or a specific version use
  `--upgrade-package <pkg>`. To upgrade all packages, you can still use
  `pip-compile --upgrade`. ({pr}`409`)
- Adds support for pinning dependencies even further by including the hashes found on
  PyPI at compilation time, which will be re-checked when dependencies are installed at
  installation time. This adds protection against packages that are tampered with. ({pr}`383`)
- Improve support for extras, like `hypothesis[django]`
- Drop support for `pip < 8`

## v1.7.1

*20 Oct 2016*

- Add `--allow-unsafe` option (#377)

## v1.7.0

*06 Jul 2016*

- Add compatibility with `pip >= 8.1.2` (#374)
  -- by {user}`jmbowman`

## v1.6.5

*11 May 2016*

- Add warning that `pip >= 8.1.2` is not supported until 1.7.x is out

## v1.6.4

*03 May 2016*

- Incorporate fix for atomic file saving behaviour on the Windows platform (see {issue}`351`)

## v1.6.3

*02 May 2016*

- PyPI won't let me upload 1.6.2

## v1.6.2

*02 May 2016*

- Respect pip configuration from `pip.{ini,conf}`
- Fixes for atomic-saving of output files on Windows (see {issue}`351`)

## v1.6.1

*06 Apr 2016*

### Minor Changes

- `pip-sync` now supports being invoked from within and outside an activated virtualenv
  (see {issue}`317`)
- `pip-compile`: support `-U` as a shorthand for `--upgrade`
- `pip-compile`: support pip's `--no-binary` and `--binary-only` flags

### Bug Fixes

- Change header format of output files to mention all input files

## v1.6

*05 Feb 2016*

### Major Changes

- `pip-compile` will by default try to fulfill package specs by looking at a previously
  compiled output file first, before checking PyPI. This means `pip-compile` will only
  update the `requirements.txt` when it absolutely has to. To get the old behaviour
  (picking the latest version of all packages from PyPI), use the new `--upgrade`
  option.

### Minor Changes

- Bugfix where `pip-compile` would lose "via" info when on pip 8 (see {issue}`313`)
- Ensure cache dir exists (see {issue}`315`)

## v1.5

*23 Jan 2016*

- Add support for `pip >= 8`
- Drop support for `pip < 7`
- Fix bug where `pip-sync` fails to uninstall packages if you're using the `--no-index`
  (or other) flags

## v1.4.5

*20 Jan 2016*

- Add `--no-index` flag to `pip-compile` to avoid emitting `--index-url` into the output
  (useful if you have configured a different index in your global `~/.pip/pip.conf`, for
  example)
- Fix: ignore stdlib backport packages, like `argparse`, when listing which packages
  will be installed/uninstalled ({issue}`286`)
- Fix `pip-sync` failed uninstalling packages when using `--find-links` ({issue}`298`)
- Explicitly error when pip-tools is used with pip 8.0+ (for now)

## v1.4.4

*11 Jan 2016*

- Fix: unintended change in behaviour where packages installed by `pip-sync` could
  accidentally get upgraded under certain conditions, even though the `requirements.txt`
  would dictate otherwise (see {issue}`290`)

## v1.4.3

*06 Jan 2016*

- Fix: add `--index-url` and `--extra-index-url` options to `pip-sync`
- Fix: always install using `--upgrade` flag when running `pip-sync`

## v1.4.2

*13 Dec 2015*

- Fix bug where umask was ignored when writing requirement files ({issue}`268`)

## v1.4.1

*13 Dec 2015*

- Fix bug where successive invocations of `pip-sync` with editables kept
  uninstalling/installing them (fixes {issue}`270`)

## v1.4.0

*13 Dec 2015*

- Add command line option `-f` / `--find-links`
- Add command line option `--no-index`
- Add command line alias `-n` (for `--dry-run`)
- Fix a unicode issue

## v1.3.0

*08 Dec 2015*

- Support multiple requirement files to `pip-compile`
- Support requirements from stdin for `pip-compile`
- Support `--output-file` option on `pip-compile`, to redirect output to a file (or stdout)

## v1.2.0

*30 Nov 2015*

- Add CHANGELOG :)
- Support pip-sync'ing editable requirements
- Support extras properly (i.e. `package[foo]` syntax)

(Anything before 1.2.0 was not recorded.)
