# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from abc import ABCMeta, abstractmethod

from six import add_metaclass


@add_metaclass(ABCMeta)
class BaseRepository(object):

    def clear_caches(self):
        """Should clear any caches used by the implementation."""

    def freshen_build_caches(self):
        """Should start with fresh build/source caches."""

    @abstractmethod
    def find_best_match(self, ireq):
        """Return a Version object.

        This object indicates the best match for the given
        InstallRequirement according to the repository.
        """

    @abstractmethod
    def get_dependencies(self, ireq):
        """Returns a set of dependencies.

        The returned dependencies are InstallRequirements, but are not necessarily pinned.
        They indicate the secondary dependencies for the given requirement.

        Args:
            ireq: a pinned or editable InstallRequirement
        """

    @abstractmethod
    def get_hashes(self, ireq):
        """Returns a set of hashses that represent all of the files for a requirement.

        It is not acceptable for an editable or unpinned requirement to be passed
        to this function.

        Args:
            ireq: a pinned InstallRequirement
        """
