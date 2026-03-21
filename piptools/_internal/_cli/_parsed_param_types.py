from __future__ import annotations

import pathlib

import click


class ParsedDependencyGroupParam:
    """
    Parse a dependency group input, but retain the input value.

    Splits on the rightmost ":", and validates that the path (if present) ends
    in ``pyproject.toml``. Defaults the path to ``pyproject.toml`` when one is not given.

    ``:`` cannot appear in dependency group names, so this is a safe and simple parse.

    If the path portion ends in ":", then the ":" is removed, effectively resulting in
    a split on "::" when that is used.

    The following conversions are expected::

        'foo' -> ('pyproject.toml', 'foo')
        'foo/pyproject.toml:bar' -> ('foo/pyproject.toml', 'bar')
        'foo/pyproject.toml::bar' -> ('foo/pyproject.toml', 'bar')
    """

    def __init__(self, value: str) -> None:
        self.input_arg = value

        path, sep, groupname = value.rpartition(":")
        if not sep:
            path = "pyproject.toml"
        else:
            # strip a rightmost ":" if one was present
            if path.endswith(":"):
                path = path[:-1]
            # check for 'pyproject.toml' filenames using pathlib
            if pathlib.PurePath(path).name != "pyproject.toml":
                msg = "group paths use 'pyproject.toml' filenames"
                raise click.UsageError(msg)

        self.path = path
        self.group = groupname

    def __str__(self) -> str:
        return self.input_arg
