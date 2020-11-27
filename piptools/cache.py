# coding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import platform
import sys

from .exceptions import PipToolsError
from .utils import as_tuple

_PEP425_PY_TAGS = {"cpython": "cp", "pypy": "pp", "ironpython": "ip", "jython": "jy"}


def _implementation_name():
    """similar to PEP 425, however the minor version is separated from the
    major to differentation "3.10" and "31.0".
    """
    implementation_name = platform.python_implementation().lower()
    implementation = _PEP425_PY_TAGS.get(implementation_name, "??")
    return "{}{}.{}".format(implementation, *sys.version_info)


class CorruptCacheError(PipToolsError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        lines = [
            "The dependency cache seems to have been corrupted.",
            "Inspect, or delete, the following file:",
            "  {}".format(self.path),
        ]
        return os.linesep.join(lines)


def read_cache_file(cache_file_path):
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

    Where py indicates the Python implementation.
    Where X.Y indicates the Python version.
    """

    def __init__(self, cache_dir):
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        cache_filename = "depcache-{}.json".format(_implementation_name())

        self._cache_file = os.path.join(cache_dir, cache_filename)
        self._cache = None

    @property
    def cache(self):
        """
        The dictionary that is the actual in-memory cache.  This property
        lazily loads the cache from disk.
        """
        if self._cache is None:
            self.read_cache()
        return self._cache

    def as_cache_key(self, ireq):
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
        """Reads the cached contents into memory."""
        if os.path.exists(self._cache_file):
            self._cache = read_cache_file(self._cache_file)
        else:
            self._cache = {}

    def write_cache(self):
        """Writes the cache to disk as JSON."""
        doc = {"__format__": 1, "dependencies": self._cache}
        with open(self._cache_file, "w") as f:
            json.dump(doc, f, sort_keys=True)

    def clear(self):
        self._cache = {}
        self.write_cache()

    def __contains__(self, ireq):
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return pkgversion_and_extras in self.cache.get(pkgname, {})

    def __getitem__(self, ireq):
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return self.cache[pkgname][pkgversion_and_extras]

    def __setitem__(self, ireq, values):
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        self.cache.setdefault(pkgname, {})
        self.cache[pkgname][pkgversion_and_extras] = values
        self.write_cache()
