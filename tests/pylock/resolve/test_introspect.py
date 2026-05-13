from __future__ import annotations

import typing as _t
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from pytest_mock import MockerFixture

from piptools.pylock.resolve._introspect import (
    extract_dep_markers,
    get_forward_dependencies,
)


@dataclass
class FakeCandidate:
    name: str
    _is_real: bool = True

    def get_install_requirement(self) -> str | None:
        return self.name if self._is_real else None


@dataclass
class FakeGraph:
    _children: dict[str | None, list[str | None]] = field(default_factory=dict)

    def iter_children(self, name: str | None) -> Iterator[str | None]:
        return iter(self._children.get(name, []))


@dataclass
class FakeResult:
    mapping: dict[str, FakeCandidate] = field(default_factory=dict)
    graph: FakeGraph = field(default_factory=FakeGraph)


@pytest.fixture(name="fake_result")
def _fake_result() -> FakeResult:
    real_names = ("flask", "click", "jinja2", "werkzeug", "colorama", "markupsafe")
    mapping: dict[str, FakeCandidate] = {
        name: FakeCandidate(name=name) for name in real_names
    }
    mapping["<Python from Requires-Python>"] = FakeCandidate(
        name="<Python from Requires-Python>", _is_real=False
    )
    return FakeResult(
        mapping=mapping,
        graph=FakeGraph(
            _children={
                None: ["flask", "click"],
                "flask": [None, "click", "jinja2", "werkzeug"],
                "click": ["colorama", "<Python from Requires-Python>"],
                "jinja2": ["markupsafe"],
                "werkzeug": ["markupsafe"],
                "colorama": ["<Python from Requires-Python>"],
                "markupsafe": [],
                "<Python from Requires-Python>": [],
            }
        ),
    )


def test_get_forward_dependencies(fake_result: FakeResult) -> None:
    deps = get_forward_dependencies(_t.cast("_t.Any", fake_result))
    assert deps["flask"] == {"click", "jinja2", "werkzeug"}
    assert deps["click"] == {"colorama"}
    assert deps["jinja2"] == {"markupsafe"}
    assert deps["colorama"] == set()


def test_get_forward_dependencies_skips_root(fake_result: FakeResult) -> None:
    deps = get_forward_dependencies(_t.cast("_t.Any", fake_result))
    assert None not in deps


def test_extract_dep_markers_returns_empty_when_no_result(
    mocker: MockerFixture,
) -> None:
    scan_resolver = mocker.MagicMock(name="scan_resolver", _resolver_result=None)
    assert extract_dep_markers(scan_resolver) == set()


def test_extract_dep_markers_collects_env_referencing_markers(
    mocker: MockerFixture,
) -> None:
    info = mocker.MagicMock(name="info")
    info.requirement._ireq.req.marker = mocker.MagicMock(
        __str__=lambda _self: "sys_platform == 'linux'"
    )
    criterion = mocker.MagicMock(name="criterion", information=[info])
    result = mocker.MagicMock(name="result", criteria={"pkg": criterion})
    scan_resolver = mocker.MagicMock(name="scan_resolver", _resolver_result=result)

    markers = extract_dep_markers(scan_resolver)

    assert markers == {"sys_platform == 'linux'"}


def test_extract_dep_markers_drops_non_env_markers(mocker: MockerFixture) -> None:
    info = mocker.MagicMock(name="info")
    info.requirement._ireq.req.marker = mocker.MagicMock(
        __str__=lambda _self: "extra == 'dev'"
    )
    criterion = mocker.MagicMock(name="criterion", information=[info])
    result = mocker.MagicMock(name="result", criteria={"pkg": criterion})
    scan_resolver = mocker.MagicMock(name="scan_resolver", _resolver_result=result)

    assert extract_dep_markers(scan_resolver) == set()


def test_extract_dep_markers_logs_when_introspection_returns_no_markers(
    mocker: MockerFixture,
) -> None:
    info = mocker.MagicMock(name="info", requirement=mocker.MagicMock(_ireq=None))
    criterion = mocker.MagicMock(name="criterion", information=[info])
    result = mocker.MagicMock(name="result", criteria={"pkg": criterion})
    scan_resolver = mocker.MagicMock(name="scan_resolver", _resolver_result=result)
    log_info = mocker.patch("piptools.pylock.resolve._introspect.log.info")

    markers = extract_dep_markers(scan_resolver)

    assert markers == set()
    log_info.assert_called_once()
    assert "extracted zero markers" in log_info.call_args.args[0]
