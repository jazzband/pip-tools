from __future__ import annotations

from setuptools import setup

setup(
    name="small_fake_with_build_deps",
    version=0.1,
    install_requires=[
        "fake_direct_runtime_dep",
    ],
    extras_require={
        "x": ["fake_direct_extra_runtime_dep"],
    },
)
