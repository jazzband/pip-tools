# coding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import sys

from pip._vendor.packaging.requirements import Requirement

from ._compat.typing import MYPY
from .exceptions import PipToolsError
from .locations import CACHE_DIR
from .utils import as_tuple, key_from_req, lookup_table

if MYPY:
    from typing import Dict, List, Optional, Set, Tuple
    from ._compat import InstallRequirement


class CorruptCacheError(PipToolsError):
    def __init__(self, path):
        # type: (str) -> None
        self.path = path

    def __str__(self):
        # type: () -> str
        lines = [
            "The dependency cache seems to have been corrupted.",
            "Inspect, or delete, the following file:",
            "  {}".format(self.path),
        ]
        return os.linesep.join(lines)


def read_cache_file(cache_file_path):
    # type: (str) -> Dict[str, dict]
    with open(cache_file_path, "r") as cache_file:
        try:
            doc = json.load(cache_file)
        except ValueError:
            raise CorruptCacheError(cache_file_path)

        # Check version and load the contents
        if doc["__format__"] != 1:
            raise AssertionError("Unknown cache file format")
        return doc["dependencies"]


class DependencyCache(object):
    """
    Creates a new persistent dependency cache for the current Python version.
    The cache file is written to the appropriate user cache dir for the
    current platform, i.e.

        ~/.cache/pip-tools/depcache-pyX.Y.json

    Where X.Y indicates the Python version.
    """

    _cache = None  # type: Dict[str, dict]

    def __init__(self, cache_dir=None):
        # type: (Optional[str]) -> None
        if cache_dir is None:
            cache_dir = CACHE_DIR
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        py_version = ".".join(str(digit) for digit in sys.version_info[:2])
        cache_filename = "depcache-py{}.json".format(py_version)

        self._cache_file = os.path.join(cache_dir, cache_filename)

    @property
    def cache(self):
        # type: () -> Dict[str, dict]
        """
        The dictionary that is the actual in-memory cache.  This property
        lazily loads the cache from disk.
        """
        if self._cache is None:
            self.read_cache()
        return self._cache

    def as_cache_key(self, ireq):
        # type: (InstallRequirement) -> Tuple[str, str]
        """
        Given a requirement, return its cache key. This behavior is a little weird
        in order to allow backwards compatibility with cache files. For a requirement
        without extras, this will return, for example:

        ("ipython", "2.1.0")

        For a requirement with extras, the extras will be comma-separated and appended
        to the version, inside brackets, like so:

        ("ipython", "2.1.0[nbconvert,notebook]")
        """
        name, version, extras = as_tuple(ireq)
        if not extras:
            extras_string = ""
        else:
            extras_string = "[{}]".format(",".join(extras))
        return name, "{}{}".format(version, extras_string)

    def read_cache(self):
        # type: () -> None
        """Reads the cached contents into memory."""
        if os.path.exists(self._cache_file):
            self._cache = read_cache_file(self._cache_file)
        else:
            self._cache = {}

    def write_cache(self):
        # type: () -> None
        """Writes the cache to disk as JSON."""
        doc = {"__format__": 1, "dependencies": self._cache}
        with open(self._cache_file, "w") as f:
            json.dump(doc, f, sort_keys=True)

    def clear(self):
        # type: () -> None
        self._cache = {}
        self.write_cache()

    def __contains__(self, ireq):
        # type: (InstallRequirement) -> bool
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return pkgversion_and_extras in self.cache.get(pkgname, {})

    def __getitem__(self, ireq):
        # type: (InstallRequirement) -> List[str]
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return self.cache[pkgname][pkgversion_and_extras]

    def __setitem__(self, ireq, values):
        # type: (InstallRequirement, List[str]) -> None
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        self.cache.setdefault(pkgname, {})
        self.cache[pkgname][pkgversion_and_extras] = values
        self.write_cache()

    def reverse_dependencies(self, ireqs):
        # type: (List[InstallRequirement]) -> Dict[str, Set[str]]
        """
        Returns a lookup table of reverse dependencies for all the given ireqs.

        Since this is all static, it only works if the dependency cache
        contains the complete data, otherwise you end up with a partial view.
        This is typically no problem if you use this function after the entire
        dependency tree is resolved.
        """
        ireqs_as_cache_values = [self.as_cache_key(ireq) for ireq in ireqs]
        return self._reverse_dependencies(ireqs_as_cache_values)

    def _reverse_dependencies(self, cache_keys):
        # type: (List[Tuple[str, str]]) -> Dict[str, Set[str]]
        """
        Returns a lookup table of reverse dependencies for all the given cache keys.

        Example input:

            [('pep8', '1.5.7'),
             ('flake8', '2.4.0'),
             ('mccabe', '0.3'),
             ('pyflakes', '0.8.1')]

        Example output:

            {'pep8': ['flake8'],
             'flake8': [],
             'mccabe': ['flake8'],
             'pyflakes': ['flake8']}

        """
        # First, collect all the dependencies into a sequence of (parent, child)
        # tuples, like [('flake8', 'pep8'), ('flake8', 'mccabe'), ...]
        return lookup_table(
            (key_from_req(Requirement(dep_name)), name)
            for name, version_and_extras in cache_keys
            for dep_name in self.cache[name][version_and_extras]
        )
