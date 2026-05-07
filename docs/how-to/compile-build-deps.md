# Include build dependencies

PEP 517 build backends declare static build dependencies in `[build-system].requires`. Backends can also
declare dynamic build dependencies via the `get_requires_for_build_wheel`/`sdist`/`editable` hooks. Both
sets matter for reproducible builds and neither appears in the lockfile by default.

`pip-compile` exposes three flags to pull them in.

## `--build-deps-for=<target>`

Pin the build dependencies for one specific build target (`sdist`, `wheel`, or `editable`):

```console
pip-compile --build-deps-for=wheel pyproject.toml
```

Output picks up the static `build-system.requires` plus the dynamic deps for `wheel`. Each gets a `# via`
annotation that traces the source:

```text
hatchling==1.21.0
    # via my-app (pyproject.toml::build-system.backend::wheel)
setuptools-scm==8.0.4
    # via my-app (pyproject.toml::build-system.requires)
```

## `--all-build-deps`

Pin build dependencies for every target:

```console
pip-compile --all-build-deps pyproject.toml
```

Equivalent to passing `--build-deps-for=sdist`, `--build-deps-for=wheel`, and
`--build-deps-for=editable` together. Use this in CI when the project produces both an sdist and a
wheel, or when you do not know in advance which target will get used.

## `--only-build-deps`

Pin only the build dependencies and drop the project's own runtime requirements:

```console
pip-compile --only-build-deps --all-build-deps pyproject.toml
```

`--only-build-deps` requires either `--build-deps-for` or `--all-build-deps`. The output contains the
build deps but none of the runtime dependencies declared in `[project].dependencies`.

This is the right shape for a constraints file driving the build environment of a downstream consumer:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-cool-django-app"
version = "42"
dependencies = ["django"]

[project.optional-dependencies]
dev = ["pytest"]
```

```console
$ pip-compile \
    --all-build-deps \
    --all-extras \
    --output-file=constraints.txt \
    --strip-extras \
    pyproject.toml
```

```text
asgiref==3.5.2
    # via django
attrs==22.1.0
    # via pytest
django==4.1
    # via my-cool-django-app (pyproject.toml)
editables==0.3
    # via hatchling
hatchling==1.11.1
    # via my-cool-django-app (pyproject.toml::build-system.requires)
iniconfig==1.1.1
    # via pytest
packaging==21.3
    # via
    #   hatchling
    #   pytest
pathspec==0.10.2
    # via hatchling
pluggy==1.0.0
    # via
    #   hatchling
    #   pytest
pytest==7.1.2
    # via my-cool-django-app (pyproject.toml)
sqlparse==0.4.2
    # via django
tomli==2.0.1
    # via
    #   hatchling
    #   pytest
```

The same file:

- installs as `pip install -r constraints.txt` (everything pinned, no extras);
- works as `PIP_CONSTRAINT=constraints.txt python -m build` (constrains the build environment);
- works as `pip install -c constraints.txt my-cool-django-app[dev]` (constrains downstream installs).

## Annotations

Build-dep annotations include the source they came from:

- `(pyproject.toml::build-system.requires)` for the static list.
- `(pyproject.toml::build-system.backend::sdist)` for dynamic deps requested by `get_requires_for_build_sdist`.
- `(pyproject.toml::build-system.backend::wheel)` for `get_requires_for_build_wheel`.
- `(pyproject.toml::build-system.backend::editable)` for `get_requires_for_build_editable`.

Reading the annotation tells you whether removing the package from the build manifest is safe.

## Constraints with `--upgrade-package`

When you compile with `--upgrade-package foo` and `foo` is also a build dependency, `pip-compile` writes
the upgrade list to a temporary file and sets `PIP_CONSTRAINT` for the build subprocess. The build
environment ends up using the same upgraded version. This works without ceremony; you do not need to set
the variable yourself.

## Caveats

```{warning}
`--build-deps-for` and `--all-build-deps` cannot be combined. Pass one or the other.

`--only-build-deps` cannot be combined with `--extra` or `--all-extras`. The build graph is separate
from the extras graph.

Build-deps mode requires a project source (`pyproject.toml`, `setup.py`, or `setup.cfg`). A plain
`requirements.in` has no build backend to ask.
```

```{seealso}
- {doc}`/explanation/build-system-integration` for the static-vs-PEP-517 fast path and how
  `PIP_CONSTRAINT` flows into isolated build environments.
- {doc}`/explanation/reproducibility` for the full reproducible-build checklist.
```
