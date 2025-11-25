from __future__ import annotations

import pytest

from piptools._pip_api import (
    PIP_VERSION,
    copy_install_requirement,
    create_install_requirement_from_line,
)


@pytest.mark.skipif(PIP_VERSION[:2] < (25, 3), reason="test requires pip>=25.3")
@pytest.mark.parametrize("use_pep517", (True, False))
def test_copy_install_requirement_removes_pip_25_3_unsupported_opts(use_pep517):
    req = create_install_requirement_from_line("foolib==0.1")

    updated_req = copy_install_requirement(req, use_pep517=use_pep517)
    assert not hasattr(updated_req, "use_pep517")


@pytest.mark.skipif(PIP_VERSION[:2] >= (25, 3), reason="test requires pip<25.3")
@pytest.mark.parametrize("use_pep517", (True, False))
def test_copy_install_requirement_preserves_pip_25_3_unsupported_opts(use_pep517):
    req = create_install_requirement_from_line("foolib==0.1")

    updated_req = copy_install_requirement(req, use_pep517=use_pep517)
    assert hasattr(updated_req, "use_pep517")
    assert updated_req.use_pep517 == use_pep517
