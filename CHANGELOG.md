## v7.3.0

09 Aug 2023

Features:

- Add `--no-strip-extras` and warn about strip extras by default
  ([#1954](https://github.com/jazzband/pip-tools/pull/1954)). Thanks @ryanhiebert

Bug Fixes:

- Fix revealed default config in header if requirements in subfolder
  ([#1904](https://github.com/jazzband/pip-tools/pull/1904)). Thanks @atugushev
- Direct references show extra requirements in .txt files
  ([#1582](https://github.com/jazzband/pip-tools/pull/1582)). Thanks @FlorentJeannot

Other Changes:

- Document how to run under `pipx run`
  ([#1951](https://github.com/jazzband/pip-tools/pull/1951)). Thanks @brettcannon
- Document that the backtracking resolver is the current default
  ([#1948](https://github.com/jazzband/pip-tools/pull/1948)). Thanks @jeffwidman

## v7.2.0

02 Aug 2023

Features:

- Add `-c/--constraint` option to `pip-compile`
  ([#1936](https://github.com/jazzband/pip-tools/pull/1936)). Thanks @atugushev

Bug Fixes:

- Allow options in config from both `pip-compile` and `pip-sync`
  ([#1933](https://github.com/jazzband/pip-tools/pull/1933)). Thanks @atugushev
- Fix rejection of negating CLI boolean flags in config
  ([#1913](https://github.com/jazzband/pip-tools/pull/1913)). Thanks @chrysle

Other Changes:

- Add Command Line Reference section to docs
  ([#1934](https://github.com/jazzband/pip-tools/pull/1934)). Thanks @atugushev

## v7.1.0

18 Jul 2023

Features:

- Validate parsed config against CLI options
  ([#1910](https://github.com/jazzband/pip-tools/pull/1910)). Thanks @atugushev

Bug Fixes:

- Fix a bug where pip-sync would unexpectedly uninstall some packages
  ([#1919](https://github.com/jazzband/pip-tools/pull/1919)). Thanks @atugushev

## v7.0.0

14 Jul 2023

Backwards Incompatible Changes:

- Default to `--resolver=backtracking`
  ([#1897](https://github.com/jazzband/pip-tools/pull/1897)). Thanks @atugushev
- Drop support for Python 3.7
  ([#1879](https://github.com/jazzband/pip-tools/pull/1879)). Thanks @chrysle

Features:

- Add support for `pip==23.2` where refactored out `DEV_PKGS`
  ([#1906](https://github.com/jazzband/pip-tools/pull/1906)). Thanks @atugushev
- Add `--no-config` option ([#1896](https://github.com/jazzband/pip-tools/pull/1896)).
  Thanks @atugushev

Bug Fixes:

- Sync direct references with hashes
  ([#1885](https://github.com/jazzband/pip-tools/pull/1885)). Thanks @siddharthab
- Fix missing `via`s when more than two input files are used
  ([#1890](https://github.com/jazzband/pip-tools/pull/1890)). Thanks @lpulley

## v6.14.0

28 Jun 2023

Features:

- Support config defaults using `.pip-tools.toml` or `pyproject.toml`
  ([#1863](https://github.com/jazzband/pip-tools/pull/1863)). Thanks @j00bar
- Log a warning if the user specifies `-P` and the output file is present but empty
  ([#1822](https://github.com/jazzband/pip-tools/pull/1822)). Thanks @davidmreed
- Improve warning for `pip-compile` if no `--allow-unsafe` was passed
  ([#1867](https://github.com/jazzband/pip-tools/pull/1867)). Thanks @chrysle

Other Changes:

- Correct in README `pre-commit` hook to run off `requirements.in`
  ([#1847](https://github.com/jazzband/pip-tools/pull/1847)). Thanks @atugushev
- Add pyprojects.toml example for using setuptools
  ([#1851](https://github.com/jazzband/pip-tools/pull/1851)). Thanks @shatakshiiii

## v6.13.0

07 Apr 2023

Features:

- Add support for self-referential extras
  ([#1791](https://github.com/jazzband/pip-tools/pull/1791)). Thanks @q0w
- Add support for `pip==23.1` where removed `FormatControl` in `WheelCache`
  ([#1834](https://github.com/jazzband/pip-tools/pull/1834)). Thanks @atugushev
- Add support for `pip==23.1` where refactored requirement options
  ([#1832](https://github.com/jazzband/pip-tools/pull/1832)). Thanks @atugushev
- Add support for `pip==23.1` where deprecated `--install-option` has been removed
  ([#1828](https://github.com/jazzband/pip-tools/pull/1828)). Thanks @atugushev

Bug Fixes:

- Pass `--cache-dir` to `--pip-args` for backtracking resolver
  ([#1827](https://github.com/jazzband/pip-tools/pull/1827)). Thanks @q0w

Other Changes:

- Update examples in README ([#1835](https://github.com/jazzband/pip-tools/pull/1835)).
  Thanks @lucaswerkmeister

## v6.12.3

01 Mar 2023

Bug Fixes:

- Remove extras from user-supplied constraints in backtracking resolver
  ([#1808](https://github.com/jazzband/pip-tools/pull/1808)). Thanks @thomdixon
- Fix for sync error when the ireqs being merged have no names
  ([#1802](https://github.com/jazzband/pip-tools/pull/1802)). Thanks @richafrank

## v6.12.2

25 Dec 2022

Bug Fixes:

- Raise error if input and output filenames are matched
  ([#1787](https://github.com/jazzband/pip-tools/pull/1787)). Thanks @atugushev
- Add `pyproject.toml` as default input file format
  ([#1780](https://github.com/jazzband/pip-tools/pull/1780)). Thanks @berislavlopac
- Fix a regression with unsafe packages for `--allow-unsafe`
  ([#1788](https://github.com/jazzband/pip-tools/pull/1788)). Thanks @q0w

## v6.12.1

16 Dec 2022

Bug Fixes:

- Set explicitly packages for setuptools
  ([#1782](https://github.com/jazzband/pip-tools/pull/1782)). Thanks @q0w

## v6.12.0

13 Dec 2022

Features:

- Add `--no-index` flag to `pip-compile`
  ([#1745](https://github.com/jazzband/pip-tools/pull/1745)). Thanks @atugushev

Bug Fixes:

- Treat `--upgrade-packages` PKGSPECs as constraints (not just minimums), consistently
  ([#1578](https://github.com/jazzband/pip-tools/pull/1578)). Thanks @AndydeCleyre
- Filter out the user provided unsafe packages
  ([#1766](https://github.com/jazzband/pip-tools/pull/1766)). Thanks @q0w
- Adopt PEP-621 for packaging
  ([#1763](https://github.com/jazzband/pip-tools/pull/1763)). Thanks @ssbarnea

## v6.11.0

30 Nov 2022

Features:

- Add `pyproject.toml` file ([#1643](https://github.com/jazzband/pip-tools/pull/1643)).
  Thanks @otherJL0
- Support build isolation using `setuptools/pyproject.toml` requirement files
  ([#1727](https://github.com/jazzband/pip-tools/pull/1727)). Thanks @atugushev

Bug Fixes:

- Improve punctuation/grammar with `pip-compile` header
  ([#1547](https://github.com/jazzband/pip-tools/pull/1547)). Thanks @blueyed
- Generate hashes for all available candidates
  ([#1723](https://github.com/jazzband/pip-tools/pull/1723)). Thanks @neykov

Other Changes:

- Bump click minimum version to `>= 8`
  ([#1733](https://github.com/jazzband/pip-tools/pull/1733)). Thanks @atugushev
- Bump pip minimum version to `>= 22.2`
  ([#1729](https://github.com/jazzband/pip-tools/pull/1729)). Thanks @atugushev

## v6.10.0

13 Nov 2022

Features:

- Deprecate `pip-compile --resolver=legacy`
  ([#1724](https://github.com/jazzband/pip-tools/pull/1724)). Thanks @atugushev
- Prompt user to use the backtracking resolver on errors
  ([#1719](https://github.com/jazzband/pip-tools/pull/1719)). Thanks @maxfenv
- Add support for Python 3.11 final
  ([#1708](https://github.com/jazzband/pip-tools/pull/1708)). Thanks @hugovk
- Add `--newline=[LF|CRLF|native|preserve]` option to `pip-compile`
  ([#1652](https://github.com/jazzband/pip-tools/pull/1652)). Thanks @AndydeCleyre

Bug Fixes:

- Fix inconsistent handling of constraints comments with backtracking resolver
  ([#1713](https://github.com/jazzband/pip-tools/pull/1713)). Thanks @mkniewallner
- Fix some encoding warnings in Python 3.10 (PEP 597)
  ([#1614](https://github.com/jazzband/pip-tools/pull/1614)). Thanks @GalaxySnail

Other Changes:

- Update pip-tools version in the README's pre-commit examples
  ([#1701](https://github.com/jazzband/pip-tools/pull/1701)). Thanks @Kludex
- Document use of the backtracking resolver
  ([#1718](https://github.com/jazzband/pip-tools/pull/1718)). Thanks @maxfenv
- Use HTTPS in a readme link ([#1716](https://github.com/jazzband/pip-tools/pull/1716)).
  Thanks @Arhell

## v6.9.0

05 Oct 2022

Features:

- Add `--all-extras` flag to `pip-compile`
  ([#1630](https://github.com/jazzband/pip-tools/pull/1630)). Thanks @apljungquist
- Support Exclude Package with custom unsafe packages
  ([#1509](https://github.com/jazzband/pip-tools/pull/1509)). Thanks @hmc-cs-mdrissi

Bug Fixes:

- Fix compile cached vcs packages
  ([#1649](https://github.com/jazzband/pip-tools/pull/1649)). Thanks @atugushev
- Include `py.typed` in wheel file
  ([#1648](https://github.com/jazzband/pip-tools/pull/1648)). Thanks @FlorentJeannot

Other Changes:

- Add pyproject.toml & modern packaging to introduction.
  ([#1668](https://github.com/jazzband/pip-tools/pull/1668)). Thanks @hynek

## v6.8.0

30 Jun 2022

Features:

- Add support for pip's 2020 dependency resolver. Use
  `pip-compile --resolver backtracking` to enable new resolver
  ([#1539](https://github.com/jazzband/pip-tools/pull/1539)). Thanks @atugushev

## v6.7.0

27 Jun 2022

Features:

- Support for the `importlib.metadata` metadata implementation
  ([#1632](https://github.com/jazzband/pip-tools/pull/1632)). Thanks @richafrank

Bug Fixes:

- Instantiate a new accumulator `InstallRequirement` for `combine_install_requirements`
  output ([#1519](https://github.com/jazzband/pip-tools/pull/1519)). Thanks @richafrank

Other Changes:

- Replace direct usage of the `pep517` module with the `build` module, for loading
  project metadata ([#1629](https://github.com/jazzband/pip-tools/pull/1629)). Thanks
  @AndydeCleyre

## v6.6.2

23 May 2022

Bug Fixes:

- Update `PyPIRepository::resolve_reqs()` for pip>=22.1.1
  ([#1624](https://github.com/jazzband/pip-tools/pull/1624)). Thanks @m000

## v6.6.1

13 May 2022

Bug Fixes:

- Fix support for pip>=22.1 ([#1618](https://github.com/jazzband/pip-tools/pull/1618)).
  Thanks @wizpig64

## v6.6.0

06 Apr 2022

Features:

- Add support for pip>=22.1 ([#1607](https://github.com/jazzband/pip-tools/pull/1607)).
  Thanks @atugushev

Bug Fixes:

- Ensure `pip-compile --dry-run --quiet` still shows what would be done, while omitting
  the dry run message ([#1592](https://github.com/jazzband/pip-tools/pull/1592)). Thanks
  @AndydeCleyre
- Fix `--generate-hashes` when hashes are computed from files
  ([#1540](https://github.com/jazzband/pip-tools/pull/1540)). Thanks @RazerM

## v6.5.1

08 Feb 2022

Bug Fixes:

- Ensure canonicalized requirement names are used as keys, to prevent unnecessary
  reinstallations during sync
  ([#1572](https://github.com/jazzband/pip-tools/pull/1572)). Thanks @AndydeCleyre

## v6.5.0

04 Feb 2022

Features:

- Add support for pip>=22.0, drop support for Python 3.6
  ([#1567](https://github.com/jazzband/pip-tools/pull/1567)). Thanks @di
- Test on Python 3.11 ([#1527](https://github.com/jazzband/pip-tools/pull/1527)). Thanks
  @hugovk

Other Changes:

- Minor doc edits ([#1445](https://github.com/jazzband/pip-tools/pull/1445)). Thanks
  @ssiano

## v6.4.0

12 Oct 2021

Features:

- Add support for `pip>=21.3`
  ([#1501](https://github.com/jazzband/pip-tools/pull/1501)). Thanks @atugushev
- Add support for Python 3.10
  ([#1497](https://github.com/jazzband/pip-tools/pull/1497)). Thanks @joshuadavidthomas

Other Changes:

- Bump pip minimum version to `>= 21.2`
  ([#1500](https://github.com/jazzband/pip-tools/pull/1500)). Thanks @atugushev

## v6.3.1

08 Oct 2021

Bug Fixes:

- Ensure `pip-tools` unions dependencies of multiple declarations of a package with
  different extras ([#1486](https://github.com/jazzband/pip-tools/pull/1486)). Thanks
  @richafrank
- Allow comma-separated arguments for `--extra`
  ([#1493](https://github.com/jazzband/pip-tools/pull/1493)). Thanks @AndydeCleyre
- Improve clarity of help text for options supporting multiple
  ([#1492](https://github.com/jazzband/pip-tools/pull/1492)). Thanks @AndydeCleyre

## v6.3.0

21 Sep 2021

Features:

- Enable single-line annotations with `pip-compile --annotation-style=line`
  ([#1477](https://github.com/jazzband/pip-tools/pull/1477)). Thanks @AndydeCleyre
- Generate PEP 440 direct reference whenever possible
  ([#1455](https://github.com/jazzband/pip-tools/pull/1455)). Thanks @FlorentJeannot
- PEP 440 Direct Reference support
  ([#1392](https://github.com/jazzband/pip-tools/pull/1392)). Thanks @FlorentJeannot

Bug Fixes:

- Change log level of hash message
  ([#1460](https://github.com/jazzband/pip-tools/pull/1460)). Thanks @plannigan
- Allow passing `--no-upgrade` option
  ([#1438](https://github.com/jazzband/pip-tools/pull/1438)). Thanks @ssbarnea

## v6.2.0

22 Jun 2021

Features:

- Add `--emit-options/--no-emit-options` flags to `pip-compile`
  ([#1123](https://github.com/jazzband/pip-tools/pull/1123)). Thanks @atugushev
- Add `--python-executable` option for `pip-sync`
  ([#1333](https://github.com/jazzband/pip-tools/pull/1333)). Thanks @MaratFM
- Log which python version was used during compile
  ([#828](https://github.com/jazzband/pip-tools/pull/828)). Thanks @graingert

Bug Fixes:

- Fix `pip-compile` package ordering
  ([#1419](https://github.com/jazzband/pip-tools/pull/1419)). Thanks @adamsol
- Add `--strip-extras` option to `pip-compile` for producing constraint compatible
  output ([#1404](https://github.com/jazzband/pip-tools/pull/1404)). Thanks @ssbarnea
- Fix `click` v7 `version_option` compatibility
  ([#1410](https://github.com/jazzband/pip-tools/pull/1410)). Thanks @FuegoFro
- Pass `package_name` explicitly in `click.version_option` decorators for compatibility
  with `click>=8.0` ([#1400](https://github.com/jazzband/pip-tools/pull/1400)). Thanks
  @nicoa

Other Changes:

- Document updating requirements with `pre-commit` hooks
  ([#1387](https://github.com/jazzband/pip-tools/pull/1387)). Thanks @microcat49
- Add `setuptools` and `wheel` dependencies to the `setup.cfg`
  ([#889](https://github.com/jazzband/pip-tools/pull/889)). Thanks @jayvdb
- Improve instructions for new contributors
  ([#1394](https://github.com/jazzband/pip-tools/pull/1394)). Thanks @FlorentJeannot
- Better explain role of existing `requirements.txt`
  ([#1369](https://github.com/jazzband/pip-tools/pull/1369)). Thanks @mikepqr

## v6.1.0

14 Apr 2021

Features:

- Add support for `pyproject.toml` or `setup.cfg` as input dependency file (PEP-517) for
  `pip-compile` ([#1356](https://github.com/jazzband/pip-tools/pull/1356)). Thanks
  @orsinium
- Add `pip-compile --extra` option to specify `extras_require` dependencies
  ([#1363](https://github.com/jazzband/pip-tools/pull/1363)). Thanks @orsinium

Bug Fixes:

- Restore ability to set compile cache with env var `PIP_TOOLS_CACHE_DIR`
  ([#1368](https://github.com/jazzband/pip-tools/pull/1368)). Thanks @AndydeCleyre

## v6.0.1

15 Mar 2021

Bug Fixes:

- Fixed a bug with undeclared dependency on `importlib-metadata` at Python 3.6
  ([#1353](https://github.com/jazzband/pip-tools/pull/1353)). Thanks @atugushev

Dependencies:

- Add `pep517` dependency ([#1353](https://github.com/jazzband/pip-tools/pull/1353)).
  Thanks @atugushev

## v6.0.0

12 Mar 2021

Backwards Incompatible Changes:

- Remove support for EOL Python 3.5 and 2.7
  ([#1243](https://github.com/jazzband/pip-tools/pull/1243)). Thanks @jdufresne
- Remove deprecated `--index/--no-index` option from `pip-compile`
  ([#1234](https://github.com/jazzband/pip-tools/pull/1234)). Thanks @jdufresne

Features:

- Use `pep517` to parse dependencies metadata from `setup.py`
  ([#1311](https://github.com/jazzband/pip-tools/pull/1311)). Thanks @astrojuanlu

Bug Fixes:

- Fix a bug where `pip-compile` with `setup.py` would not include dependencies with
  environment markers ([#1311](https://github.com/jazzband/pip-tools/pull/1311)). Thanks
  @astrojuanlu
- Prefer `===` over `==` when generating `requirements.txt` if a dependency was pinned
  with `===` ([#1323](https://github.com/jazzband/pip-tools/pull/1323)). Thanks
  @IceTDrinker
- Fix a bug where `pip-compile` with `setup.py` in nested folder would generate
  `setup.txt` output file ([#1324](https://github.com/jazzband/pip-tools/pull/1324)).
  Thanks @peymanslh
- Write out default index when it is provided as `--extra-index-url`
  ([#1325](https://github.com/jazzband/pip-tools/pull/1325)). Thanks @fahrradflucht

Dependencies:

- Bump `pip` minimum version to `>= 20.3`
  ([#1340](https://github.com/jazzband/pip-tools/pull/1340)). Thanks @atugushev

## v5.5.0

31 Dec 2020

Features:

- Add Python 3.9 support ([1222](https://github.com/jazzband/pip-tools/pull/1222)).
  Thanks @jdufresne
- Improve formatting of long "via" annotations
  ([1237](https://github.com/jazzband/pip-tools/pull/1237)). Thanks @jdufresne
- Add `--verbose` and `--quiet` options to `pip-sync`
  ([1241](https://github.com/jazzband/pip-tools/pull/1241)). Thanks @jdufresne
- Add `--no-allow-unsafe` option to `pip-compile`
  ([1265](https://github.com/jazzband/pip-tools/pull/1265)). Thanks @jdufresne

Bug Fixes:

- Restore `PIP_EXISTS_ACTION` environment variable to its previous state when resolve
  dependencies in `pip-compile`
  ([1255](https://github.com/jazzband/pip-tools/pull/1255)). Thanks @jdufresne

Dependencies:

- Remove `six` dependency in favor `pip`'s vendored `six`
  ([1240](https://github.com/jazzband/pip-tools/pull/1240)). Thanks @jdufresne

Improved Documentation:

- Add `pip-requirements.el` (for Emacs) to useful tools to `README`
  ([#1244](https://github.com/jazzband/pip-tools/pull/1244)). Thanks @jdufresne
- Add supported Python versions to `README`
  ([#1246](https://github.com/jazzband/pip-tools/pull/1246)). Thanks @jdufresne

## v5.4.0

21 Nov 2020

Features:

- Add `pip>=20.3` support ([1216](https://github.com/jazzband/pip-tools/pull/1216)).
  Thanks @atugushev and @AndydeCleyre
- Exclude `--no-reuse-hashes` option from «command to run» header
  ([1197](https://github.com/jazzband/pip-tools/pull/1197)). Thanks @graingert

Dependencies:

- Bump `pip` minimum version to `>= 20.1`
  ([1191](https://github.com/jazzband/pip-tools/pull/1191)). Thanks @atugushev and
  @AndydeCleyre

## v5.3.1

31 Jul 2020

Bug Fixes:

- Fix `pip-20.2` compatibility issue that caused `pip-tools` to sometime fail to
  stabilize in a constant number of rounds
  ([1194](https://github.com/jazzband/pip-tools/pull/1194)). Thanks @vphilippon

## v5.3.0

26 Jul 2020

Features:

- Add `-h` alias for `--help` option to `pip-sync` and `pip-compile`
  ([1163](https://github.com/jazzband/pip-tools/pull/1163)). Thanks @jan25
- Add `pip>=20.2` support ([1168](https://github.com/jazzband/pip-tools/pull/1168)).
  Thanks @atugushev
- `pip-sync` now exists with code `1` on `--dry-run`
  ([1172](https://github.com/jazzband/pip-tools/pull/1172)). Thanks @francisbrito
- `pip-compile` now doesn't resolve constraints from `-c constraints.txt`that are not
  (yet) requirements ([1175](https://github.com/jazzband/pip-tools/pull/1175)). Thanks
  @clslgrnc
- Add `--reuse-hashes/--no-reuse-hashes` options to `pip-compile`
  ([1177](https://github.com/jazzband/pip-tools/pull/1177)). Thanks @graingert

## v5.2.1

09 Jun 2020

Bug Fixes:

- Fix a bug where `pip-compile` would lose some dependencies on update a
  `requirements.txt` ([1159](https://github.com/jazzband/pip-tools/pull/1159)). Thanks
  @richafrank

## v5.2.0

27 May 2020

Features:

- Show basename of URLs when `pip-compile` generates hashes in a verbose mode
  ([1113](https://github.com/jazzband/pip-tools/pull/1113)). Thanks @atugushev
- Add `--emit-index-url/--no-emit-index-url` options to `pip-compile`
  ([1130](https://github.com/jazzband/pip-tools/pull/1130)). Thanks @atugushev

Bug Fixes:

- Fix a bug where `pip-compile` would ignore some of package versions when
  `PIP_PREFER_BINARY` is set on
  ([1119](https://github.com/jazzband/pip-tools/pull/1119)). Thanks @atugushev
- Fix leaked URLs with credentials in the debug output of `pip-compile`.
  ([1146](https://github.com/jazzband/pip-tools/pull/1146)). Thanks @atugushev
- Fix a bug where URL requirements would have name collisions
  ([1149](https://github.com/jazzband/pip-tools/pull/1149)). Thanks @geokala

Deprecations:

- Deprecate `--index/--no-index` in favor of `--emit-index-url/--no-emit-index-url`
  options in `pip-compile` ([1130](https://github.com/jazzband/pip-tools/pull/1130)).
  Thanks @atugushev

Other Changes:

- Switch to `setuptools` declarative syntax through `setup.cfg`
  ([1141](https://github.com/jazzband/pip-tools/pull/1141)). Thanks @jdufresne

## v5.1.2

05 May 2020

Bug Fixes:

- Fix grouping of editables and non-editables requirements
  ([1132](https://github.com/jazzband/pip-tools/pull/1132)). Thanks @richafrank

## v5.1.1

01 May 2020

Bug Fixes:

- Fix a bug where `pip-compile` would generate hashes for `*.egg` files
  ([#1122](https://github.com/jazzband/pip-tools/pull/1122)). Thanks @atugushev

## v5.1.0

27 Apr 2020

Features:

- Show progress bar when downloading packages in `pip-compile` verbose mode
  ([#949](https://github.com/jazzband/pip-tools/pull/949)). Thanks @atugushev
- `pip-compile` now gets hashes from `PyPI` JSON API (if available) which significantly
  increases the speed of hashes generation
  ([#1109](https://github.com/jazzband/pip-tools/pull/1109)). Thanks @atugushev

## v5.0.0

16 Apr 2020

Backwards Incompatible Changes:

- `pip-tools` now requires `pip>=20.0` (previously `8.1.x` - `20.0.x`). Windows users,
  make sure to use `python -m pip install pip-tools` to avoid issues with `pip`
  self-update from now on ([#1055](https://github.com/jazzband/pip-tools/pull/1055)).
  Thanks @atugushev
- `--build-isolation` option now set on by default for `pip-compile`
  ([#1060](https://github.com/jazzband/pip-tools/pull/1060)). Thanks @hramezani

Features:

- Exclude requirements with non-matching markers from `pip-sync`
  ([#927](https://github.com/jazzband/pip-tools/pull/927)). Thanks @AndydeCleyre
- Add `pre-commit` hook for `pip-compile`
  ([#976](https://github.com/jazzband/pip-tools/pull/976)). Thanks @atugushev
- `pip-compile` and `pip-sync` now pass anything provided to the new `--pip-args` option
  on to `pip` ([#1080](https://github.com/jazzband/pip-tools/pull/1080)). Thanks
  @AndydeCleyre
- `pip-compile` output headers are now more accurate when `--` is used to escape
  filenames ([#1080](https://github.com/jazzband/pip-tools/pull/1080)). Thanks
  @AndydeCleyre
- Add `pip>=20.1` support ([#1088](https://github.com/jazzband/pip-tools/pull/1088)).
  Thanks @atugushev

Bug Fixes:

- Fix a bug where editables that are both direct requirements and constraints wouldn't
  appear in `pip-compile` output
  ([#1093](https://github.com/jazzband/pip-tools/pull/1093)). Thanks @richafrank
- `pip-compile` now sorts format controls (`--no-binary/--only-binary`) to ensure
  consistent results ([#1098](https://github.com/jazzband/pip-tools/pull/1098)). Thanks
  @richafrank

Improved Documentation:

- Add cross-environment usage documentation to `README`
  ([#651](https://github.com/jazzband/pip-tools/pull/651)). Thanks @vphilippon
- Add versions compatibility table to `README`
  ([#1106](https://github.com/jazzband/pip-tools/pull/1106)). Thanks @atugushev

## v4.5.1

26 Feb 2020

Bug Fixes:

- Strip line number annotations such as "(line XX)" from file requirements, to prevent
  diff noise when modifying input requirement files
  ([#1075](https://github.com/jazzband/pip-tools/pull/1075)). Thanks @adamchainz

Improved Documentation:

- Updated `README` example outputs for primary requirement annotations
  ([#1072](https://github.com/jazzband/pip-tools/pull/1072)). Thanks @richafrank

## v4.5.0

20 Feb 2020

Features:

- Primary requirements and VCS dependencies are now get annotated with any source `.in`
  files and reverse dependencies
  ([#1058](https://github.com/jazzband/pip-tools/pull/1058)). Thanks @AndydeCleyre

Bug Fixes:

- Always use normalized path for cache directory as it is required in newer versions of
  `pip` ([#1062](https://github.com/jazzband/pip-tools/pull/1062)). Thanks @kammala

Improved Documentation:

- Replace outdated link in the `README` with rationale for pinning
  ([#1053](https://github.com/jazzband/pip-tools/pull/1053)). Thanks @m-aciek

## v4.4.1

31 Jan 2020

Bug Fixes:

- Fix a bug where `pip-compile` would keep outdated options from `requirements.txt`
  ([#1029](https://github.com/jazzband/pip-tools/pull/1029)). Thanks @atugushev
- Fix the `No handlers could be found for logger "pip.*"` error by configuring the
  builtin logging module ([#1035](https://github.com/jazzband/pip-tools/pull/1035)).
  Thanks @vphilippon
- Fix a bug where dependencies of relevant constraints may be missing from output file
  ([#1037](https://github.com/jazzband/pip-tools/pull/1037)). Thanks @jeevb
- Upgrade the minimal version of `click` from `6.0` to `7.0` version in `setup.py`
  ([#1039](https://github.com/jazzband/pip-tools/pull/1039)). Thanks @hramezani
- Ensure that depcache considers the python implementation such that (for example)
  `cpython3.6` does not poison the results of `pypy3.6`
  ([#1050](https://github.com/jazzband/pip-tools/pull/1050)). Thanks @asottile

Improved Documentation:

- Make the `README` more imperative about installing into a project's virtual
  environment to avoid confusion
  ([#1023](https://github.com/jazzband/pip-tools/pull/1023)). Thanks @tekumara
- Add a note to the `README` about how to install requirements on different stages to
  [Workflow for layered requirements](https://pip-tools.rtfd.io/en/latest/#workflow-for-layered-requirements)
  section ([#1044](https://github.com/jazzband/pip-tools/pull/1044)). Thanks @hramezani

## v4.4.0

21 Jan 2020

Features:

- Add `--cache-dir` option to `pip-compile`
  ([#1022](https://github.com/jazzband/pip-tools/pull/1022)). Thanks @richafrank
- Add `pip>=20.0` support ([#1024](https://github.com/jazzband/pip-tools/pull/1024)).
  Thanks @atugushev

Bug Fixes:

- Fix a bug where `pip-compile --upgrade-package` would upgrade those passed packages
  not already required according to the `*.in` and `*.txt` files
  ([#1031](https://github.com/jazzband/pip-tools/pull/1031)). Thanks @AndydeCleyre

## v4.3.0

25 Nov 2019

Features:

- Add Python 3.8 support ([#956](https://github.com/jazzband/pip-tools/pull/956)).
  Thanks @hramezani
- Unpin commented out unsafe packages in `requirements.txt`
  ([#975](https://github.com/jazzband/pip-tools/pull/975)). Thanks @atugushev

Bug Fixes:

- Fix `pip-compile` doesn't copy `--trusted-host` from `requirements.in` to
  `requirements.txt` ([#964](https://github.com/jazzband/pip-tools/pull/964)). Thanks
  @atugushev
- Add compatibility with `pip>=20.0`
  ([#953](https://github.com/jazzband/pip-tools/pull/953) and
  [#978](https://github.com/jazzband/pip-tools/pull/978)). Thanks @atugushev
- Fix a bug where the resolver wouldn't clean up the ephemeral wheel cache
  ([#968](https://github.com/jazzband/pip-tools/pull/968)). Thanks @atugushev

Improved Documentation:

- Add a note to `README` about `requirements.txt` file, which would possibly interfere
  if you're compiling from scratch
  ([#959](https://github.com/jazzband/pip-tools/pull/959)). Thanks @hramezani

## v4.2.0

12 Oct 2019

Features:

- Add `--ask` option to `pip-sync`
  ([#913](https://github.com/jazzband/pip-tools/pull/913)). Thanks @georgek

Bug Fixes:

- Add compatibility with `pip>=19.3`
  ([#864](https://github.com/jazzband/pip-tools/pull/864),
  [#904](https://github.com/jazzband/pip-tools/pull/904),
  [#910](https://github.com/jazzband/pip-tools/pull/910),
  [#912](https://github.com/jazzband/pip-tools/pull/912) and
  [#915](https://github.com/jazzband/pip-tools/pull/915)). Thanks @atugushev
- Ensure `pip-compile --no-header <blank requirements.in>` creates/overwrites
  `requirements.txt` ([#909](https://github.com/jazzband/pip-tools/pull/909)). Thanks
  @AndydeCleyre
- Fix `pip-compile --upgrade-package` removes «via» annotation
  ([#931](https://github.com/jazzband/pip-tools/pull/931)). Thanks @hramezani

Improved Documentation:

- Add info to `README` about layered requirements files and `-c` flag
  ([#905](https://github.com/jazzband/pip-tools/pull/905)). Thanks @jamescooke

## v4.1.0

26 Aug 2019

Features:

- Add `--no-emit-find-links` option to `pip-compile`
  ([#873](https://github.com/jazzband/pip-tools/pull/873)). Thanks @jacobtolar

Bug Fixes:

- Prevent `--dry-run` log message from being printed with `--quiet` option in
  `pip-compile` ([#861](https://github.com/jazzband/pip-tools/pull/861)). Thanks
  @ddormer
- Fix resolution of requirements from Git URLs without `-e`
  ([#879](https://github.com/jazzband/pip-tools/pull/879)). Thanks @andersk

## v4.0.0

25 Jul 2019

Backwards Incompatible Changes:

- Drop support for EOL Python 3.4
  ([#803](https://github.com/jazzband/pip-tools/pull/803)). Thanks @auvipy

Bug Fixes:

- Fix `pip>=19.2` compatibility
  ([#857](https://github.com/jazzband/pip-tools/pull/857)). Thanks @atugushev

## v3.9.0

17 Jul 2019

Features:

- Print provenance information when `pip-compile` fails
  ([#837](https://github.com/jazzband/pip-tools/pull/837)). Thanks @jakevdp

Bug Fixes:

- Output all logging to stderr instead of stdout
  ([#834](https://github.com/jazzband/pip-tools/pull/834)). Thanks @georgek
- Fix output file update with `--dry-run` option in `pip-compile`
  ([#842](https://github.com/jazzband/pip-tools/pull/842)). Thanks @shipmints and
  @atugushev

## v3.8.0

06 Jun 2019

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

## v3.7.0

09 May 2019

Features:

- Show progressbar on generation hashes in `pip-compile` verbose mode
  ([#743](https://github.com/jazzband/pip-tools/pull/743)). Thanks @atugushev
- Add options `--cert` and `--client-cert` to `pip-sync`
  ([#798](https://github.com/jazzband/pip-tools/pull/798)). Thanks @atugushev
- Add support for `--find-links` in `pip-compile` output
  ([#793](https://github.com/jazzband/pip-tools/pull/793)). Thanks @estan and @atugushev
- Normalize «command to run» in `pip-compile` headers
  ([#800](https://github.com/jazzband/pip-tools/pull/800)). Thanks @atugushev
- Support URLs as packages ([#807](https://github.com/jazzband/pip-tools/pull/807)).
  Thanks @jcushman, @nim65s and @toejough

Bug Fixes:

- Fix replacing password to asterisks in `pip-compile`
  ([#808](https://github.com/jazzband/pip-tools/pull/808)). Thanks @atugushev

## v3.6.1

24 Apr 2019

Bug Fixes:

- Fix `pip>=19.1` compatibility
  ([#795](https://github.com/jazzband/pip-tools/pull/795)). Thanks @atugushev

## v3.6.0

03 Apr 2019

Features:

- Show less output on `pip-sync` with `--quiet` option
  ([#765](https://github.com/jazzband/pip-tools/pull/765)). Thanks @atugushev
- Support the flag `--trusted-host` in `pip-sync`
  ([#777](https://github.com/jazzband/pip-tools/pull/777)). Thanks @firebirdberlin

## v3.5.0

13 Mar 2019

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

## v3.4.0

19 Feb 2019

Features:

- Add option `--quiet` to `pip-compile`
  ([#720](https://github.com/jazzband/pip-tools/pull/720)). Thanks @bendikro
- Emit the original command to the `pip-compile`'s header
  ([#733](https://github.com/jazzband/pip-tools/pull/733)). Thanks @atugushev

Bug Fixes:

- Fix `pip-sync` to use pip script depending on a python version
  ([#737](https://github.com/jazzband/pip-tools/pull/737)). Thanks @atugushev

## v3.3.2

26 Jan 2019

Bug Fixes:

- Fix `pip-sync` with a temporary requirement file on Windows
  ([#723](https://github.com/jazzband/pip-tools/pull/723)). Thanks @atugushev
- Fix `pip-sync` to prevent uninstall of stdlib and dev packages
  ([#718](https://github.com/jazzband/pip-tools/pull/718)). Thanks @atugushev

## v3.3.1

24 Jan 2019

- Re-release of 3.3.0 after fixing the deployment pipeline
  ([#716](https://github.com/jazzband/pip-tools/issues/716)). Thanks @atugushev

## v3.3.0

23 Jan 2019

(Unreleased - Deployment pipeline issue, see 3.3.1)

Features:

- Added support of `pip` 19.0 ([#715](https://github.com/jazzband/pip-tools/pull/715)).
  Thanks @atugushev
- Add `--allow-unsafe` to update instructions in the generated `requirements.txt`
  ([#708](https://github.com/jazzband/pip-tools/pull/708)). Thanks @richafrank

Bug Fixes:

- Fix `pip-sync` to check hashes
  ([#706](https://github.com/jazzband/pip-tools/pull/706)). Thanks @atugushev

## v3.2.0

18 Dec 2018

Features:

- Apply version constraints specified with package upgrade option
  (`-P, --upgrade-package`) ([#694](https://github.com/jazzband/pip-tools/pull/694)).
  Thanks @richafrank

## v3.1.0

05 Oct 2018

Features:

- Added support of `pip` 18.1 ([#689](https://github.com/jazzband/pip-tools/pull/689)).
  Thanks @vphilippon

## v3.0.0

24 Sep 2018

Major changes:

- Update `pip-tools` for native `pip` 8, 9, 10 and 18 compatibility, un-vendoring `pip`
  to use the user-installed `pip`
  ([#657](https://github.com/jazzband/pip-tools/pull/657) and
  [#672](https://github.com/jazzband/pip-tools/pull/672)). Thanks to @techalchemy,
  @suutari, @tysonclugg and @vphilippon for contributing on this.

Features:

- Removed the dependency on the external library `first`
  ([#676](https://github.com/jazzband/pip-tools/pull/676)). Thanks @jdufresne

## v2.0.2

28 Apr 2018

Bug Fixes:

- Added clearer error reporting when skipping pre-releases
  ([#655](https://github.com/jazzband/pip-tools/pull/655)). Thanks @WoLpH

## v2.0.1

15 Apr 2018

Bug Fixes:

- Added missing package data from vendored pip, such as missing cacert.pem file. Thanks
  @vphilippon

## v2.0.0

15 Apr 2018

Major changes:

- Vendored `pip` 9.0.3 to keep compatibility for users with `pip` 10.0.0
  ([#644](https://github.com/jazzband/pip-tools/pull/644)). Thanks @vphilippon

Features:

- Improved the speed of pip-compile --generate-hashes by caching the hashes from an
  existing output file ([#641](https://github.com/jazzband/pip-tools/pull/641)). Thanks
  @justicz
- Added a `pip-sync --user` option to restrict attention to user-local directory
  ([#642](https://github.com/jazzband/pip-tools/pull/642)). Thanks @jbergknoff-10e
- Removed the hard dependency on setuptools
  ([#645](https://github.com/jazzband/pip-tools/pull/645)). Thanks @vphilippon

Bug fixes:

- The pip environment markers on top-level requirements in the source file
  (requirements.in) are now properly handled and will only be processed in the right
  environment ([#647](https://github.com/jazzband/pip-tools/pull/647)). Thanks
  @JoergRittinger

## v1.11.0

30 Nov 2017

Features:

- Allow editable packages in requirements.in with `pip-compile --generate-hashes`
  ([#524](https://github.com/jazzband/pip-tools/pull/524)). Thanks @jdufresne
- Allow for CA bundles with `pip-compile --cert`
  ([#612](https://github.com/jazzband/pip-tools/pull/612)). Thanks @khwilson
- Improved `pip-compile` duration with large locally available editable requirement by
  skipping a copy to the cache ([#583](https://github.com/jazzband/pip-tools/pull/583)).
  Thanks @costypetrisor
- Slightly improved the `NoCandidateFound` error message on potential causes
  ([#614](https://github.com/jazzband/pip-tools/pull/614)). Thanks @vphilippon

Bug Fixes:

- Add `-markerlib` to the list of `PACKAGES_TO_IGNORE` of `pip-sync`
  ([#613](https://github.com/jazzband/pip-tools/pull/613)).

## v1.10.2

22 Nov 2017

Bug Fixes:

- Fixed bug causing dependencies from invalid wheels for the current platform to be
  included ([#571](https://github.com/jazzband/pip-tools/pull/571)).
- `pip-sync` will respect environment markers in the requirements.txt
  ([600](https://github.com/jazzband/pip-tools/pull/600)). Thanks @hazmat345
- Converted the ReadMe to have a nice description rendering on PyPI. Thanks @bittner

## v1.10.1

27 Sep 2017

Bug Fixes:

- Fixed bug breaking `pip-sync` on Python 3, raising
  `TypeError: '<' not supported between instances of 'InstallRequirement' and 'InstallRequirement'`
  ([#570](https://github.com/jazzband/pip-tools/pull/570)).

## v1.10.0

27 Sep 2017

Features:

- `--generate-hashes` now generates hashes for all wheels, not only wheels for the
  currently running platform ([#520](https://github.com/jazzband/pip-tools/pull/520)).
  Thanks @jdufresne
- Added a `-q`/`--quiet` argument to the pip-sync command to reduce log output.

Bug Fixes:

- Fixed bug where unsafe packages would get pinned in generated requirements files when
  `--allow-unsafe` was not set.
  ([#517](https://github.com/jazzband/pip-tools/pull/517)). Thanks @dschaller
- Fixed bug where editable PyPI dependencies would have a `download_dir` and be exposed
  to `git-checkout-index`, (thus losing their VCS directory) and
  `python setup.py egg_info` fails.
  ([#385](https://github.com/jazzband/pip-tools/pull/385#) and
  [#538](https://github.com/jazzband/pip-tools/pull/538)). Thanks @blueyed and @dfee
- Fixed bug where some primary dependencies were annotated with "via" info comments.
  ([#542](https://github.com/jazzband/pip-tools/pull/542)). Thanks @quantus
- Fixed bug where pkg-resources would be removed by pip-sync in Ubuntu.
  ([#555](https://github.com/jazzband/pip-tools/pull/555)). Thanks @cemsbr
- Fixed bug where the resolver would sometime not stabilize on requirements specifying
  extras. ([#566](https://github.com/jazzband/pip-tools/pull/566)). Thanks @vphilippon
- Fixed an unicode encoding error when distribution package contains non-ASCII file
  names ([#567](https://github.com/jazzband/pip-tools/pull/567)). Thanks @suutari
- Fixed package hashing doing unnecessary unpacking
  ([#557](https://github.com/jazzband/pip-tools/pull/557)). Thanks @suutari-ai

## v1.9.0

12 Apr 2017

Features:

- Added ability to read requirements from `setup.py` instead of just `requirements.in`
  ([#418](https://github.com/jazzband/pip-tools/pull/418)). Thanks to @tysonclugg and
  @majuscule.
- Added a `--max-rounds` argument to the pip-compile command to allow for solving large
  requirement sets ([#472](https://github.com/jazzband/pip-tools/pull/472)). Thanks
  @derek-miller.
- Exclude unsafe packages' dependencies when `--allow-unsafe` is not in use
  ([#441](https://github.com/jazzband/pip-tools/pull/441)). Thanks @jdufresne.
- Exclude irrelevant pip constraints
  ([#471](https://github.com/jazzband/pip-tools/pull/471)). Thanks @derek-miller.
- Allow control over emitting trusted-host to the compiled requirements.
  ([#448](https://github.com/jazzband/pip-tools/pull/448)). Thanks @tonyseek.
- Allow running as a Python module
  (#[461](https://github.com/jazzband/pip-tools/pull/461)). Thanks @AndreLouisCaron.
- Preserve environment markers in generated requirements.txt.
  ([#460](https://github.com/jazzband/pip-tools/pull/460)). Thanks @barrywhart.

Bug Fixes:

- Fixed the --upgrade-package option to respect the given package list to update
  ([#491](https://github.com/jazzband/pip-tools/pull/491)).
- Fixed the default output file name when the source file has no extension
  ([#488](https://github.com/jazzband/pip-tools/pull/488)). Thanks @vphilippon
- Fixed crash on editable requirements introduced in 1.8.2.
- Fixed duplicated --trusted-host, --extra-index-url and --index-url in the generated
  requirements.

## v1.8.2

28 Mar 2017

- Regression fix: editable reqs were losing their dependencies after first round
  ([#476](https://github.com/jazzband/pip-tools/pull/476)) Thanks @mattlong
- Remove duplicate index urls in generated requirements.txt
  ([#468](https://github.com/jazzband/pip-tools/pull/468)) Thanks @majuscule

## v1.8.1

22 Mar 2017

- Recalculate secondary dependencies between rounds (#378)
- Calculated dependencies could be left with wrong candidates when toplevel requirements
  happen to be also pinned in sub-dependencies (#450)
- Fix duplicate entries that could happen in generated requirements.txt (#427)
- Gracefully report invalid pip version (#457)
- Fix capitalization in the generated requirements.txt, packages will always be
  lowercased (#452)

## v1.8.0

17 Nov 2016

- Adds support for upgrading individual packages with a new option `--upgrade-package`.
  To upgrade a _specific_ package to the latest or a specific version use
  `--upgrade-package <pkg>`. To upgrade all packages, you can still use
  `pip-compile --upgrade`. (#409)
- Adds support for pinning dependencies even further by including the hashes found on
  PyPI at compilation time, which will be re-checked when dependencies are installed at
  installation time. This adds protection against packages that are tampered with.
  (#383)
- Improve support for extras, like `hypothesis[django]`
- Drop support for pip < 8

## v1.7.1

20 Oct 2016

- Add `--allow-unsafe` option (#377)

## v1.7.0

06 Jul 2016

- Add compatibility with pip >= 8.1.2 (#374) Thanks so much, @jmbowman!

## v1.6.5

11 May 2016

- Add warning that pip >= 8.1.2 is not supported until 1.7.x is out

## v1.6.4

03 May 2016

- Incorporate fix for atomic file saving behaviour on the Windows platform (see #351)

## v1.6.3

02 May 2016

- PyPI won't let me upload 1.6.2

## v1.6.2

02 May 2016

- Respect pip configuration from pip.{ini,conf}
- Fixes for atomic-saving of output files on Windows (see #351)

## v1.6.1

06 Apr 2016

Minor changes:

- pip-sync now supports being invoked from within and outside an activated virtualenv
  (see #317)
- pip-compile: support -U as a shorthand for --upgrade
- pip-compile: support pip's --no-binary and --binary-only flags

Fixes:

- Change header format of output files to mention all input files

## v1.6

05 Feb 2016

Major change:

- pip-compile will by default try to fulfill package specs by looking at a previously
  compiled output file first, before checking PyPI. This means pip-compile will only
  update the requirements.txt when it absolutely has to. To get the old behaviour
  (picking the latest version of all packages from PyPI), use the new `--upgrade`
  option.

Minor changes:

- Bugfix where pip-compile would lose "via" info when on pip 8 (see #313)
- Ensure cache dir exists (see #315)

## v1.5

23 Jan 2016

- Add support for pip >= 8
- Drop support for pip < 7
- Fix bug where `pip-sync` fails to uninstall packages if you're using the `--no-index`
  (or other) flags

## v1.4.5

20 Jan 2016

- Add `--no-index` flag to `pip-compile` to avoid emitting `--index-url` into the output
  (useful if you have configured a different index in your global ~/.pip/pip.conf, for
  example)
- Fix: ignore stdlib backport packages, like `argparse`, when listing which packages
  will be installed/uninstalled (#286)
- Fix pip-sync failed uninstalling packages when using `--find-links` (#298)
- Explicitly error when pip-tools is used with pip 8.0+ (for now)

## v1.4.4

11 Jan 2016

- Fix: unintended change in behaviour where packages installed by `pip-sync` could
  accidentally get upgraded under certain conditions, even though the requirements.txt
  would dictate otherwise (see #290)

## v1.4.3

06 Jan 2016

- Fix: add `--index-url` and `--extra-index-url` options to `pip-sync`
- Fix: always install using `--upgrade` flag when running `pip-sync`

## v1.4.2

13 Dec 2015

- Fix bug where umask was ignored when writing requirement files (#268)

## v1.4.1

13 Dec 2015

- Fix bug where successive invocations of pip-sync with editables kept
  uninstalling/installing them (fixes #270)

## v1.4.0

13 Dec 2015

- Add command line option -f / --find-links
- Add command line option --no-index
- Add command line alias -n (for --dry-run)
- Fix a unicode issue

## v1.3.0

08 Dec 2015

- Support multiple requirement files to pip-compile
- Support requirements from stdin for pip-compile
- Support --output-file option on pip-compile, to redirect output to a file (or stdout)

## v1.2.0

30 Nov 2015

- Add CHANGELOG :)
- Support pip-sync'ing editable requirements
- Support extras properly (i.e. package[foo] syntax)

(Anything before 1.2.0 was not recorded.)
