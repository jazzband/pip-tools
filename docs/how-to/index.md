# How-to guides

Recipes for the things you do with `pip-tools`. Each page is short, scoped, and links back to the
explanation pages when context helps.

## Set up

- {doc}`install` installs `pip-tools` with `uv`, `pipx`, or `pip`.

## Compile a `requirements.txt`

- {doc}`compile-from-pyproject` compiles from PEP 621 `pyproject.toml`.
- {doc}`compile-from-requirements-in` compiles from a plain `requirements.in`.
- {doc}`compile-from-stdin` pipes input in or writes output to stdout.
- {doc}`compile-build-deps` includes build-system requirements in the output.
- {doc}`layered-requirements` shares pins between production, dev, test, and CI files.
- {doc}`vcs-and-url-deps` pins a Git commit, branch, tag, or remote archive.
- {doc}`use-hashes` produces `--require-hashes`-mode files.
- {doc}`update-dependencies` bumps one package, all packages, or none.
- {doc}`customize-output` controls headers, annotations, line endings, and emitted options.
- {doc}`time-travel-builds` pins to a historical PyPI snapshot via `--uploaded-prior-to`.
- {doc}`system-packages` aligns the lockfile with packages installed by the OS.
- {doc}`migrate-off-legacy-resolver` leaves `--resolver=legacy` behind before it goes away.

## Sync an environment

- {doc}`sync-environment` makes an environment match a `requirements.txt`.
- {doc}`sync-other-env` syncs an environment that isn't the one running `pip-sync`.
- {doc}`sync-interactive` previews, asks, and forces.

## Cross-cutting

- {doc}`private-indexes` points at a private index and configures certs and trusted hosts.
- {doc}`forward-pip-args` passes arguments straight through to `pip`.
- {doc}`custom-compile-command` rewrites the command shown in the file header.
- {doc}`use-with-pre-commit` wires `pip-compile` into `pre-commit`.
- {doc}`shell-completions` enables tab completion for `pip-compile` and `pip-sync`.

```{toctree}
:hidden:
:caption: Set up

install
```

```{toctree}
:hidden:
:caption: Compile a requirements.txt

compile-from-pyproject
compile-from-requirements-in
compile-from-stdin
compile-build-deps
layered-requirements
vcs-and-url-deps
use-hashes
update-dependencies
customize-output
time-travel-builds
system-packages
migrate-off-legacy-resolver
```

```{toctree}
:hidden:
:caption: Sync an environment

sync-environment
sync-other-env
sync-interactive
```

```{toctree}
:hidden:
:caption: Cross-cutting

private-indexes
forward-pip-args
custom-compile-command
use-with-pre-commit
shell-completions
```
