from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from piptools._internal import _pip_api
from piptools._internal._pip_api import pip_version


@pytest.mark.skipif(
    _pip_api.PIP_VERSION_MAJOR_MINOR < (25, 3), reason="test requires pip>=25.3"
)
@pytest.mark.parametrize(
    "use_pep517",
    (pytest.param(True, id="pep517"), pytest.param(False, id="no-pep517")),
)
def test_copy_install_requirement_removes_pip_25_3_unsupported_opts(
    use_pep517: bool,
) -> None:
    req = _pip_api.create_install_requirement_from_line("foolib==0.1")
    updated_req = _pip_api.copy_install_requirement(req, use_pep517=use_pep517)
    assert not hasattr(updated_req, "use_pep517")


@pytest.mark.parametrize(
    "use_pep517",
    (pytest.param(True, id="pep517"), pytest.param(False, id="no-pep517")),
)
def test_copy_install_requirement_preserves_pre_25_3_opts(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, use_pep517: bool
) -> None:
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (25, 0))
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (25, 0))
    template = mocker.MagicMock()
    template.install_options = []
    template.global_options = []
    template.use_pep517 = use_pep517
    template.original_link = None
    fake = mocker.patch(
        "piptools._internal._pip_api.install_requirements.InstallRequirement",
        autospec=False,
    )
    _pip_api.copy_install_requirement(template)
    assert fake.call_args.kwargs["use_pep517"] is use_pep517
