from __future__ import annotations

from datetime import datetime, timezone

import pytest

from piptools.pylock.tool_block import (
    PylockToolMetadata,
    _default_generated_at,
    to_dict,
)


def test_tool_metadata_to_dict_omits_empty_version() -> None:
    # ``--skip-metadata-field version`` blanks ``meta.version`` to ``""``;
    # writing the empty string would emit a malformed metadata field rather
    # than dropping it.
    meta = PylockToolMetadata(
        version="",
        pip_version="1.2.3",
        command=["pip-lock"],
        generated_at=None,
        options=None,
    )
    result = to_dict(meta)
    assert "version" not in result
    assert result["pip-version"] == "1.2.3"


def test_tool_metadata_to_dict_handles_no_options() -> None:
    # ``PylockToolMetadata`` keeps ``options`` typed as ``Optional`` so a
    # caller that built metadata by hand (rather than via the public CLI
    # path) can pass ``None`` and still produce a valid lockfile dict.
    meta = PylockToolMetadata(
        version="1.0",
        pip_version="",
        command=[],
        generated_at=None,
        options=None,
    )
    result = to_dict(meta)
    assert result == {"version": "1.0"}


def test_default_generated_at_uses_wall_clock_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    before = datetime.now(tz=timezone.utc)
    result = _default_generated_at()
    after = datetime.now(tz=timezone.utc)
    assert before <= result <= after


@pytest.mark.parametrize(
    ("epoch", "expected_isoformat"),
    (
        pytest.param("0", "1970-01-01T00:00:00+00:00", id="unix-epoch"),
        pytest.param(
            "1700000000", "2023-11-14T22:13:20+00:00", id="reproducible-build"
        ),
    ),
)
def test_default_generated_at_honours_source_date_epoch(
    monkeypatch: pytest.MonkeyPatch, epoch: str, expected_isoformat: str
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", epoch)
    assert _default_generated_at().isoformat() == expected_isoformat


def test_default_generated_at_falls_back_when_env_value_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "not-an-int")
    before = datetime.now(tz=timezone.utc)
    result = _default_generated_at()
    after = datetime.now(tz=timezone.utc)
    assert before <= result <= after
