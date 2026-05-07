<!-- pyml disable-next-line no-trailing-punctuation -->
# pip-tools

[![PyPI version][pypi-image]][pypi]
[![Python versions][pyversions-image]][pypi]
[![Jazzband][jazzband-image]][jazzband]
[![CI][buildstatus-image]][buildstatus]
[![Coverage][codecov-image]][codecov]

`pip-tools` keeps your `pip`-based packages fresh, even when you've pinned them. The current commands are
`pip-compile` and `pip-sync`. `pip-compile` reads your top-level dependencies from `pyproject.toml`,
`setup.cfg`, `setup.py`, or `requirements.in` and writes a pinned `requirements.txt` that any
`pip install -r` can replay. `pip-sync` then makes a virtual environment match that file: it installs what
you list, uninstalls what you don't, and upgrades anything that drifted.

The output file changes when something you asked about changes. A lockfile produced today is the same
contract every install gets until you re-compile.

## Quick navigation

- {doc}`tutorial/getting-started` pins and syncs a real project end to end.
- {doc}`how-to/index` for recipes: install, compile, sync, hashes, layered files, pre-commit.
- {doc}`reference/index` for every flag, every config key, every environment variable.
- {doc}`explanation/index` for the model: how the resolver works, why the output is stable, what
  `pip-compile` does versus what other tools do.
- {doc}`contributing` and {doc}`changelog`.

```{toctree}
:hidden:
:maxdepth: 2

tutorial/getting-started
how-to/index
reference/index
explanation/index
contributing
changelog
```

```{toctree}
:hidden:
:caption: Internal API reference

pkg/modules
```

[pypi]: https://pypi.org/project/pip-tools/
[pypi-image]: https://img.shields.io/pypi/v/pip-tools.svg
[pyversions-image]: https://img.shields.io/pypi/pyversions/pip-tools.svg
[jazzband]: https://jazzband.co/
[jazzband-image]: https://jazzband.co/static/img/badge.svg
[buildstatus]: https://github.com/jazzband/pip-tools/actions?query=workflow%3ACI
[buildstatus-image]: https://github.com/jazzband/pip-tools/workflows/CI/badge.svg
[codecov]: https://codecov.io/gh/jazzband/pip-tools
[codecov-image]: https://codecov.io/gh/jazzband/pip-tools/branch/main/graph/badge.svg
