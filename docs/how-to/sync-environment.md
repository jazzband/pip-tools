# Sync an environment

`pip-sync` makes a virtual environment match a `requirements.txt`. It installs what's listed,
uninstalls what isn't, and upgrades anything that drifted.

## Basic usage

In an active virtual environment:

```console
pip-sync
```

`pip-sync` reads `requirements.txt` from the current directory by default. It calls `pip install` and
`pip uninstall` to converge the environment.

## Multiple input files

```console
pip-sync requirements.txt dev-requirements.txt
```

`pip-sync` merges the inputs: any package listed in any file gets installed; anything installed but not
listed in any file gets uninstalled. Conflicting pins (same package, different version across the
files) raise an error. Pass `--force` to use the last-occurrence resolution if you accept the risk.

## What gets uninstalled

`pip-sync` uninstalls packages that are not in the lockfile, with several exceptions baked in:

- `pip` and `pip-tools` themselves.
- All of `pip-tools`'s transitive dependencies (so `click`, `build`, `pyproject_hooks`, etc. survive).
- Stdlib-shadowing pseudo-packages (`pip-review`, `pkg-resources`, `-markerlib`).
- Development packages installed via `setup.py develop` or similar.

The full ignore list lives in {doc}`/reference/sync-ignore-list`. The intent is "do not break the tools
you used to set up the environment".

## What does not get installed

`pip-sync` does not install:

- Editable installs into the current environment if not in the lockfile. Editables in the lockfile
  install normally (as `-e <link>`).
- VCS sources without a hash, when the existing install matches the URL. The diff key for URL
  requirements without a hash is the URL itself, which means the package always reinstalls.

## Inspecting before applying

`--dry-run` (`-n`) prints the plan and exits non-zero:

```console
(venv) $ pip-sync --dry-run
Would install:
  django==4.2.7
Would uninstall:
  flask==3.0.0
```

The non-zero exit is intentional: it lets `pip-sync --dry-run` be used as "is the environment
in sync?" check in CI:

```console
pip-sync --dry-run requirements.txt && echo synced || echo drifted
```

See {doc}`sync-interactive` for the prompt-and-confirm variant.

## Forcing on `.in` inputs

```{warning}
`pip-sync` rejects `.in` files by default. Running `pip-sync requirements.in` instead of
`pip-sync requirements.txt` is a common mistake; the safety check stops you from syncing against an
unpinned source file.
```

```console
(venv) $ pip-sync requirements.in
ERROR: Some input files have the .in extension, which is most likely an error
```

If the `.in` extension is intentional (the file contains the pinned versions you want), pass `--force`:

```console
(venv) $ pip-sync --force requirements.in
WARNING: Some input files have the .in extension, which is most likely an error
```

## Forwarding pip arguments

`--pip-args` passes a string of flags to the underlying `pip install` and `pip uninstall`:

```console
pip-sync --pip-args "--no-cache-dir --no-deps"
```

Use this for index URLs, certs, network options, and anything `pip-sync` does not surface natively. See
{doc}`forward-pip-args`.

## Index, find-links, certificates

`pip-sync` accepts the same network flags as `pip-compile`:

```console
pip-sync --index-url https://my-index.example.com/simple
pip-sync --find-links ./vendor/wheels
pip-sync --cert /path/to/ca.pem
pip-sync --trusted-host my-index.example.com
```

These compose with whatever was emitted into the lockfile (unless you stripped it with `--no-emit-*`
during compile). See {doc}`private-indexes`.

## When `pip-sync` is not what you want

`pip-sync` is for "make this environment match this lockfile". For other shapes:

- Adding one package without a re-compile: `pip install <name>`. Then re-compile to update the lockfile.
- Installing without uninstalling anything: `pip install -r requirements.txt`. This installs the listed
  packages but leaves drift in place.
- Production deploys with strict hashes: `pip install --require-hashes -r requirements.txt`. `pip-sync`
  does call `pip install` under the hood, but for production deploys the strict mode is more explicit.

```{seealso}
- {doc}`sync-other-env` for `pip-sync --python-executable` to sync a different environment.
- {doc}`sync-interactive` for `--ask` and `--dry-run` workflows.
```
