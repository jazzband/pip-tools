from __future__ import annotations

import pytest
from pip._internal.commands import create_command

from piptools._internal import _pip_api


@pytest.mark.skipif(
    _pip_api.PIP_VERSION_MAJOR_MINOR < (26, 0), reason="test requires pip>=26.0"
)
def test_postprocess_cli_options_pre_adds_all_to_release_control_all_releases():
    """
    Test that ``--pre`` gets transformed into ``--all-releases :all:``
    """
    # start with pip's own parsing logic (as applied by the PyPIRepository)
    cmd = create_command("install")
    options, _ = cmd.parse_args(["--pre"])

    # initiall, 'all_releases' is empty
    assert not options.release_control.all_releases

    _pip_api.postprocess_cli_options(options)
    assert ":all:" in options.release_control.all_releases
