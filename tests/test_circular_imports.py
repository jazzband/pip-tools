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

import optparse
import os
import pkgutil
import subprocess
import sys
import typing as _t
from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from types import ModuleType

import pytest
from pytest_mock import MockerFixture

import piptools
from piptools._internal import _pip_api
from piptools._internal._pip_api import (
    cli_options,
    install_requirements,
    package_finder,
    pip_version,
)

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock


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
    # pkg_resources.declare_namespace() is deprecated. sphinxcontrib
    # packages that can land in the dev environment trigger it, and the
    # warning originates from pip's vendored copy of pkg_resources.
    flags.extend(("-W", "ignore::DeprecationWarning:pip._vendor.pkg_resources"))
    if _pip_api.PIP_VERSION_MAJOR_MINOR < (25, 3):
        flags.extend(
            ("-W", "ignore:pkg_resources is deprecated as an API.:DeprecationWarning:")
        )
    if _pip_api.PIP_VERSION_MAJOR_MINOR <= (22, 3):
        flags.extend(
            (
                "-W",
                ("ignore:path is deprecated. Use files() instead.:DeprecationWarning:"),
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


@pytest.mark.parametrize(
    ("func_name", "expected"),
    (
        pytest.param("finder_allows_prereleases_of_req", True, id="per-req"),
        pytest.param("finder_allows_all_prereleases", True, id="all"),
    ),
)
def test_finder_prerelease_functions_old_pip(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    func_name: str,
    expected: bool,
) -> None:
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (25, 0))
    finder: MagicMock = mocker.MagicMock()
    finder.allow_all_prereleases = expected
    func = getattr(package_finder, func_name)
    result = (
        func(finder, mocker.MagicMock())
        if func_name == "finder_allows_prereleases_of_req"
        else func(finder)
    )
    assert result is expected


def test_copy_install_requirement_old_pip_includes_install_options(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    # pip <= 23.0 passes ``install_options`` to the constructor; modern
    # pip rejects the kwarg, so without monkeypatching the version *and*
    # the constructor, the call raises before the test can verify the
    # branch fired. Capture the kwargs by stubbing ``InstallRequirement``
    # and assert the version-conditional kwarg lands in them.
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (23, 0))
    template = mocker.MagicMock()
    template.install_options = ["--prefix=/usr/local"]
    template.use_pep517 = False
    template.global_options = []
    template.original_link = None
    fake_ireq = mocker.patch.object(
        install_requirements, "InstallRequirement", autospec=False
    )
    install_requirements.copy_install_requirement(template)
    kwargs = fake_ireq.call_args.kwargs
    assert kwargs["install_options"] == ["--prefix=/usr/local"]
    assert kwargs["use_pep517"] is False
    assert kwargs["global_options"] == []


def test_postprocess_cli_options_old_pip_skips_release_control_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (25, 0))
    cli_options.postprocess_cli_options(optparse.Values())


@pytest.mark.parametrize(
    ("pip_version_tuple", "expected_filter_substring"),
    (
        pytest.param(
            (25, 0),
            "pkg_resources is deprecated as an API.",
            id="pip<25.3-adds-pkg-resources-filter",
        ),
        pytest.param(
            (22, 3),
            "path is deprecated.",
            id="pip<=22.3-adds-importlib-path-filter",
        ),
    ),
)
def test_allowed_deprecation_warning_filters_old_pip_branches(
    monkeypatch: pytest.MonkeyPatch,
    pip_version_tuple: tuple[int, int],
    expected_filter_substring: str,
) -> None:
    # Two version-conditional branches inside
    # ``_allowed_deprecation_warning_filters`` fire on pip releases
    # older than the supported minimum on modern dev machines. Force
    # the version to exercise each branch so coverage covers the
    # warning-filter additions instead of treating them as dead.
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", pip_version_tuple)
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", pip_version_tuple)
    flags = _allowed_deprecation_warning_filters()
    assert any(expected_filter_substring in flag for flag in flags)
