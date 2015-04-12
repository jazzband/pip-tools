import os
import pickle


class PersistentCache(object):
    def __init__(self, cache_file):
        """Creates a new persistent cache, retrieving/storing cached key-value
        pairs from/to the given filename.
        """
        self._cache_file = cache_file
        self._cache = None

    @property
    def cache(self):
        """The dictionary that is the actual in-memory cache.  This property
        lazily loads the cache from disk.
        """
        if self._cache is None:
            self.read_cache()
        return self._cache

    def read_cache(self):
        """Reads the cached contents into memory."""
        if os.path.exists(self._cache_file):
            with open(self._cache_file, 'rb') as f:
                self._cache = pickle.load(f)
        else:
            # Create a new, empty cache otherwise (store a __format__ field
            # that can be used to version the file, should we need to make
            # changes to its internals)
            self._cache = {'__format__': 1}

    def write_cache(self):
        """Writes (pickles) the cache to disk.

        It uses pickle protocol 2 to be compatible with Python 2.
        """
        with open(self._cache_file, 'wb') as f:
            pickle.dump(self._cache, f, protocol=2)

    def __contains__(self, item):
        return item in self.cache

    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.write_cache()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
