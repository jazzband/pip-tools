from __future__ import annotations

import pytest
from packaging import markers as _markers_mod
from packaging.markers import Marker
from pip._vendor.packaging.markers import Marker as VendoredMarker

from piptools.pylock._marker_eval import (
    mock_marker_environment,
    platform_blind_marker_eval,
)
from piptools.pylock.platforms import TargetEnvironment, build_target_environments


def _windows_target_env() -> TargetEnvironment:
    return build_target_environments(("windows-amd64",), ("3.12",))[
        "windows-amd64-3.12-cpython"
    ]


def _linux_target_env() -> TargetEnvironment:
    return build_target_environments(("linux-x86_64",), ("3.12",))[
        "linux-x86_64-3.12-cpython"
    ]


def test_mock_marker_environment_overrides_default() -> None:
    original = _markers_mod.default_environment()
    with mock_marker_environment(_windows_target_env()):
        mocked = _markers_mod.default_environment()
        assert mocked["sys_platform"] == "win32"
        assert mocked["os_name"] == "nt"

    restored = _markers_mod.default_environment()
    assert restored["sys_platform"] == original["sys_platform"]


def _raise_inside_mock(env: TargetEnvironment) -> None:
    with mock_marker_environment(env):
        raise ValueError("test")


def test_mock_marker_environment_restores_on_exception() -> None:
    original = _markers_mod.default_environment()
    with pytest.raises(ValueError, match="test"):
        _raise_inside_mock(_windows_target_env())

    restored = _markers_mod.default_environment()
    assert restored["sys_platform"] == original["sys_platform"]


def test_mock_marker_environment_evaluates_markers() -> None:
    win_marker = Marker("sys_platform == 'win32'")
    linux_marker = Marker("sys_platform == 'linux'")

    with mock_marker_environment(_windows_target_env()):
        assert win_marker.evaluate()
        assert not linux_marker.evaluate()

    with mock_marker_environment(_linux_target_env()):
        assert not win_marker.evaluate()
        assert linux_marker.evaluate()


def test_platform_blind_marker_eval_forces_platform_to_true() -> None:
    win_marker = Marker("sys_platform == 'win32'")
    env = {"sys_platform": "linux", "python_version": "3.12"}
    assert win_marker.evaluate(env) is False
    with platform_blind_marker_eval():
        assert win_marker.evaluate(env) is True
        py_marker = Marker("python_version == '3.12'")
        assert py_marker.evaluate(env) is True
        py_marker_other = Marker("python_version == '3.10'")
        assert py_marker_other.evaluate(env) is False
    assert win_marker.evaluate(env) is False


def test_platform_blind_marker_eval_patches_vendored_packaging() -> None:
    # Pip's resolver evaluates dep markers via pip._vendor.packaging.markers,
    # not the top-level package; patching only the latter would silently drop
    # every transitive `sys_platform == 'win32'` dependency from the scan.
    win_marker = VendoredMarker("sys_platform == 'win32'")
    env = {"sys_platform": "linux", "python_version": "3.12"}
    assert win_marker.evaluate(env) is False
    with platform_blind_marker_eval():
        assert win_marker.evaluate(env) is True
    assert win_marker.evaluate(env) is False


def test_platform_blind_evaluator_recurses_into_nested_lists() -> None:
    nested = Marker(
        "(sys_platform == 'win32' or sys_platform == 'darwin') "
        "and python_version >= '3.12'"
    )
    env = {"sys_platform": "linux", "python_version": "3.12"}
    assert nested.evaluate(env) is False
    with platform_blind_marker_eval():
        assert nested.evaluate(env) is True


def test_platform_blind_evaluator_handles_value_lhs_variable_rhs() -> None:
    extras_marker = Marker("'gpu' in extras")
    env = {"sys_platform": "linux", "python_version": "3.12", "extras": "gpu"}
    with platform_blind_marker_eval():
        assert extras_marker.evaluate(env) is True
