from __future__ import annotations

import pytest

from piptools.pylock.platforms import PLATFORM_ENVIRONMENTS, build_target_environments


def test_all_platforms_have_required_keys() -> None:
    required = {
        "os_name",
        "sys_platform",
        "platform_machine",
        "platform_system",
        "implementation_name",
        "platform_python_implementation",
    }
    for name, env in PLATFORM_ENVIRONMENTS.items():
        assert required.issubset(env.keys()), f"{name} missing {required - env.keys()}"


@pytest.mark.parametrize(
    ("name", "os_name", "sys_platform", "platform_machine", "platform_system"),
    (
        pytest.param(
            "linux-x86_64", "posix", "linux", "x86_64", "Linux", id="linux-x86_64"
        ),
        pytest.param(
            "linux-aarch64", "posix", "linux", "aarch64", "Linux", id="linux-aarch64"
        ),
        pytest.param("linux-i686", "posix", "linux", "i686", "Linux", id="linux-i686"),
        pytest.param(
            "linux-armv7l", "posix", "linux", "armv7l", "Linux", id="linux-armv7l"
        ),
        pytest.param(
            "linux-ppc64le", "posix", "linux", "ppc64le", "Linux", id="linux-ppc64le"
        ),
        pytest.param(
            "linux-s390x", "posix", "linux", "s390x", "Linux", id="linux-s390x"
        ),
        pytest.param(
            "linux-riscv64", "posix", "linux", "riscv64", "Linux", id="linux-riscv64"
        ),
        pytest.param(
            "windows-amd64", "nt", "win32", "AMD64", "Windows", id="windows-amd64"
        ),
        pytest.param(
            "windows-arm64", "nt", "win32", "ARM64", "Windows", id="windows-arm64"
        ),
        pytest.param("windows-x86", "nt", "win32", "x86", "Windows", id="windows-x86"),
        pytest.param(
            "macos-x86_64", "posix", "darwin", "x86_64", "Darwin", id="macos-x86_64"
        ),
        pytest.param(
            "macos-arm64", "posix", "darwin", "arm64", "Darwin", id="macos-arm64"
        ),
        pytest.param(
            "android-aarch64",
            "posix",
            "android",
            "aarch64",
            "Android",
            id="android-aarch64",
        ),
        pytest.param(
            "android-x86_64",
            "posix",
            "android",
            "x86_64",
            "Android",
            id="android-x86_64",
        ),
        pytest.param("ios-arm64", "posix", "ios", "arm64", "iOS", id="ios-arm64"),
        pytest.param("ios-x86_64", "posix", "ios", "x86_64", "iOS", id="ios-x86_64"),
        pytest.param(
            "pyodide-wasm32",
            "posix",
            "emscripten",
            "wasm32",
            "Emscripten",
            id="pyodide-wasm32",
        ),
    ),
)
def test_platform_environment_fields(
    name: str,
    os_name: str,
    sys_platform: str,
    platform_machine: str,
    platform_system: str,
) -> None:
    env = PLATFORM_ENVIRONMENTS[name]
    assert env["os_name"] == os_name
    assert env["sys_platform"] == sys_platform
    assert env["platform_machine"] == platform_machine
    assert env["platform_system"] == platform_system


def test_all_platforms_cpython() -> None:
    for name, env in PLATFORM_ENVIRONMENTS.items():
        assert env["implementation_name"] == "cpython", f"{name} not cpython"
        assert env["platform_python_implementation"] == "CPython", f"{name} not CPython"


def test_platform_environments_are_marker_distinct() -> None:
    # Two presets sharing (sys_platform, platform_machine) would alias under
    # `--no-universal` autodetection and `compute_platform_marker`. Adding a
    # marker-aliased preset (e.g. an iOS simulator variant) is a UX bug.
    seen: dict[tuple[str, str], str] = {}
    for name, env in PLATFORM_ENVIRONMENTS.items():
        key = (env["sys_platform"], env["platform_machine"])
        assert (
            key not in seen
        ), f"{name} has the same (sys_platform, platform_machine) as {seen[key]}"
        seen[key] = name


@pytest.mark.parametrize(
    ("platforms", "python_versions", "expected_count"),
    (
        pytest.param(
            ("linux-x86_64",),
            ("3.12",),
            1,
            id="single-platform-single-version",
        ),
        pytest.param(
            ("linux-x86_64", "windows-amd64"),
            ("3.12",),
            2,
            id="two-platforms-single-version",
        ),
        pytest.param(
            ("linux-x86_64",),
            ("3.12", "3.13"),
            2,
            id="single-platform-two-versions",
        ),
        pytest.param(
            ("linux-x86_64", "windows-amd64"),
            ("3.12", "3.13"),
            4,
            id="two-platforms-two-versions",
        ),
    ),
)
def test_build_target_environments_count(
    platforms: tuple[str, ...],
    python_versions: tuple[str, ...],
    expected_count: int,
) -> None:
    result = build_target_environments(platforms, python_versions)
    assert len(result) == expected_count


def test_build_target_environments_keys() -> None:
    result = build_target_environments(("linux-x86_64",), ("3.12",))
    assert "linux-x86_64-3.12-cpython" in result


@pytest.mark.parametrize(
    ("version", "expected_short", "expected_full"),
    (
        pytest.param("3.13", "3.13", "3.13.0", id="major-minor-synthesizes-patch"),
        pytest.param("3.13.5", "3.13", "3.13.5", id="major-minor-patch-passthrough"),
    ),
)
def test_build_target_environments_python_fields(
    version: str, expected_short: str, expected_full: str
) -> None:
    result = build_target_environments(("linux-x86_64",), (version,))
    env = result[f"linux-x86_64-{version}-cpython"]
    assert env["python_version"] == expected_short
    assert env["python_full_version"] == expected_full
    assert env["implementation_version"] == expected_full
    assert env["sys_platform"] == "linux"


def test_build_target_environments_inherits_platform() -> None:
    result = build_target_environments(("windows-amd64",), ("3.12",))
    env = result["windows-amd64-3.12-cpython"]
    assert env["os_name"] == "nt"
    assert env["platform_machine"] == "AMD64"


def test_build_target_environments_cross_product() -> None:
    result = build_target_environments(
        ("linux-x86_64", "macos-arm64"), ("3.12", "3.13")
    )
    assert set(result.keys()) == {
        "linux-x86_64-3.12-cpython",
        "linux-x86_64-3.13-cpython",
        "macos-arm64-3.12-cpython",
        "macos-arm64-3.13-cpython",
    }


@pytest.mark.parametrize(
    ("implementation", "expected_name", "expected_pep"),
    (
        pytest.param("cpython", "cpython", "CPython", id="cpython"),
        pytest.param("pypy", "pypy", "PyPy", id="pypy"),
        pytest.param("graalpy", "graalpy", "GraalPy", id="graalpy"),
    ),
)
def test_build_target_environments_implementation_axis(
    implementation: str, expected_name: str, expected_pep: str
) -> None:
    result = build_target_environments(("linux-x86_64",), ("3.12",), (implementation,))
    env = result[f"linux-x86_64-3.12-{implementation}"]
    assert env["implementation_name"] == expected_name
    assert env["platform_python_implementation"] == expected_pep


def test_build_target_environments_unknown_implementation_capitalises() -> None:
    result = build_target_environments(("linux-x86_64",), ("3.12",), ("micropython",))
    env = result["linux-x86_64-3.12-micropython"]
    assert env["implementation_name"] == "micropython"
    assert env["platform_python_implementation"] == "Micropython"
