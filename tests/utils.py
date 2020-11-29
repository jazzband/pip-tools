import os

# NOTE: keep in sync with "passenv" in tox.ini
CI_VARIABLES = {"CI", "GITHUB_ACTIONS"}


def looks_like_ci():
    return bool(set(os.environ.keys()) & CI_VARIABLES)
