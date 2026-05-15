# Sync an environment that isn't yours

`pip-sync --python-executable <path>` operates on a different virtual environment than the one running
`pip-sync`. This lets you keep `pip-tools` installed once and use it to drive every project's environment.

## Basic usage

```console
pip-sync --python-executable /path/to/other/.venv/bin/python requirements.txt
```

`pip-sync` reads `sys.path` from the target Python via a subprocess, queries the installed packages there,
diffs them against the lockfile, and runs `pip install` and `pip uninstall` against the target.

The target Python must have `pip` installed at a version `pip-tools` accepts. `pip-sync` validates the
target's `pip` version against `pip-tools`'s `pip` requirement at startup; if it mismatches you get an
error like:

```text
ERROR: Target python executable '/path/to/python' has pip version 21.0 installed.
       Version >=22.2 is expected.
```

Upgrade `pip` in the target environment, or in `pip-tools`'s install location.

## Use cases

**Keep `pip-tools` out of the project venv.** Install `pip-tools` once via `uv tool install` or `pipx`,
then drive every project from there:

```console
pipx install pip-tools
cd ~/code/project-a
pip-sync --python-executable .venv/bin/python requirements.txt
cd ~/code/project-b
pip-sync --python-executable .venv/bin/python requirements.txt
```

The project venvs stay clean. `pip-tools`'s own dependencies do not leak in.

**Sync a venv from outside it.** A common workflow is "the venv is for the application; my shell is
elsewhere". `--python-executable` lets you sync without activating:

```console
pip-sync --python-executable .venv/bin/python requirements.txt
```

**Sync an air-gapped or container Python.** Cross-runtime sync also works for "the Python lives in a
container I bind-mounted":

```console
pip-sync --python-executable /mounted/container/venv/bin/python requirements.txt
```

The sync runs in your shell; `pip install` and `pip uninstall` run inside the target. The target needs
write access to its own site-packages.

## Resolving aliases

`--python-executable` accepts anything `shutil.which` accepts. An alias on `PATH` works:

```console
pip-sync --python-executable python3.13 requirements.txt
```

`pip-sync` resolves `python3.13` to the absolute path. If it cannot resolve the name, you get:

```text
ERROR: Could not resolve 'python3.13' as valid executable path or alias.
```

## With `--user`

`--user` restricts `pip-sync` to the user-site-packages of the target Python. Useful for system-Python
syncs where you cannot or do not want to write to the global site:

```console
pip-sync --python-executable /usr/bin/python3 --user requirements.txt
```

`pip install` and `pip uninstall` get `--user` forwarded.

## With dry-run and ask

The interactive flags compose:

```console
pip-sync --python-executable .venv/bin/python --dry-run requirements.txt
pip-sync --python-executable .venv/bin/python --ask requirements.txt
```

See {doc}`sync-interactive`.

## Caveats

```{warning}
The target Python must have `pip` installed at a version `pip-tools` accepts. A bare
`python -m venv --without-pip` venv fails. `pip-sync` also needs to spawn the target as a subprocess;
containerised or sandboxed targets that block subprocess invocation will not work.
```

The target's pip cache is separate from `pip-tools`'s. Network downloads can happen twice when you
drive several environments back to back.

```{warning}
Running `pip-sync` from a Python in isolated mode (`-I`) does not propagate isolation to the target
Python. The subprocess that reads `sys.path` from the target inherits the user-site and `sys.path[0]`
from the target's environment, not from yours. If you need a deterministic `sys.path`, set
`PYTHONNOUSERSITE=1` and `PYTHONSAFEPATH=1` in the target's environment before invoking `pip-sync`. See
[issue #2117](https://github.com/jazzband/pip-tools/issues/2117).
```
