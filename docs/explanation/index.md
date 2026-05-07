# Explanation

This section answers "why does it work this way?" rather than "how do I do X?". Read it once when you want
the model in your head; come back to specific pages when something surprises you.

## What `pip-tools` does

`pip-tools` makes `pip` repeatable. Today it ships two commands:

- **`pip-compile`** turns a list of what you want (top-level dependencies) into a `requirements.txt` that
  describes what to install (every transitive package, pinned to a version that resolves).
- **`pip-sync`** makes a virtual environment match a `requirements.txt`. It installs what's missing,
  uninstalls what isn't listed, and upgrades anything that drifted.

Together they replace "whatever `pip install` happened to pick last time" with a checked-in contract. The
contract is plain `pip` syntax. No custom format, no custom installer, no daemon. Anyone with `pip` can
replay the install.

## What `pip-tools` is not

`pip-tools` is a CLI, not a Python library. The modules under `piptools.*` appear in the internal API
reference for contributors, not for callers. They track `pip`'s private API and break together with it on
new `pip` releases. If you want a programmatic resolver with a stable API, look at `uv` or `poetry`.

`pip-tools` also does not run your code, manage virtual environments, or publish to PyPI. It produces and
applies dependency pins; everything else is your shell, your build tool, or your CI.

## How the pieces fit

```{mermaid}
flowchart LR
    A[pyproject.toml<br/>setup.cfg<br/>setup.py<br/>requirements.in] --> B[pip-compile]
    B --> C{{requirements.txt}}
    C --> D[pip-sync]
    D --> E[venv]
    C -.->|pip install -r| F[any environment]

    style A fill:#2563eb,stroke:#1d4ed8,color:#fff
    style B fill:#6366f1,stroke:#4f46e5,color:#fff
    style C fill:#16a34a,stroke:#15803d,color:#fff
    style D fill:#6366f1,stroke:#4f46e5,color:#fff
    style E fill:#16a34a,stroke:#15803d,color:#fff
    style F fill:#7c3aed,stroke:#6d28d9,color:#fff
```

`pip-compile` reads top-level requirements from one or more sources, asks an index (PyPI by default) for
candidate versions, runs `pip`'s resolver, and writes a pinned `requirements.txt`. `pip-sync` reads that
file, compares it to the currently installed packages, then runs `pip install` and `pip uninstall` until
the environment matches.

## Pages in this section

- {doc}`how-pip-compile-works` walks the resolution loop, including the static-vs-PEP-517 fast path.
- {doc}`stable-output` covers the local-pin proxy that prevents churn between runs.
- {doc}`caching` describes the three caches `pip-tools` keeps and what `--rebuild` clears.
- {doc}`resolvers` compares the backtracking and legacy resolvers.
- {doc}`build-system-integration` covers PEP 517 backends, build isolation, and `PIP_CONSTRAINT`.
- {doc}`strip-extras-and-constraints` covers why `--strip-extras` is becoming the default.
- {doc}`unsafe-packages` covers why `setuptools`, `pip`, and `distribute` get filtered.
- {doc}`cross-environment` covers why one lockfile cannot cover all platforms.
- {doc}`reproducibility` covers builds that survive an audit.
- {doc}`comparison` compares `pip-tools` to `uv`, `poetry`, `pdm`, `hatch`, and plain `pip`.
- {doc}`deprecations` covers defaults that are flipping and flags that are leaving.

```{toctree}
:hidden:

how-pip-compile-works
stable-output
caching
resolvers
build-system-integration
strip-extras-and-constraints
unsafe-packages
cross-environment
reproducibility
comparison
deprecations
```
