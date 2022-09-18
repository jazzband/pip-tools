from __future__ import annotations

# A dependency of the build backend that is not installed is equivalent to a build
# backend that is not installed so we don't have to test both cases.
import fake_static_build_dep  # noqa: F401
import setuptools.build_meta

# Re-export all names in case more hooks are added in the future
from setuptools.build_meta import *  # noqa: F401, F403

build_wheel = setuptools.build_meta.build_wheel
build_sdist = setuptools.build_meta.build_sdist


def get_requires_for_build_sdist(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_sdist(config_settings)
    assert result == []
    result.append("fake_dynamic_build_dep_for_all")
    result.append("fake_dynamic_build_dep_for_sdist")
    return result


def get_requires_for_build_wheel(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_wheel(config_settings)
    assert result == ["wheel"]
    result.append("fake_dynamic_build_dep_for_all")
    result.append("fake_dynamic_build_dep_for_wheel")
    return result


def get_requires_for_build_editable(config_settings=None):
    return ["fake_dynamic_build_dep_for_all", "fake_dynamic_build_dep_for_editable"]
