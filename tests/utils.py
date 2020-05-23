import os
import subprocess


def invoke(command):
    """Invoke sub-process."""
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        status = 0
    except subprocess.CalledProcessError as error:  # pragma: no cover
        output = error.output
        status = error.returncode

    return status, output


# NOTE: keep in sync with "passenv" in tox.ini
CI_VARIABLES = {"CI", "GITHUB_ACTIONS"}


def looks_like_ci():
    return bool(set(os.environ.keys()) & CI_VARIABLES)
