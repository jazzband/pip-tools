from __future__ import annotations

import os
import tempfile

import pytest

from piptools._compat.pip_compat import parse_requirements
from piptools.repositories import PyPIRepository

from .constants import PACKAGES_RELATIVE_PATH


@pytest.fixture
def repository():
    with tempfile.TemporaryDirectory() as cache_dir:
        yield PyPIRepository([], cache_dir=cache_dir)


def test_parse_requirements_preserve_editable_relative(repository):
    test_package_path = os.path.join(PACKAGES_RELATIVE_PATH, "small_fake_a")

    with tempfile.NamedTemporaryFile("w") as infile:
        infile.write(f"-e {test_package_path}")
        infile.flush()
        [install_requirement] = parse_requirements(
            infile.name, session=repository.session
        )

    assert install_requirement.link.url == test_package_path
    assert install_requirement.link.file_path == test_package_path
