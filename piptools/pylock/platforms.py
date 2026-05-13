"""Lock targets pip-tools knows how to build a marker environment for."""

from __future__ import annotations

import typing as _t

from packaging.markers import Environment


class PlatformEnvironment(_t.TypedDict):
    """The platform-side fields PEP 508 markers evaluate against."""

    os_name: str
    sys_platform: str
    platform_machine: str
    platform_system: str
    implementation_name: str
    platform_python_implementation: str


class ImplementationEnvironment(_t.TypedDict):
    """``implementation_name`` and ``platform_python_implementation`` together."""

    implementation_name: str
    platform_python_implementation: str


IMPLEMENTATION_ENVIRONMENTS: dict[str, ImplementationEnvironment] = {
    "cpython": {
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
    },
    "pypy": {
        "implementation_name": "pypy",
        "platform_python_implementation": "PyPy",
    },
    "graalpy": {
        "implementation_name": "graalpy",
        "platform_python_implementation": "GraalPy",
    },
}


# Populated marker environment for one ``(platform, python)`` cell. Aliased
# to ``packaging.markers.Environment`` so a marker field added upstream lands here
# without a parallel edit in pip-tools.
TargetEnvironment: _t.TypeAlias = Environment


# ``os_key -> (os_name, sys_platform, platform_system)``. Used by the
# preset table and the best-effort synthesiser; one row per OS spelling.
_OS_PROFILE: _t.Final[dict[str, tuple[str, str, str]]] = {
    "linux": ("posix", "linux", "Linux"),
    "windows": ("nt", "win32", "Windows"),
    "macos": ("posix", "darwin", "Darwin"),
    "android": ("posix", "android", "Android"),
    "ios": ("posix", "ios", "iOS"),
    "pyodide": ("posix", "emscripten", "Emscripten"),
}


def _env_for(os_key: str, machine: str) -> PlatformEnvironment:
    os_name, sys_platform, platform_system = _OS_PROFILE[os_key]
    return {
        "os_name": os_name,
        "sys_platform": sys_platform,
        "platform_machine": machine,
        "platform_system": platform_system,
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
    }


# ``<os>-<arch>`` keys; arch matches ``platform.machine()``. Only
# marker-distinct combinations live here (musl vs glibc collapse to the
# same env).
PLATFORM_ENVIRONMENTS: dict[str, PlatformEnvironment] = {
    "linux-x86_64": _env_for("linux", "x86_64"),
    "linux-aarch64": _env_for("linux", "aarch64"),
    "linux-i686": _env_for("linux", "i686"),
    "linux-armv7l": _env_for("linux", "armv7l"),
    "linux-ppc64le": _env_for("linux", "ppc64le"),
    "linux-s390x": _env_for("linux", "s390x"),
    "linux-riscv64": _env_for("linux", "riscv64"),
    "windows-amd64": _env_for("windows", "AMD64"),
    "windows-arm64": _env_for("windows", "ARM64"),
    "windows-x86": _env_for("windows", "x86"),
    "macos-x86_64": _env_for("macos", "x86_64"),
    "macos-arm64": _env_for("macos", "arm64"),
    "android-aarch64": _env_for("android", "aarch64"),
    "android-x86_64": _env_for("android", "x86_64"),
    "ios-arm64": _env_for("ios", "arm64"),
    "ios-x86_64": _env_for("ios", "x86_64"),
    "pyodide-wasm32": _env_for("pyodide", "wasm32"),
}


_PLATFORM_SYSTEM_FIXED_CASING: _t.Final[dict[str, str]] = {
    "freebsd": "FreeBSD",
    "openbsd": "OpenBSD",
    "netbsd": "NetBSD",
    "aix": "AIX",
    "sunos": "SunOS",
    "darwin": "Darwin",
    "linux": "Linux",
    "windows": "Windows",
    "android": "Android",
    "ios": "iOS",
    "emscripten": "Emscripten",
}


def build_target_environments(
    platforms: tuple[str, ...],
    python_versions: tuple[str, ...],
    implementations: tuple[str, ...] = ("cpython",),
) -> dict[str, TargetEnvironment]:
    """Expand platforms x python versions x implementations into marker envs.

    Env keys are ``<platform>-<version>-<implementation>`` so multiple
    implementations against the same ``(platform, python)`` can coexist.

    :param platforms: Platform names (built-in or freeform ``<os>-<arch>`` pairs).
    :param python_versions: Python versions in ``MAJOR.MINOR`` or ``MAJOR.MINOR.PATCH`` form.
    :param implementations: ``implementation_name`` values; defaults to ``cpython``.
    :returns: Mapping from ``<platform>-<version>-<impl>`` keys to populated
        marker environments.
    """
    result: dict[str, TargetEnvironment] = {}
    for platform in platforms:
        platform_env = PLATFORM_ENVIRONMENTS.get(
            platform, _best_effort_platform_env(platform)
        )
        for version in python_versions:
            # MAJOR.MINOR vs MAJOR.MINOR.PATCH: honour explicit patch
            parts = version.split(".")
            python_full_version = version if len(parts) == 3 else f"{version}.0"
            for implementation in implementations:
                impl_env = IMPLEMENTATION_ENVIRONMENTS.get(
                    implementation,
                    {
                        "implementation_name": implementation,
                        "platform_python_implementation": implementation.capitalize(),
                    },
                )
                result[f"{platform}-{version}-{implementation}"] = {
                    "os_name": platform_env["os_name"],
                    "sys_platform": platform_env["sys_platform"],
                    "platform_machine": platform_env["platform_machine"],
                    "platform_system": platform_env["platform_system"],
                    "implementation_name": impl_env["implementation_name"],
                    "platform_python_implementation": impl_env[
                        "platform_python_implementation"
                    ],
                    "python_version": ".".join(parts[:2]),
                    "python_full_version": python_full_version,
                    "implementation_version": python_full_version,
                    "platform_release": "",
                    "platform_version": "",
                }
    return result


def _best_effort_platform_env(platform: str) -> PlatformEnvironment:
    """Synthesize a marker env for an ``<os>-<arch>`` not in the built-in set.

    PEP 508 markers cover the user's target when every keyed-on field has
    a sensible value. Unknown OSes get ``os_name=posix`` (the dominant case;
    Windows is the common exception and it's already in the presets) and
    a ``sys_platform`` derived from the ``<os>`` prefix. ``platform_machine``
    is the trailing ``<arch>`` token verbatim. ``platform_system`` matches
    ``platform.system()``'s casing (``FreeBSD``, ``AIX``, ...) so markers
    like ``platform_system == 'FreeBSD'`` evaluate to True against the
    target. The user is responsible for knowing whether the deduced
    markers match their target.
    """
    os_name, _, machine = platform.partition("-")
    return {
        "os_name": "nt" if os_name in {"windows", "cygwin"} else "posix",
        "sys_platform": "win32" if os_name == "windows" else os_name,
        "platform_machine": machine,
        "platform_system": _PLATFORM_SYSTEM_FIXED_CASING.get(
            os_name, os_name.capitalize() if os_name else ""
        ),
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
    }


def parse_env_key(env_key: str) -> tuple[str, str, str]:
    """Split ``<platform>-<version>-<impl>`` into its three axes.

    ``<platform>`` itself may carry an internal ``-`` (e.g. ``linux-x86_64``),
    so peel impl and version off the tail with ``rpartition`` before the
    remainder is taken as the platform.
    """
    head, _, implementation = env_key.rpartition("-")
    platform, _, version = head.rpartition("-")
    return platform, version, implementation


def to_marker_env(env: TargetEnvironment) -> dict[str, str]:
    """Return the target environment as a plain marker-environment mapping.

    :param env: Target environment with full marker fields populated.
    :returns: A plain string-to-string dict suitable for marker evaluation.
    """
    return _t.cast("dict[str, str]", env)


__all__ = [
    "IMPLEMENTATION_ENVIRONMENTS",
    "ImplementationEnvironment",
    "PLATFORM_ENVIRONMENTS",
    "PlatformEnvironment",
    "TargetEnvironment",
    "build_target_environments",
    "parse_env_key",
    "to_marker_env",
]
