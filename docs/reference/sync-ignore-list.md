# Packages `pip-sync` does not uninstall

`pip-sync` uninstalls every package in the environment that is not listed in the lockfile, with a
deliberate ignore list. The list exists to keep the tools you used to set up the environment from
disappearing on the first sync.

## The static list

These names are always ignored, regardless of what is installed:

- `pip`
- `pip-tools`
- `pip-review`
- `pkg-resources`
- `-markerlib`

Plus everything in `pip._internal.utils.compat.stdlib_pkgs` (the names `pip` itself considers
shadowing-the-stdlib).

Plus the names of "development packages" as defined by `pip._internal.metadata.get_dev_pkgs()` (packages
installed via `pip install --editable .` or `setup.py develop` that report themselves as
distinguishable).

## The dynamic list

The static list expands to its **transitive closure** at runtime. `pip-sync` walks the dependency tree
of every package in the static list and adds every dependency to the ignore set.

In practice this means:

- `pip-tools` is ignored, so all of its dependencies (`click`, `build`, `pyproject_hooks`, `tomli`,
  `setuptools`, `wheel`) are ignored.
- `build` pulls in `packaging` and `pyproject_hooks`, both ignored.
- `click` brings nothing further on Python 3.10+, so the chain ends.

The result is that running `pip-sync` against a `requirements.txt` that does not list any of these
packages does not remove them. They survive across syncs.

## What you cannot override

You cannot extend the ignore list from the command line. The only way to keep a package across syncs is
to list it in the lockfile.

You also cannot shrink the ignore list. `pip-sync` will never uninstall `pip` or `pip-tools` even if you
list a different version in `requirements.txt`. The note "`pip-sync` will not upgrade or uninstall
packaging tools like `setuptools`, `pip`, or `pip-tools` itself" in the README reflects this. Use
`python -m pip install --upgrade pip pip-tools` to update the tools themselves.

## What you can override (sort of)

The "unsafe" packages from `pip-compile` (`pip`, `setuptools`, `distribute`) are filtered from the
lockfile by default. If you want them in the lockfile so that `pip install -r` (not `pip-sync`) will
install specific versions, pass `--allow-unsafe` to `pip-compile`. They appear as ordinary pinned lines
in the file. `pip-sync` still ignores them at sync time, but a manual `pip install -r requirements.txt`
honours the pin.

## Why this exists

`pip-sync` runs safely twice in a row without breaking the environment that hosts it. Without the ignore
list, an `pip-sync` invocation that uninstalled `pip-tools` would leave the next one with
`command not found`. The list keeps that loop closed.

The trade-off is that "`pip-sync` makes the environment match the lockfile" has a footnote. The
environment matches the lockfile *plus* the tooling. Most of the time you want this. When you do not,
sync into a different Python via `--python-executable`. See {doc}`/how-to/sync-other-env`.

```{seealso}
- {doc}`/how-to/sync-environment` for the basic sync flow.
- {doc}`/explanation/unsafe-packages` for the parallel filter on `pip-compile`'s output.
```
