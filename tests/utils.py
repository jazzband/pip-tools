import os
import subprocess

TEST_DATA_PATH = os.path.join(os.path.split(__file__)[0], "test_data")
MINIMAL_WHEELS_PATH = os.path.join(TEST_DATA_PATH, "minimal_wheels")
PACKAGES_PATH = os.path.join(TEST_DATA_PATH, "packages")


def invoke(command):
    """Invoke sub-process."""
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        status = 0
    except subprocess.CalledProcessError as error:  # pragma: no cover
        output = error.output
        status = error.returncode

    return status, output
