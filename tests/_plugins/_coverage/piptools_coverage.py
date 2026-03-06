from __future__ import annotations

import datetime
import functools
import operator
import pathlib
import sys
import typing as _t

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from coverage import CoveragePlugin
from coverage.config import CoverageConfig
from coverage.plugin_support import Plugins
from packaging.requirements import Requirement
from packaging.version import Version


class UnrecognizedPipDependency(ValueError):
    pass


COMPARATORS: list[tuple[str, _t.Callable[[tuple[int, int], tuple[int, int]], bool]]] = [
    ("<", operator.lt),
    ("<=", operator.le),
    (">", operator.gt),
    (">=", operator.ge),
    ("==", operator.eq),
]


# pip uses 2-digit calver, so the current year is the latest possibly supported version
def _get_max_pip_major_version() -> int:
    return datetime.date.today().year - 2000


def _get_min_supported_pip_major_version() -> int:
    # the path to pyproject.toml is taken always from the CWD
    # since tests should always run under tox, this is always expected to be the repo root
    pyproject_path = pathlib.Path.cwd() / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        pyproject_toml = tomllib.load(pyproject_file)
    parsed_dependencies = [
        Requirement(d) for d in pyproject_toml["project"]["dependencies"]
    ]
    pip_requirements = [r for r in parsed_dependencies if r.name == "pip"]

    # we will presently assume that there's exactly one declared dependency on 'pip'
    # which sets the lower bound
    # if this changes in the future (e.g., we have different data for different markers)
    # then the plugin will need to be updated to ensure it parses that data correctly
    if len(pip_requirements) != 1:
        raise UnrecognizedPipDependency(
            "piptools_coverage is unable to determine the pip lower bound. "
            "Please update the plugin to handle changes to piptools metadata."
        )

    pip_specifier_set = pip_requirements[0].specifier
    if len(pip_specifier_set) != 1:
        raise UnrecognizedPipDependency(
            "piptools_coverage is unable to determine the pip lower bound. "
            "Please update the plugin to handle changes to piptools metadata."
        )

    pip_specifier = next(iter(pip_specifier_set))
    if pip_specifier.operator != ">=":
        raise UnrecognizedPipDependency(
            "piptools_coverage is unable to determine the pip lower bound. "
            "Please update the plugin to handle changes to piptools metadata."
        )

    version = Version(pip_specifier.version)
    return version.major


def _list_supported_pip_versions() -> list[tuple[int, int]]:
    return [
        (major, minor)
        for major in range(
            _get_min_supported_pip_major_version(), _get_max_pip_major_version() + 1
        )
        for minor in (0, 1, 2, 3)
    ]


@functools.cache
def get_pip_major_minor() -> tuple[int, int]:
    import pip
    from pip._vendor.packaging.version import parse as parse_version

    base_version = parse_version(pip.__version__).base_version
    major_str, minor_str = base_version.split(".")[:2]

    return int(major_str), int(minor_str)


def _compute_pip_version_exclude_pragmas() -> list[str]:
    current_major, current_minor = get_pip_major_minor()

    result: list[str] = [
        rf"# pragma: pip=={current_major}.{current_minor} no cover\b",
    ]

    for major, minor in _list_supported_pip_versions():
        for opname, opfunc in COMPARATORS:
            if opfunc((current_major, current_minor), (major, minor)):
                result.append(rf"# pragma: pip{opname}{major}.{minor} no cover\b")
            else:
                result.append(rf"# pragma: pip{opname}{major}.{minor} cover\b")

    return result


class PipVersionPragmas(CoveragePlugin):  # type: ignore[misc]
    def configure(self, config: CoverageConfig) -> None:
        exclude = set(config.get_option("report:exclude_lines"))
        exclude.update(_compute_pip_version_exclude_pragmas())
        config.set_option("report:exclude_lines", sorted(exclude))


def coverage_init(registry: Plugins, options: dict[str, object]) -> None:
    registry.add_configurer(PipVersionPragmas())
