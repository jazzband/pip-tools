from setuptools import find_packages, setup

setup(
    name='small_fake_with_deps',
    version=0.1,
    install_requires=[
        "six==1.10.0",
    ],
    packages=find_packages(),
)
