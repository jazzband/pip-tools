import os
import subprocess
import sys


def test_remove_legacy_cache_dir():
    """
    Check that legacy cache dir is removed at import time.
    """
    os.mkdir(os.path.expanduser("~/.pip-tools"))

    result = subprocess.run(
        [sys.executable, "-m", "piptools"], stdout=subprocess.PIPE, check=True
    )

    assert result.stdout.startswith(b"Removing old cache dir")
