import os

import pytest

from piptools._compat import makedirs


def test_makedirs_exist_ok_true(tmpdir):
    path = str(tmpdir / "test")
    makedirs(path, exist_ok=True)
    assert os.path.isdir(path)
    makedirs(path, exist_ok=True)
    assert os.path.isdir(path)


def test_makedirs_exist_ok_false(tmpdir):
    path = str(tmpdir / "test")
    makedirs(path)
    assert os.path.isdir(path)
    with pytest.raises(OSError, match="exists"):
        makedirs(path)
