"""Tests for circular imports in all local packages and modules.

This ensures all internal packages can be imported right away without
any need to import some other module before doing so.

This module is based on an idea that pytest uses for self-testing:
* https://github.com/aio-libs/aiohttp/blob/91108c9/tests/test_circular_imports.py
* https://github.com/sanitizers/octomachinery/blob/be18b54/tests/circular_imports_test.py
* https://github.com/pytest-dev/pytest/blob/d18c75b/testing/test_meta.py
* https://twitter.com/codewithanthony/status/1229445110510735361
"""

from __future__ import annotations

import os
import pkgutil
import subprocess
import sys
from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from types import ModuleType

import pytest

import piptools
from piptools._internal import _pip_api


def _find_all_importables(pkg: ModuleType) -> list[str]:
    """Find all importables in the project.

    Return them in order.
    """
    return sorted(
        set(
            chain.from_iterable(
                _discover_path_importables(Path(p), pkg.__name__) for p in pkg.__path__
            ),
        ),
    )


def _discover_path_importables(pkg_pth: Path, pkg_name: str) -> Iterator[str]:
    """Yield all importables under a given path and package."""
    for dir_path, _d, file_names in os.walk(pkg_pth):
        pkg_dir_path = Path(dir_path)

        if pkg_dir_path.parts[-1] == "__pycache__":
            continue

        if all(Path(_).suffix != ".py" for _ in file_names):  # pragma: no cover
            continue

        rel_pt = pkg_dir_path.relative_to(pkg_pth)
        pkg_pref = ".".join((pkg_name,) + rel_pt.parts)
        yield from (
            pkg_path
            for _, pkg_path, _ in pkgutil.walk_packages(
                (str(pkg_dir_path),),
                prefix=f"{pkg_pref}.",
            )
        )


def _allowed_deprecation_warning_filters() -> list[str]:
    """
    Yield filters which allow for deprecation warnings based on the current
    test environment.
    """
    # note that we can't use regex syntax in filters as of yet, only literals
    # https://github.com/python/cpython/pull/138149 allows regex usage, but is not
    # yet supported on all Python versions we support
    flags: list[str] = []
    if _pip_api.PIP_VERSION_MAJOR_MINOR < (25, 3):
        flags.extend(
            ("-W", "ignore:pkg_resources is deprecated as an API.:DeprecationWarning:")
        )
    if _pip_api.PIP_VERSION_MAJOR_MINOR <= (22, 2):
        flags.extend(
            (
                "-W",
                (
                    "ignore:path is deprecated. Use files() instead."
                    ":DeprecationWarning:"
                ),
                "-W",
                (
                    "ignore:Creating a LegacyVersion has been deprecated "
                    "and will be removed in the next major release"
                    ":DeprecationWarning:"
                ),
            )
        )
    return flags


@pytest.mark.parametrize("import_path", _find_all_importables(piptools))
def test_no_warnings(import_path: str) -> None:
    """Verify that each importable name can be independently imported.

    This is seeking for any import errors including ones caused
    by circular imports.
    """
    import_statement = f"import {import_path!s}"
    # On lower pip versions, we need to allow certain deprecation warnings.
    flags = ("-W", "error", *_allowed_deprecation_warning_filters())
    command = (sys.executable, *flags, "-c", import_statement)

    subprocess.check_call(command)
