from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess
from typing import Protocol, TypedDict

# NOTE: keep in sync with "passenv" in tox.ini
CI_VARIABLES = {"CI", "GITHUB_ACTIONS"}


def looks_like_ci():
    return bool(set(os.environ.keys()) & CI_VARIABLES)


class MakePackageProtocol(Protocol):
    """
    The protocol implemented by the ``make_package`` fixture.
    """

    def __call__(
        self,
        name: str,
        version: str = "0.1",
        install_requires: Sequence[str] | None = None,
        extras_require: dict[str, str | list[str]] | None = None,
    ) -> Path:
        ...


class MakePackageArgs(TypedDict, total=False):
    name: str
    version: str
    install_requires: Sequence[str] | None
    extras_require: dict[str, str | list[str]] | None


class RunSetupFileProtocol(Protocol):
    """
    The protocol implemented by the ``run_setup_file`` fixture.
    """

    def __call__(self, package_dir_path: Path, *args: str) -> CompletedProcess[bytes]:
        ...


class MakeSDistProtocol(Protocol):
    """
    The protocol implemented by the ``make_sdist`` fixture.
    """

    def __call__(
        self, package_dir: Path, dist_dir: str | Path, *args: str
    ) -> CompletedProcess[bytes]:
        ...
