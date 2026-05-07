# `pip-compile` versus other tools

Several Python tools produce or update lockfiles. They make different trade-offs. This page covers the
ones you most often see proposed as alternatives.

## `uv pip compile`

[`uv`](https://docs.astral.sh/uv/) is a Rust-based package manager from Astral. Its `uv pip compile`
command is a deliberate near-drop-in for `pip-compile`:

- It accepts the same source formats: `requirements.in`, `pyproject.toml`, `setup.cfg`, `setup.py`.
- It produces the same `requirements.txt` shape, with the same `# via` annotations.
- It supports `--generate-hashes`, layered `-c` constraints, `--upgrade`, `--upgrade-package`, and
  `--strip-extras`.

Where it differs:

- **Speed**. `uv pip compile` is faster on cold runs and on large constraint pools. The difference is
  pronounced for `--generate-hashes`, where `uv` parallelises hash fetching aggressively.
- **Resolver**. `uv` uses its own resolver, written in Rust on top of PubGrub. Most graphs resolve
  identically; pathological cases sometimes go differently.
- **Stability**. `uv` is younger; its CLI surface is still settling. `pip-compile`'s CLI is stable.

Pick `uv pip compile` if you already use `uv` for installs or speed dominates. Pick `pip-compile` if you
need maximum compatibility with `pip` semantics, want to stay on a CPython-only tooling stack, or rely on
`pip-tools` features `uv` does not yet replicate (the `LocalRequirementsRepository` proxy, the dependency
JSON cache for the legacy resolver).

## `poetry lock`

[Poetry](https://python-poetry.org/) is a project-management tool. `poetry lock` produces a `poetry.lock`
file that is *not* a `requirements.txt`. Installing it requires Poetry. Two implications:

- The lockfile carries information `requirements.txt` cannot: per-platform pins, multiple environments
  in one file, source metadata.
- The lockfile is unreadable to `pip install -r`. Anyone consuming your project needs Poetry too, or you
  need `poetry export -f requirements.txt` as an extra step.

Pick Poetry if you want a single tool managing dependencies, virtual environments, builds, and publishing.
Pick `pip-compile` if you want plain `pip`-compatible output and prefer to compose smaller tools.

## `pdm lock`

[PDM](https://pdm-project.org/) is similar in spirit to Poetry, with a different lockfile format
(`pdm.lock`). It supports PEP 582 in-project package layouts. The same `requirements.txt` non-portability
applies: installs need PDM.

Pick PDM if you want PEP 582 or its dependency-group ergonomics, accept the custom lockfile format. Pick
`pip-compile` if you want output any `pip` can install.

## `hatch`

[Hatch](https://hatch.pypa.io/) is a project manager focused on environments and builds. It does not have
its own resolver; it delegates to `pip` (or to `uv`, optionally). Hatch and `pip-compile` solve different
problems and compose well. Use Hatch for environments and builds, `pip-compile` for pinning.

## `pip freeze`

`pip freeze` writes whatever happens to be installed in the current environment. That is not a lockfile:

- It does not pin transitive dependencies you didn't explicitly install. If a package was installed and
  later removed, `pip freeze` reflects only what's left.
- It carries no "via" annotations; you cannot tell which packages are top-level versus transitive.
- It cannot regenerate. If you delete the venv, you have to re-resolve from scratch.

`pip freeze` is fine for reporting. It is not a lockfile. Use `pip-compile`.

## Quick comparison

| Tool | Output format | `pip install -r` works | Cross-platform | Speed |
|------|---------------|------------------------|----------------|-------|
| `pip-compile` | `requirements.txt` | yes | per-environment file | seconds |
| `uv pip compile` | `requirements.txt` | yes | per-environment file | sub-second |
| `poetry lock` | `poetry.lock` | no, needs Poetry | yes | seconds |
| `pdm lock` | `pdm.lock` | no, needs PDM | yes | seconds |
| `pip freeze` | `requirements.txt` | yes | current env only | instant |

The "cross-platform" column matters when your CI matrix has more than one row. See
{doc}`cross-environment` for what "per-environment" means in practice.

## When to migrate

`pip-compile` to `uv pip compile`: low risk, near-drop-in. Worth trying when speed is the constraint.

`pip-compile` to `poetry`/`pdm`: higher risk, larger surface area change. Worth it when you want one tool
to also manage virtual environments, builds, and publishing. Not worth it just for the lockfile format.

`pip freeze` to `pip-compile`: always. `pip freeze` is not a lockfile.
