from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from piptools._internal import _pip_api
from piptools._internal._pip_api import pip_version

from .conftest import (
    _install_req_from_line_compat,
    _make_cli_runner,
    pytest_collection_modifyitems,
)


@pytest.mark.parametrize(
    ("ci", "has_network", "expected_called"),
    (
        pytest.param(True, True, True, id="ci-network"),
        pytest.param(True, False, False, id="ci-no-network"),
        pytest.param(False, True, False, id="local-network"),
    ),
)
def test_pytest_collection_modifyitems_flaky_marker(
    mocker: MockerFixture,
    ci: bool,
    has_network: bool,
    expected_called: bool,
) -> None:
    item = mocker.MagicMock(name="collected_item")
    item.get_closest_marker.return_value = object() if has_network else None
    mocker.patch("tests.conftest.looks_like_ci", return_value=ci)

    pytest_collection_modifyitems(
        config=mocker.MagicMock(name="pytest_config"), items=[item]
    )

    assert item.add_marker.called is expected_called


def test_install_req_from_line_compat_rewrites_kwargs_for_old_pip(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (23, 0))
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (23, 0))
    fake = mocker.patch("tests.conftest.install_req_from_line")
    _install_req_from_line_compat("pkg==1.0", hash_options={"sha256": ["abc"]})
    assert fake.call_args.kwargs["options"] == {"hashes": {"sha256": ["abc"]}}


def test_install_req_from_line_compat_passes_kwargs_through_on_modern_pip(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (23, 1))
    monkeypatch.setattr(pip_version, "PIP_VERSION_MAJOR_MINOR", (23, 1))
    fake = mocker.patch("tests.conftest.install_req_from_line")
    _install_req_from_line_compat("pkg==1.0", hash_options={"sha256": ["abc"]})
    assert fake.call_args.kwargs["hash_options"] == {"sha256": ["abc"]}


@pytest.mark.parametrize(
    ("click_version", "expected_kwargs"),
    (
        pytest.param("8.1.0", {"mix_stderr": False}, id="click<8.2"),
        pytest.param("8.2.0", {}, id="click>=8.2"),
    ),
)
def test_make_cli_runner_branches_on_click_version(
    mocker: MockerFixture,
    click_version: str,
    expected_kwargs: dict[str, object],
) -> None:
    mocker.patch("tests.conftest.version_of", return_value=click_version)
    fake = mocker.patch("tests.conftest.CliRunner", autospec=False)
    _make_cli_runner()
    assert fake.call_args.kwargs == expected_kwargs
