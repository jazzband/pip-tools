# Update dependencies

By default, `pip-compile` keeps the existing pins as long as they still satisfy your constraints. To
upgrade, you have to opt in. Three flags, in increasing order of aggression: `-P`, `-U`, `--rebuild`.

## Bump one package

`-P <name>` (`--upgrade-package`) re-resolves a single package and leaves every other pin alone:

```console
pip-compile -P django
```

Pass it multiple times for several packages:

```console
pip-compile -P django -P requests
```

Bind one package to a specific version:

```console
pip-compile -P django==4.2.10
```

The version is treated as a constraint on the upgrade, not on the source files. Your `pyproject.toml`
or `requirements.in` keeps its original specifier; the lockfile picks up the requested version.

`-P` is the surgical tool. Use it for "I want to ship this security patch", "the team agreed to bump X",
or "I'm updating one library and want the diff to show only that".

## Bump everything

`-U` (`--upgrade`) disables the local pin proxy. Every package gets re-resolved against PyPI:

```console
pip-compile --upgrade
```

The diff can be large. Read it before merging. Re-run your tests against the new lockfile.

`-U` is the regular maintenance tool. A typical cadence is monthly: run `pip-compile -U`, run the test
suite, commit if green.

## Combine `-U` and `-P`

`-U` upgrades everything but you can constrain specific packages with `-P`:

```console
pip-compile --upgrade -P 'requests<3.0'
```

Reads as: "upgrade everything, but keep `requests` below 3.0". Useful when one dependency has a known
bad version range.

## Force a re-fetch from PyPI

`--rebuild` clears the dependency JSON cache before resolving, forcing a fresh lookup:

```console
pip-compile --rebuild
```

This is rarely needed. It exists for cases where a yanked release left the cache stale; the next compile
might still consider the yanked version "available" because the cached metadata says so. `--rebuild`
clears that.

The wheel and download cache are *not* cleared by `--rebuild`. To force a clean wheel cache, delete the
cache directory or run with a fresh `--cache-dir`.

## Allow prereleases

`-pre` (`--pre`) lets the resolver consider prerelease versions:

```console
pip-compile --pre -P django
```

Prereleases match constraints like `>=4.2`. Without `--pre`, the resolver skips them and picks the latest
non-prerelease that satisfies. Use this when you want to bump to a `1.0.0rc1` or similar.

## A footgun with empty output files

```{warning}
A shell redirection (`pip-compile ... > requirements.txt`) truncates the output file before
`pip-compile` can read its existing pins. With nothing to constrain against, `-P` behaves as if `-U`
had been passed and re-resolves everything.

Use `-o requirements.txt` instead of `>`. `pip-compile` writes atomically and reads the existing file
before overwriting it.
```

`pip-compile -P django` notices this case and prints:

```text
WARNING: the output file requirements.txt exists but is empty. Pip-tools cannot
upgrade only specific packages (using -P/--upgrade-package) without an existing
pin file to provide constraints.
```

## CI bumping

A common CI pattern: a scheduled job that runs `pip-compile -U`, opens a PR with the diff, and lets a
human review before merging. Tools like `dependabot` and `renovate` do this for you, but a small shell
script does the job too:

```console
pip-compile -U
git diff --quiet || gh pr create --title "deps: weekly upgrade" --body-file=...
```

Keep the cadence weekly or monthly. Daily produces too many PRs; quarterly accumulates breaking changes.

```{seealso}
- {doc}`/explanation/stable-output` for why the default behaviour does not upgrade.
- {doc}`/explanation/caching` for what `--rebuild` actually clears.
```
