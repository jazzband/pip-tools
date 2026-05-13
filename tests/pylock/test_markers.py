from __future__ import annotations

import pytest

from piptools.pylock.markers import build_combined_marker, compute_platform_marker


@pytest.mark.parametrize(
    ("envs", "all_envs", "expected"),
    (
        pytest.param(
            {"linux-x86_64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython"},
            None,
            id="single-env-is-all",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            id="all-envs-no-marker",
        ),
        pytest.param(
            {"windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            "sys_platform == 'win32'",
            id="windows-only",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            "sys_platform == 'linux'",
            id="linux-only",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "linux-aarch64-3.12-cpython"},
            {
                "linux-x86_64-3.12-cpython",
                "linux-aarch64-3.12-cpython",
                "windows-amd64-3.12-cpython",
            },
            "sys_platform == 'linux'",
            id="all-linux-archs-simplify",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython"},
            {
                "linux-x86_64-3.12-cpython",
                "linux-aarch64-3.12-cpython",
                "windows-amd64-3.12-cpython",
            },
            "sys_platform == 'linux' and platform_machine == 'x86_64'",
            id="specific-linux-arch",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "macos-arm64-3.12-cpython"},
            {
                "linux-x86_64-3.12-cpython",
                "macos-arm64-3.12-cpython",
                "windows-amd64-3.12-cpython",
            },
            "(sys_platform == 'darwin' or sys_platform == 'linux')",
            id="multiple-platforms-or",
        ),
        pytest.param(
            {"windows-amd64"},
            {"linux-x86_64", "windows-amd64"},
            "sys_platform == 'win32'",
            id="bare-platform-keys-without-version",
        ),
        pytest.param(
            {"android-aarch64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "android-aarch64-3.12-cpython"},
            "sys_platform == 'android'",
            id="android-only",
        ),
        pytest.param(
            {"ios-arm64-3.12-cpython", "ios-x86_64-3.12-cpython"},
            {
                "ios-arm64-3.12-cpython",
                "ios-x86_64-3.12-cpython",
                "linux-x86_64-3.12-cpython",
            },
            "sys_platform == 'ios'",
            id="all-ios-archs-simplify",
        ),
        pytest.param(
            {"pyodide-wasm32-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "pyodide-wasm32-3.12-cpython"},
            "sys_platform == 'emscripten'",
            id="pyodide-only",
        ),
        pytest.param(
            {"linux-x86_64-3.10-cpython", "windows-amd64-3.10-cpython"},
            {
                "linux-x86_64-3.10-cpython",
                "linux-x86_64-3.11-cpython",
                "windows-amd64-3.10-cpython",
                "windows-amd64-3.11-cpython",
            },
            "python_version == '3.10'",
            id="all-platforms-single-python",
        ),
        pytest.param(
            {
                "linux-x86_64-3.10-cpython",
                "windows-amd64-3.10-cpython",
                "linux-x86_64-3.11-cpython",
                "windows-amd64-3.11-cpython",
            },
            {
                "linux-x86_64-3.10-cpython",
                "linux-x86_64-3.11-cpython",
                "linux-x86_64-3.12-cpython",
                "windows-amd64-3.10-cpython",
                "windows-amd64-3.11-cpython",
                "windows-amd64-3.12-cpython",
            },
            "(python_version == '3.10' or python_version == '3.11')",
            id="all-platforms-two-pythons-of-three",
        ),
        pytest.param(
            {
                "windows-amd64-3.10-cpython",
                "windows-amd64-3.11-cpython",
                "windows-amd64-3.12-cpython",
            },
            {
                "linux-x86_64-3.10-cpython",
                "linux-x86_64-3.11-cpython",
                "linux-x86_64-3.12-cpython",
                "windows-amd64-3.10-cpython",
                "windows-amd64-3.11-cpython",
                "windows-amd64-3.12-cpython",
            },
            "sys_platform == 'win32'",
            id="single-platform-all-pythons-drops-version",
        ),
        pytest.param(
            {"linux-x86_64-3.10-cpython"},
            {
                "linux-x86_64-3.10-cpython",
                "linux-x86_64-3.11-cpython",
                "windows-amd64-3.10-cpython",
                "windows-amd64-3.11-cpython",
            },
            "sys_platform == 'linux' and python_version == '3.10'",
            id="single-platform-single-python",
        ),
        pytest.param(
            {"linux-x86_64-3.10.5-cpython"},
            {"linux-x86_64-3.10.5-cpython", "linux-x86_64-3.11.0-cpython"},
            "python_full_version == '3.10.5'",
            id="patch-version-uses-python-full-version",
        ),
    ),
)
def test_compute_platform_marker(
    envs: set[str], all_envs: set[str], expected: str | None
) -> None:
    result = compute_platform_marker(envs, all_envs)
    assert result == expected


@pytest.mark.parametrize(
    ("platform_envs", "all_envs", "extras_needed", "expected"),
    (
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            None,
            id="unconditional",
        ),
        pytest.param(
            {"windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            "sys_platform == 'win32'",
            id="platform-only",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"dev"},
            "'dev' in extras",
            id="extras-only",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"dev", "test"},
            "('dev' in extras or 'test' in extras)",
            id="multiple-extras",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"gpu"},
            "'gpu' in extras and sys_platform == 'linux'",
            id="extras-plus-platform",
        ),
    ),
)
def test_build_combined_marker(
    platform_envs: set[str],
    all_envs: set[str],
    extras_needed: set[str] | None,
    expected: str | None,
) -> None:
    result = build_combined_marker(platform_envs, all_envs, extras_needed)
    assert result == expected


@pytest.mark.parametrize(
    ("platform_envs", "all_envs", "extras_needed", "groups_needed", "expected"),
    (
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            {"test"},
            "'test' in dependency_groups",
            id="groups-only",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            {"test", "dev"},
            "('dev' in dependency_groups or 'test' in dependency_groups)",
            id="multiple-groups",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            None,
            {"test"},
            "'test' in dependency_groups and sys_platform == 'linux'",
            id="groups-and-platform",
        ),
        pytest.param(
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"dev"},
            {"test"},
            "('dev' in extras or 'test' in dependency_groups)",
            id="extras-and-groups-ored",
        ),
    ),
)
def test_build_combined_marker_with_groups(
    platform_envs: set[str],
    all_envs: set[str],
    extras_needed: set[str] | None,
    groups_needed: set[str] | None,
    expected: str | None,
) -> None:
    result = build_combined_marker(
        platform_envs, all_envs, extras_needed, groups_needed
    )
    assert result == expected
