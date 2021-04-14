from setuptools import setup
import os

setup(
    name="fake with local files as dependencies",
    version=0.1,
    install_requires=[
        'fake_package_a @ file://localhost/{}/tests/test_data/non_linked_wheel_file/fake_package_a-0.1-py2.py3-none-any.whl'.format(os.getcwd())
        ],
)


