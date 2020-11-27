from contextlib import contextmanager
from os import remove
from tempfile import NamedTemporaryFile

import pytest

from piptools.cache import CorruptCacheError, read_cache_file


@contextmanager
def _read_cache_file_helper(to_write):
    """
    On enter, create the file with the given string, and then yield its path.
    On exit, delete that file.

    :param str to_write: the content to write to the file
    :yield: the path to the temporary file
    """
    # Create the file and write to it
    cache_file = NamedTemporaryFile(mode="w", delete=False)
    try:
        cache_file.write(to_write)
        cache_file.close()

        # Yield the path to the file
        yield cache_file.name

    finally:
        # Delete the file on exit
        remove(cache_file.name)


def test_read_cache_file_not_json():
    """
    A cache file that's not JSON should throw a corrupt cache error.
    """
    with _read_cache_file_helper("not json") as cache_file_name:
        with pytest.raises(
            CorruptCacheError,
            match="The dependency cache seems to have been corrupted.",
        ):
            read_cache_file(cache_file_name)


def test_read_cache_file_wrong_format():
    """
    A cache file with a wrong "__format__" value should throw an assertion error.
    """
    with _read_cache_file_helper('{"__format__": 2}') as cache_file_name:
        with pytest.raises(AssertionError):
            read_cache_file(cache_file_name)


def test_read_cache_file_successful():
    """
    A good cache file.
    """
    with _read_cache_file_helper(
        '{"__format__": 1, "dependencies": "success"}'
    ) as cache_file_name:
        assert "success" == read_cache_file(cache_file_name)
