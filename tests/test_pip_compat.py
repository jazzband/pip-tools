from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath

import pytest

from piptools._compat.pip_compat import parse_requirements
from piptools.repositories import PyPIRepository

from .constants import PACKAGES_RELATIVE_PATH


def test_parse_requirements_preserve_editable_relative_path(tmp_path, repository):
    test_package_path = str(
        PurePosixPath(Path(PACKAGES_RELATIVE_PATH)) / "small_fake_a"
    )
    requirements_in_path = str(tmp_path / "requirements.in")

    with open(requirements_in_path, "w") as requirements_in_file:
        requirements_in_file.write(f"-e {test_package_path}")

    [install_requirement] = parse_requirements(
        requirements_in_path, session=repository.session
    )

    assert install_requirement.link.url == test_package_path
    assert install_requirement.link.file_path == test_package_path
