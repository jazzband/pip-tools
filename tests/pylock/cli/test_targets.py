from __future__ import annotations

import sys

import pytest
from pytest_mock import MockerFixture

from piptools.pylock.cli._targets import (
    _expand_requires_python,
    _infer_platforms,
    resolve_targets,
)


@pytest.mark.parametrize(
    ("env", "expected_platform"),
    (
        pytest.param(
            {"sys_platform": "win32", "platform_machine": "AMD64"},
            "windows-amd64",
            id="windows-amd64",
        ),
        pytest.param(
            {"sys_platform": "darwin", "platform_machine": "arm64"},
            "macos-arm64",
            id="macos-arm64",
        ),
    ),
)
def test_no_universal_resolves_unique_current_platform(
    mocker: MockerFixture,
    env: dict[str, str],
    expected_platform: str,
) -> None:
    # ``_infer_platforms`` walks ``PLATFORM_ENVIRONMENTS`` looking for one
    # entry that matches the current ``sys_platform`` and ``platform_machine``.
    # A future addition that introduces a duplicate match would flip the
    # user-facing error path for that platform without test coverage; the
    # parametrize asserts each non-Linux platform pip-tools ships resolves
    # to a single preset.

    mocker.patch("piptools.pylock.cli._targets.default_environment", return_value=env)
    assert _infer_platforms(no_universal=True) == (expected_platform,)


def test_resolve_targets_expands_current_to_host_preset(
    mocker: MockerFixture,
) -> None:
    # ``--platform current`` is shorthand for the host's auto-detected
    # preset. The expansion has to happen before ``build_target_environments``
    # would ``KeyError`` on the literal string "current".

    mocker.patch(
        "piptools.pylock.cli._targets.default_environment",
        return_value={"sys_platform": "linux", "platform_machine": "x86_64"},
    )
    targets = resolve_targets(
        ("current", "windows-amd64"), ("3.12",), no_universal=False
    )
    assert "linux-x86_64" in targets.platforms
    assert "windows-amd64" in targets.platforms
    assert "current" not in targets.platforms


def test_resolve_targets_expands_current_python_version() -> None:
    # ``--python-version current`` mirrors ``--platform current`` and expands
    # to the host's MAJOR.MINOR. The expansion has to happen before
    # ``build_target_environments`` would reject the literal string ``current``.
    targets = resolve_targets(("linux-x86_64",), ("current",), no_universal=False)
    host = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert host in targets.python_versions
    assert "current" not in targets.python_versions


def test_resolve_targets_universal_derives_python_axis_from_requires_python() -> None:
    # Without this, the universal default shrinks to the host interpreter
    # and drops every other supported python from the lock.
    targets = resolve_targets(
        ("linux-x86_64",),
        (),
        no_universal=False,
        project_requires_python=(">=3.10",),
    )
    assert "3.10" in targets.python_versions
    assert "3.14" in targets.python_versions
    assert all(v.startswith("3.") for v in targets.python_versions)


def test_resolve_targets_no_universal_keeps_host_only_python() -> None:
    # The host-only fallback applies when the user opted out of universal
    # mode; ``requires-python`` does not apply once the user signaled "lock
    # for what I run".
    targets = resolve_targets(
        ("linux-x86_64",),
        (),
        no_universal=True,
        project_requires_python=(">=3.10",),
    )
    host = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert targets.python_versions == (host,)


@pytest.mark.parametrize(
    ("specifiers", "must_include", "must_exclude"),
    (
        pytest.param(
            (">=3.10", "<3.13"),
            ("3.10", "3.11", "3.12"),
            ("3.13", "3.14"),
            id="intersection-of-multiple-specifiers",
        ),
        pytest.param(
            ("not-a-specifier", ">=3.12"),
            ("3.12", "3.13", "3.14"),
            ("3.10", "3.11"),
            id="invalid-specifier-skipped-others-narrow",
        ),
    ),
)
def test_expand_requires_python_honours_specifier_set(
    specifiers: tuple[str, ...],
    must_include: tuple[str, ...],
    must_exclude: tuple[str, ...],
) -> None:
    # Composite ``Requires-Python`` strings (one per source file) intersect to
    # the strict subset every input admits; a malformed specifier in one input
    # must not abort the universal lock and let the remaining specifiers narrow.
    versions = _expand_requires_python(specifiers)
    for version in must_include:
        assert version in versions
    for version in must_exclude:
        assert version not in versions


def test_expand_requires_python_returns_empty_when_no_input() -> None:
    # An empty specifier set means "no constraints declared"; the caller
    # falls back to the host interpreter rather than enumerating every
    # supported release in the universal lock.
    assert _expand_requires_python(()) == ()


def test_resolve_targets_empty_implementations_defaults_to_cpython() -> None:
    # Passing an empty implementations tuple lets the configured default
    # ("cpython",) take effect so the resolver never sees a zero-element
    # implementation axis.
    targets = resolve_targets(
        ("linux-x86_64",),
        ("3.12",),
        implementations=(),
        no_universal=True,
    )
    assert targets.implementations == ("cpython",)
    assert any(env.endswith("-cpython") for env in targets.target_envs)
