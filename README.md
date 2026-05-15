<!-- pyml disable-next-line first-line-heading -->
[![jazzband-image]][jazzband]
[![pypi][pypi-image]][pypi]
[![pyversions][pyversions-image]][pyversions]
[![pre-commit][pre-commit-image]][pre-commit]
[![buildstatus-gha][buildstatus-gha-image]][buildstatus-gha]
[![codecov][codecov-image]][codecov]
[![Matrix Room Badge]][Matrix Room]
[![Matrix Space Badge]][Matrix Space]
[![discord-chat-image]][discord-chat]

# pip-tools = pip-compile + pip-sync

`pip-tools` keeps your `pip`-based packages fresh, even when you've pinned them.

`pip-compile` reads your top-level dependencies from `pyproject.toml`, `setup.cfg`, `setup.py`, or
`requirements.in` and writes a pinned `requirements.txt` that `pip install -r` can replay. `pip-sync`
makes a virtual environment match that file: it installs what you list, uninstalls what you don't, and
upgrades anything that drifted.

[**Full documentation**][docs]

## Install

```console
python -m pip install pip-tools          # into your project venv
pipx install pip-tools                   # isolated install via pipx
uv tool install pip-tools                # isolated install via uv
```

[Install guide][install-doc] for `uv`, `pipx`, and per-project setups.

## Compile a `requirements.txt`

```console
pip-compile -o requirements.txt pyproject.toml
```

```text
asgiref==3.7.2
    # via django
django==4.2.7
    # via my-app (pyproject.toml)
sqlparse==0.4.4
    # via django
```

`pip-compile` reads `[project].dependencies` from `pyproject.toml` (or a `requirements.in`, `setup.py`,
or `setup.cfg`), resolves transitive dependencies, and pins everything. The output is plain `pip` syntax
that any `pip install -r` can install.

Bump one package without disturbing the rest:

```console
pip-compile -P django
```

Bump everything:

```console
pip-compile --upgrade
```

## Sync an environment

```console
pip-sync requirements.txt
```

`pip-sync` makes the active virtual environment match `requirements.txt`. It installs what's missing,
uninstalls what isn't listed, and upgrades anything that drifted.

To sync a different environment without activating it:

```console
pip-sync --python-executable .venv/bin/python requirements.txt
```

## Where to read next

- [Tutorial][tutorial-doc]: zero to a syncable project in ten minutes.
- [How-to guides][howto-doc]: hashes, layered files, build deps, private indexes, pre-commit, and more.
- [Explanation][explanation-doc]: why `pip-compile` is stable across runs, how the resolver works,
  comparisons with `uv`, `poetry`, and `pdm`.
- [CLI reference][cli-doc]: every flag for both commands.

## Contributing

This is a [Jazzband][jazzband] project. By contributing you agree to abide by the
[Contributor Code of Conduct][coc] and follow the [guidelines][jazzband-guidelines]. See
[CONTRIBUTING.md][contributing] for the development workflow.

[docs]: https://pip-tools.readthedocs.io/en/latest/
[install-doc]: https://pip-tools.readthedocs.io/en/latest/how-to/install.html
[tutorial-doc]: https://pip-tools.readthedocs.io/en/latest/tutorial/getting-started.html
[howto-doc]: https://pip-tools.readthedocs.io/en/latest/index.html#how-to-guides
[explanation-doc]: https://pip-tools.readthedocs.io/en/latest/index.html#explanation
[cli-doc]: https://pip-tools.readthedocs.io/en/latest/reference/cli.html
[jazzband]: https://jazzband.co/
[jazzband-image]: https://jazzband.co/static/img/badge.svg
[jazzband-guidelines]: https://jazzband.co/about/guidelines
[coc]: https://jazzband.co/about/conduct
[contributing]: https://github.com/jazzband/pip-tools/blob/main/CONTRIBUTING.md
[pypi]: https://pypi.org/project/pip-tools/
[pypi-image]: https://img.shields.io/pypi/v/pip-tools.svg
[pyversions]: https://pypi.org/project/pip-tools/
[pyversions-image]: https://img.shields.io/pypi/pyversions/pip-tools.svg
[pre-commit]: https://results.pre-commit.ci/latest/github/jazzband/pip-tools/main
[pre-commit-image]: https://results.pre-commit.ci/badge/github/jazzband/pip-tools/main.svg
[buildstatus-gha]: https://github.com/jazzband/pip-tools/actions?query=workflow%3ACI
[buildstatus-gha-image]: https://github.com/jazzband/pip-tools/workflows/CI/badge.svg
[codecov]: https://codecov.io/gh/jazzband/pip-tools
[codecov-image]: https://codecov.io/gh/jazzband/pip-tools/branch/main/graph/badge.svg
[Matrix Room Badge]: https://img.shields.io/matrix/pip-tools:matrix.org?label=Discuss%20on%20Matrix%20at%20%23pip-tools%3Amatrix.org&logo=matrix&server_fqdn=matrix.org&style=flat
[Matrix Room]: https://matrix.to/#/%23pip-tools:matrix.org
[Matrix Space Badge]: https://img.shields.io/matrix/jazzband:matrix.org?label=Discuss%20on%20Matrix%20at%20%23jazzband%3Amatrix.org&logo=matrix&server_fqdn=matrix.org&style=flat
[Matrix Space]: https://matrix.to/#/%23jazzband:matrix.org
[discord-chat]: https://discord.gg/pypa
[discord-chat-image]: https://img.shields.io/discord/803025117553754132?label=Discord%20chat%20%23pip-tools&style=flat-square
