from __future__ import annotations

import pathlib
import typing as _t
from unittest import mock

import pytest
from pip._internal.req import InstallRequirement

from piptools.repositories.pypi import PyPIRepository, _get_true_base_from_index_url
from tests.constants import PACKAGES_PATH


@pytest.mark.parametrize(
    ("url", "expect_result"),
    (
        pytest.param(
            "https://pypi.org/", "https://pypi.org/", id="pypi-base-unchanged"
        ),
        pytest.param(
            "https://test.pypi.org/",
            "https://test.pypi.org/",
            id="test-pypi-base-unchanged",
        ),
        pytest.param(
            "https://my-pypi-mirror.example.org/",
            "https://my-pypi-mirror.example.org/",
            id="mirror-root-unchanged",
        ),
        pytest.param(
            "https://pypi.org/simple", "https://pypi.org/", id="pypi-simple-stripped"
        ),
        pytest.param(
            "https://pypi.org/simple/",
            "https://pypi.org/",
            id="pypi-simple-trailing-slash-stripped",
        ),
        # custom index gets the same treatment
        pytest.param(
            "https://my-pypi-mirror.example.org/simple",
            "https://my-pypi-mirror.example.org/",
            id="mirror-simple-stripped",
        ),
        # an extreme case: pypi.org is being presented via some proxy,
        # which we want to preserve, *and* simple is used repeatedly in the URL
        # -- we only strip one copy of "simple", as this provides an escape hatch
        # for anyone with a particularly weird proxy setup
        pytest.param(
            "https://pypi.org/my-proxy/simple/simple",
            "https://pypi.org/my-proxy/simple/",
            id="proxy-double-simple-strips-only-one",
        ),
    ),
)
def test_true_base_url_strips_simple_suffix(url: str, expect_result: str) -> None:
    assert _get_true_base_from_index_url(url) == expect_result


@pytest.mark.parametrize(
    "requirement_string",
    (
        pytest.param("django", id="unbound"),
        pytest.param("django > 1", id="lower-bound"),
    ),
)
def test_get_dependencies_helper_rejects_unpinned_reqs(
    pypi_repository: PyPIRepository,
    from_line: _t.Callable[[str], InstallRequirement],
    requirement_string: str,
) -> None:
    ireq = from_line(requirement_string)
    with pytest.raises(
        TypeError, match="Expected url, pinned or editable InstallRequirement"
    ):
        pypi_repository.get_dependencies(ireq)


def test_find_best_match_short_circuits_on_editables(
    pypi_repository: PyPIRepository,
    from_editable: _t.Callable[[str], InstallRequirement],
) -> None:
    package_path = pathlib.Path(PACKAGES_PATH) / "small_fake_a"
    ireq = from_editable(str(package_path))
    with mock.patch.object(
        pypi_repository,
        "find_all_candidates",
        wraps=pypi_repository.find_all_candidates,
    ) as mock_find_all_candidates:
        assert pypi_repository.find_best_match(ireq) is ireq

        mock_find_all_candidates.assert_not_called()
