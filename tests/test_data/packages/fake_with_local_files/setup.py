import os

from setuptools import setup

from .constants import NON_LINKED_PACKAGES_PATH

setup(
    name="fake with local files as dependencies",
    version=0.1,
    install_requires=[
        "fake_package_a @ file://localhost/{}/fake_package_a-0.1-py2.py3-none-any.whl".format(
            os.path.join(NON_LINKED_PACKAGES_PATH)
        )
    ],
)
