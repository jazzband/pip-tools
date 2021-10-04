from __future__ import annotations

import optparse
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager

from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.index import PyPI
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement


class BaseRepository(metaclass=ABCMeta):
    DEFAULT_INDEX_URL = PyPI.simple_url

    def clear_caches(self) -> None:
        """Should clear any caches used by the implementation."""

    @abstractmethod
    def find_best_match(
        self, ireq: InstallRequirement, prereleases: bool | None
    ) -> InstallRequirement:
        """
        Returns a pinned InstallRequirement object that indicates the best match
        for the given InstallRequirement according to the external repository.
        """

    @abstractmethod
    def get_dependencies(self, ireq: InstallRequirement) -> set[InstallRequirement]:
        """
        Given a pinned, URL, or editable ``InstallRequirement``, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """

    @abstractmethod
    def get_hashes(
        self, ireq: InstallRequirement, single_hash: bool = False
    ) -> set[str]:
        """
        Given a pinned ``InstallRequirement``, return a set of hashes that can be used to verify the
        file to install for the requirement. If single_hash is True, the set will only have the
        hash for the best matching file to install based on the current execution environment. When
        False (the default), include hashes for all of the files for a given requirement.

        Files that are unhashable are excluded from the returned set.

        A TypeError is raised if the given requirement is editable or unpinned.
        """

    @abstractmethod
    @contextmanager
    def allow_all_wheels(self) -> Iterator[None]:
        """
        Monkey patches pip.Wheel to allow wheels from all platforms and Python versions.
        """

    @property
    @abstractmethod
    def options(self) -> optparse.Values:
        """Returns parsed pip options"""

    @property
    @abstractmethod
    def session(self) -> PipSession:
        """Returns a session to make requests"""

    @property
    @abstractmethod
    def finder(self) -> PackageFinder:
        """Returns a package finder to interact with simple repository API (PEP 503)"""

    @property
    @abstractmethod
    def command(self) -> InstallCommand:
        """Return an install command."""
