# Build-system integration

When a project declares its dependencies in `pyproject.toml`, `setup.cfg`, or `setup.py`, `pip-compile`
needs to extract those dependencies before it can resolve them. There are two paths.

## The static fast path

If you use a `pyproject.toml` with a `[project]` table, and neither `dependencies` nor
`optional-dependencies` appears in `[project].dynamic`, `pip-compile` reads the dependencies straight from
the TOML.

```toml
[project]
name = "my-app"
version = "1.0"
dependencies = ["django"]

[project.optional-dependencies]
dev = ["pytest"]
```

The static parse:

1. Loads the TOML.
2. Walks `project.dependencies` and `project.optional-dependencies`.
3. Builds `InstallRequirement` objects in memory.
4. Hands them to the resolver.

No subprocess, no isolated environment, no PEP 517 backend invocation. On a typical project this finishes
in milliseconds.

## The PEP 517 path

The static path does not work in three cases:

- The project uses `setup.py` or `setup.cfg`.
- The project uses `pyproject.toml` but `dependencies` or `optional-dependencies` appears in
  `[project].dynamic`. Setuptools-with-dynamic-deps and Hatch-with-version-from-VCS are both common.
- You passed `--build-deps-for` or `--all-build-deps`. Build requirements live in
  `[build-system].requires` and behind the optional `get_requires_for_build_*` PEP 517 hooks. Reading them
  needs the backend.

```{mermaid}
flowchart TD
    Start([Source is pyproject.toml / setup.py / setup.cfg]) --> Static{Static parse possible?}
    Static -->|Yes| Read[Read project.dependencies directly]
    Static -->|No| Iso[Create isolated build env]
    Iso --> Install[Install build-system.requires]
    Install --> Hook[Run prepare_metadata_for_build_wheel]
    Hook --> Parse[Read Requires-Dist from generated metadata]
    Read --> Done([Constraints handed to resolver])
    Parse --> Done

    style Start fill:#2563eb,stroke:#1d4ed8,color:#fff
    style Done fill:#16a34a,stroke:#15803d,color:#fff
    style Read fill:#16a34a,stroke:#15803d,color:#fff
    style Static fill:#d97706,stroke:#b45309,color:#fff
    style Iso fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Install fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Hook fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Parse fill:#7c3aed,stroke:#6d28d9,color:#fff
```

The PEP 517 path uses `pypa/build` and `pyproject_hooks`:

1. Create an isolated environment via `build.env.DefaultIsolatedEnv()`.
2. Install everything from `build-system.requires` into that environment.
3. Optionally install the dynamic build requirements returned by
   `get_requires_for_build_wheel`/`sdist`/`editable`.
4. Call `prepare_metadata_for_build_wheel` (or fall back to `build_wheel`) and read `Requires-Dist` from
   the resulting metadata.

This path costs seconds, sometimes more on first run when the build env has to populate. After that the
wheel cache helps.

## Build isolation

By default the build env is isolated: the project's runtime dependencies are not visible to the backend.
That is the spec-correct behaviour and the safe default. When the backend imports something it shouldn't,
the build fails loudly instead of silently picking up whatever happened to be installed.

To turn isolation off, pass `--no-build-isolation`. The backend then runs in `pip-compile`'s own
environment and any packages required by the backend must already be installed there. Use this when:

- you have already vendored the build deps locally and want to skip the install step in CI;
- the backend imports a tool you cannot vendor (rare, usually a smell);
- you want to debug a build issue and need a stable interpreter.

## `PIP_CONSTRAINT` for the build env

When you compile with `--upgrade-package foo`, you want the new version of `foo` to be honoured at every
layer: in your project's runtime deps, and in the build environment if `foo` is a build dependency.

`pip-compile` writes the upgrade list to a temporary file and sets `PIP_CONSTRAINT` to that path before
spawning the backend. `pip` (used inside `build.env.DefaultIsolatedEnv()` to install build deps) reads the
constraint file the same way as if you had passed `-c`. The build env ends up using the same versions you
asked the resolver to use.

This is the same `PIP_CONSTRAINT` you can set yourself in production builds to lock build-time
dependencies; see {doc}`reproducibility`.

## Build dependencies in the lockfile

Three flags control whether build deps end up in the output:

- `--all-build-deps` walks `sdist`, `wheel`, and `editable` targets. Each gets its own `# via` annotation
  showing the source, for example
  `(my-cool-django-app (pyproject.toml::build-system.backend::wheel))`.
- `--build-deps-for=wheel` walks one target.
- `--only-build-deps` keeps the build deps and drops the project's own runtime requirements. Use this with
  `--strip-extras` to produce a constraints file you can hand to `PIP_CONSTRAINT` in CI.

{doc}`/how-to/compile-build-deps` walks the worked example.

## Why this split exists

PEP 517 mandates that backends declare their build requirements in metadata, not in the static project
table. The static fast path covers the runtime declaration only, which is enough for most users. The
PEP 517 path covers the rest. Splitting the two means the cheap case stays cheap and the expensive case
stays correct.
