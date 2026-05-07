# Coexist with system-installed packages

System packages installed by `apt`, `dnf`, `apk`, or similar can collide with `pip-tools`. The
collisions show up two ways: `pip-compile` resolves a version `pip-sync` then refuses to overwrite, or
`pip-sync` uninstalls a package that the OS depends on. This page covers the patterns that work.

## What `pip-compile` sees

`pip-compile` does not look at currently-installed packages by default. It resolves against the
declared inputs (`requirements.in`, `pyproject.toml`, etc.) and the index. System-installed packages do
not influence the output unless you ask them to.

That means a system-installed `numpy==1.25.0` does not pin the lockfile to `1.25.0`; the resolver picks
the latest compatible version on PyPI. If you wanted the lockfile to match the system version, you have
to declare it.

## Declaring system pins as constraints

The cleanest pattern: write the system-provided versions to a constraints file and feed them in.

```text
# system-constraints.txt
numpy==1.25.0
scipy==1.11.0
```

```text
# requirements.in
-c system-constraints.txt

your-app
```

```console
pip-compile
```

`pip-compile` resolves around the constraints, picking versions that are both compatible with your app's
dependencies and with the system pins. The lockfile contains the constrained versions; `pip-sync` then
matches the lockfile against the venv.

## Two environments, one lockfile

A common scenario: a Docker image installs system packages, and you want a venv on the developer
laptop to mirror it.

The pragmatic flow:

1. List what the Docker image installs systemwide that overlaps with PyPI.
2. Capture their versions in a constraints file.
3. Run `pip-compile -c system-constraints.txt requirements.in` to produce a lockfile aligned with the
   system layer.
4. In the laptop venv, run `pip-sync requirements.txt` to install everything the lockfile mentions.
5. In the Docker image, install the system packages first, then `pip install --no-deps -r requirements.txt`
   for the rest. `--no-deps` prevents `pip` from re-installing the system-provided ones over the OS
   version.

The lockfile drives both environments; the system layer fills in what's already there.

## Avoiding `pip-sync` uninstalling system packages

`pip-sync` uninstalls anything in the venv that isn't in the lockfile. In a venv that's separate from
system Python (the usual setup), this is fine. In a system Python where you can't or don't want
`pip-sync` to remove distro-managed packages, do not run `pip-sync` against the system Python.

If you have to drive a system Python, install only into the user-site directory:

```console
pip-sync --user --python-executable /usr/bin/python3 requirements.txt
```

`--user` keeps writes inside `~/.local/`, separate from the system site-packages.

```{warning}
Even with `--user`, `pip-sync` builds the to-uninstall list from packages it finds in the target
Python's `sys.path`. System-managed packages may still appear. Use `pip-sync --dry-run` first and read
the plan; if it would remove anything from `/usr/lib/python3*/`, abort.
```

## Build dependencies that come from the system

A separate case: your project's PEP 517 backend needs `cython` or `setuptools-rust`, both of which the
distro provides. Without coordination, `pip-compile` installs them again from PyPI in an isolated build
env.

Two ways to use the system copies:

1. Pass `--no-build-isolation` to `pip-compile`. The build backend then runs against your current
   Python's site-packages, where the system or pre-installed copies live. This works when the system
   versions satisfy `[build-system].requires`. See {doc}`/explanation/build-system-integration`.
2. Pin the build dependencies in the lockfile (with `--all-build-deps`) and install them from PyPI.
   Slower at build time but the resulting lockfile is self-contained. See {doc}`compile-build-deps`.

## When the system is the wrong pin

A system Python might ship `pip==22.0.4` from two years ago. `pip-tools` itself requires `pip>=22.2`
(check `pip-compile --version` against your `pip-tools` version). If the system Python's `pip` is too
old, `pip-tools` fails at startup. The fix is to upgrade `pip` inside the venv (`python -m pip install
--upgrade pip`) or use a different interpreter via `--python-executable`. The system `pip` is rarely the
right tool driver.

```{seealso}
- {doc}`/explanation/build-system-integration` for `--no-build-isolation`.
- {doc}`/explanation/unsafe-packages` for why `pip-sync` ignores `pip` and `setuptools` regardless.
- {doc}`sync-other-env` for `--python-executable` semantics.
```
