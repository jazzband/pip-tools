"""
Tests for the local 'piptools_coverage' plugin, found in 'tests/_plugins/_coverage/'.

Because the plugin is put into the pythonpath under pytest, it can be directly imported
during testsuite runs. Note, however, that it's difficult to check coverage of the
plugin itself, since it is imported and run before coverage collection begins.
"""

from __future__ import annotations

import datetime
from unittest import mock

import pytest

from piptools._internal import _pip_api

piptools_coverage = pytest.importorskip(
    "piptools_coverage",
    reason="piptools_coverage requires coverage and must be importable to be tested",
)


def test_plugin_major_minor_lookup_agrees_with_internal_api():
    assert piptools_coverage.get_pip_major_minor() == _pip_api.PIP_VERSION_MAJOR_MINOR


def test_max_pip_major_version_is_todays_year():
    jan_first_2002 = datetime.date(year=2002, month=1, day=1)
    jan_first_2076 = datetime.date(year=2076, month=1, day=1)

    mock_date_class = mock.Mock()
    mock_date_class.today.return_value = jan_first_2002
    with mock.patch("datetime.date", mock_date_class):
        assert piptools_coverage.get_max_pip_major_version() == 2

    mock_date_class.today.return_value = jan_first_2076
    with mock.patch("datetime.date", mock_date_class):
        assert piptools_coverage.get_max_pip_major_version() == 76


@pytest.mark.parametrize(
    ("pip_requirement", "expect_result"),
    (
        ("pip >= 19.1", 19),
        ("pip >= 44.3.2dev9", 44),
    ),
)
def test_get_min_pip_major_version_uses_pyproject_data(pip_requirement, expect_result):
    with mock.patch(
        "piptools_coverage.read_project_pyproject_toml"
    ) as mock_read_pyproject:
        mock_read_pyproject.return_value = {
            "project": {"dependencies": [pip_requirement]}
        }
        assert piptools_coverage.get_min_supported_pip_major_version() == expect_result


@pytest.mark.parametrize(
    "dependency_list",
    (
        pytest.param(["pip >= 19.1", "pip > 22.2"], id="multiple_pip_deps"),
        pytest.param(["pip >= 19.1, < 33"], id="multiple_specifiers"),
        pytest.param(["pip < 99"], id="not_lower_bound"),
    ),
)
def test_get_min_pip_major_version_raises_error_on_unrecognized_data(dependency_list):
    with mock.patch(
        "piptools_coverage.read_project_pyproject_toml"
    ) as mock_read_pyproject:
        mock_read_pyproject.return_value = {
            "project": {"dependencies": dependency_list}
        }
        with pytest.raises(piptools_coverage.UnrecognizedPipDependency):
            piptools_coverage.get_min_supported_pip_major_version()


def test_computed_pragmas_include_cover_of_exact_current_version():
    major, minor = _pip_api.PIP_VERSION_MAJOR_MINOR
    cover_eq_pragma = rf"# pragma: pip=={major}.{minor} cover\b"
    nocover_eq_pragma = rf"# pragma: pip=={major}.{minor} no cover\b"

    computed_pragmas = piptools_coverage.compute_pip_version_exclude_pragmas()
    assert cover_eq_pragma not in computed_pragmas
    assert nocover_eq_pragma in computed_pragmas


def test_computed_pragmas_state_no_cover_above_next_major_version():
    current_major, minor = _pip_api.PIP_VERSION_MAJOR_MINOR
    max_major = piptools_coverage.get_max_pip_major_version()

    if current_major >= max_major:
        pytest.skip(
            "cannot test piptools_coverage handling of next major version when at or "
            "above the computed maximum"
        )

    next_major = current_major + 1

    cover_eq_pragma = rf"# pragma: pip=={next_major}.{minor} cover\b"
    nocover_eq_pragma = rf"# pragma: pip=={next_major}.{minor} no cover\b"
    cover_ge_pragma = rf"# pragma: pip>={next_major}.{minor} cover\b"
    nocover_ge_pragma = rf"# pragma: pip>={next_major}.{minor} no cover\b"

    computed_pragmas = piptools_coverage.compute_pip_version_exclude_pragmas()

    assert cover_eq_pragma in computed_pragmas
    assert nocover_eq_pragma not in computed_pragmas
    assert cover_ge_pragma in computed_pragmas
    assert nocover_ge_pragma not in computed_pragmas


def test_computed_pragmas_state_no_cover_below_previous_major_version():
    current_major, minor = _pip_api.PIP_VERSION_MAJOR_MINOR
    min_major = piptools_coverage.get_min_supported_pip_major_version()

    if current_major <= min_major:
        pytest.skip(
            "cannot test piptools_coverage handling of previous major version when at or "
            "below the computed minimum"
        )

    prev_major = current_major - 1

    cover_eq_pragma = rf"# pragma: pip=={prev_major}.{minor} cover\b"
    nocover_eq_pragma = rf"# pragma: pip=={prev_major}.{minor} no cover\b"
    cover_le_pragma = rf"# pragma: pip<={prev_major}.{minor} cover\b"
    nocover_le_pragma = rf"# pragma: pip<={prev_major}.{minor} no cover\b"

    computed_pragmas = piptools_coverage.compute_pip_version_exclude_pragmas()

    assert cover_eq_pragma in computed_pragmas
    assert nocover_eq_pragma not in computed_pragmas
    assert cover_le_pragma in computed_pragmas
    assert nocover_le_pragma not in computed_pragmas
