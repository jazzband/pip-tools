# Install `pip-tools`

`pip-tools` is a command-line tool. Install it into an isolated environment, not the system Python. Pick
the method that fits your setup.

## Decision tree

```{mermaid}
flowchart TD
    A{Have uv?} -->|Yes| U[uv tool install]
    A -->|No| B{Have pipx?}
    B -->|Yes| P[pipx install]
    B -->|No| C{Project venv already exists?}
    C -->|Yes| V[pip install pip-tools]
    C -->|No| D[Create a venv first]

    style A fill:#d97706,stroke:#b45309,color:#fff
    style B fill:#d97706,stroke:#b45309,color:#fff
    style C fill:#d97706,stroke:#b45309,color:#fff
    style U fill:#16a34a,stroke:#15803d,color:#fff
    style P fill:#16a34a,stroke:#15803d,color:#fff
    style V fill:#16a34a,stroke:#15803d,color:#fff
    style D fill:#7c3aed,stroke:#6d28d9,color:#fff
```

## Install

::::{tab} uv

[`uv`](https://docs.astral.sh/uv/) installs `pip-tools` as a [tool](https://docs.astral.sh/uv/concepts/tools/),
isolated from your projects:

```console
uv tool install pip-tools
```

The `pip-compile` and `pip-sync` commands land on your `PATH`.

To install the development version from `main`:

```console
uv tool install git+https://github.com/jazzband/pip-tools.git@main
```

::::

::::{tab} pipx

[`pipx`](https://pipx.pypa.io/) gives you the same isolation in pure Python:

```console
pipx install pip-tools
```

Development version:

```console
pipx install git+https://github.com/jazzband/pip-tools.git@main
```

For one-off invocations without installing:

```console
pipx run --spec pip-tools pip-compile pyproject.toml
```

::::

::::{tab} pip into a project venv

Install `pip-tools` into the same virtual environment as your project. `pip-compile` needs to read your
project's metadata; running it in a different environment risks resolving against the wrong Python.

:::{tab} Linux/macOS

```console
python -m venv .venv
source .venv/bin/activate
python -m pip install pip-tools
```

:::

:::{tab} Windows (PowerShell)

```console
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install pip-tools
```

:::

:::{tab} Windows (cmd)

```console
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install pip-tools
```

:::
::::

## Verifying

```console
$ pip-compile --version
pip-compile, version 7.5.3
$ pip-sync --version
pip-sync, version 7.5.3
```

If you see a different version than expected, your shell may be picking up a different `pip-compile` from
elsewhere on `PATH`:

```console
which pip-compile
command -v pip-compile
```

## Multi-Python projects

If your project supports multiple Python versions, install `pip-tools` once per Python version:

```console
python3.10 -m pip install pip-tools
python3.13 -m pip install pip-tools
```

Then invoke the matching version:

```console
python3.10 -m piptools compile
python3.13 -m piptools compile
```

The lockfile depends on the interpreter that resolves it. See {doc}`/explanation/cross-environment` for
why one file does not cover both.

## Updating

::::{tab} uv

```console
uv tool upgrade pip-tools
```

::::

::::{tab} pipx

```console
pipx upgrade pip-tools
```

::::

::::{tab} pip

```console
python -m pip install --upgrade pip-tools
```

::::
