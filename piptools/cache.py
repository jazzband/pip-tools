# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json
import os
import sys

from pkg_resources import Requirement

from .exceptions import PipToolsError
from .locations import CACHE_DIR
from .utils import lookup_table


class CorruptCacheError(PipToolsError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        lines = [
            'The dependency cache seems to have been corrupted.',
            'Inspect, or delete, the following file:',
            '  {}'.format(self.path),
        ]
        return os.linesep.join(lines)


class DependencyCache(object):
    """
    Creates a new persistent dependency cache for the current Python version.
    The cache file is written to the appropriate user cache dir for the
    current platform, i.e.

        ~/.cache/pip-tools/depcache-pyX.Y.json

    Where X.Y indicates the Python version.
    """
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = CACHE_DIR
        py_version = '.'.join(str(digit) for digit in sys.version_info[:2])
        cache_filename = 'depcache-py{}.json'.format(py_version)

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

    def read_cache(self):
        """Reads the cached contents into memory."""
        if os.path.exists(self._cache_file):
            with open(self._cache_file, 'r') as f:
                try:
                    doc = json.load(f)
                except ValueError:
                    raise CorruptCacheError(self._cache_file)

            # Check version and load the contents
            assert doc['__format__'] == 1, 'Unknown cache file format'
            self._cache = doc['dependencies']
        else:
            self._cache = {}

    def write_cache(self):
        """Writes (pickles) the cache to disk."""
        doc = {
            '__format__': 1,
            'dependencies': self._cache,
        }
        with open(self._cache_file, 'w') as f:
            json.dump(doc, f, sort_keys=True)

    def clear(self):
        self._cache = {}
        self.write_cache()

    def __contains__(self, tup):
        pkgname, pkgversion = tup
        return pkgversion in self.cache.get(pkgname, {})

    def __getitem__(self, tup):
        pkgname, pkgversion = tup
        return self.cache[pkgname][pkgversion]

    def __setitem__(self, tup, values):
        pkgname, pkgversion = tup
        self.cache.setdefault(pkgname, {})
        self.cache[pkgname][pkgversion] = values
        self.write_cache()

    def get(self, tup, default=None):
        pkgname, pkgversion = tup
        return self.cache.get(pkgname, {}).get(pkgversion, default)

    def reverse_dependencies(self, tups):
        """
        Returns a lookup table of reverse dependencies for all the given
        (name, version) tuples.

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

        Since this is all static, it only works if the dependency cache
        contains the complete data, otherwise you end up with a partial view.
        This is typically no problem if you use this function after the entire
        dependency tree is resolved.
        """
        # First, collect all the dependencies into a sequence of (parent,
        # child) tuples, like [('flake8', 'pep8'), ('flake8', 'mccabe'), ...]
        return lookup_table((Requirement.parse(dep_name).key, name)
                            for name, version in tups
                            for dep_name in self[(name, version)])
