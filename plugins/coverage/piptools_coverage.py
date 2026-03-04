from __future__ import annotations

import datetime
import functools
import typing as _t

from coverage import CoveragePlugin
from coverage.config import CoverageConfig
from coverage.plugin_support import Plugins

# only support versions which are explicitly listed
# support starts from our lowest supported major version and includes all minor versions
# pip uses calver, so we can count years from 2023 up to the current year
CURRENT_YEAR_EPOCH = datetime.date.today().year - 2000
_PRAGMA_SUPPORTED_PIP_VERSIONS: list[tuple[int, int]] = [
    (major, minor)
    for major in range(22, CURRENT_YEAR_EPOCH + 1)
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

    for major, minor in _PRAGMA_SUPPORTED_PIP_VERSIONS:
        if (current_major, current_minor) == (major, minor):
            result.extend(
                [
                    rf"# pragma: pip>={major}.{minor} no cover\b",
                    rf"# pragma: pip<={major}.{minor} no cover\b",
                ]
            )
        elif (current_major, current_minor) > (major, minor):
            result.extend(
                [
                    rf"# pragma: pip>{major}.{minor} no cover\b",
                    rf"# pragma: pip>={major}.{minor} no cover\b",
                ]
            )
        elif (current_major, current_minor) < (major, minor):
            result.extend(
                [
                    rf"# pragma: pip<{major}.{minor} no cover\b",
                    rf"# pragma: pip<={major}.{minor} no cover\b",
                ]
            )

    return result


class PipVersionPragmas(CoveragePlugin):  # type: ignore[misc]
    def configure(self, config: CoverageConfig) -> None:
        exclude = set(config.get_option("report:exclude_lines"))
        exclude.update(_compute_pip_version_exclude_pragmas())
        config.set_option("report:exclude_lines", sorted(exclude))


def coverage_init(registry: Plugins, options: dict[str, _t.Any]) -> None:
    registry.add_configurer(PipVersionPragmas())
