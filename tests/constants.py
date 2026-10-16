from __future__ import annotations

import pathlib

TEST_DATA_PATH = pathlib.Path(__file__).parent / "test_data"
MINIMAL_WHEELS_PATH = TEST_DATA_PATH / "minimal_wheels"
PACKAGES_PATH = TEST_DATA_PATH / "packages"
PACKAGES_RELATIVE_PATH = PACKAGES_PATH.relative_to(pathlib.Path.cwd())
