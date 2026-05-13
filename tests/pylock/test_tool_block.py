from __future__ import annotations

from datetime import datetime, timezone

import pytest

from piptools.pylock._inputs import (
    LockSelection,
    LockTargets,
    ResolverOptions,
    ToolMetadataOptions,
)
from piptools.pylock.tool_block import (
    PylockToolMetadata,
    _default_generated_at,
    build,
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


@pytest.fixture(name="metadata_inputs")
def metadata_inputs_fixture() -> (
    tuple[LockSelection, LockTargets, ResolverOptions, ToolMetadataOptions]
):
    return (
        LockSelection(extras=(), all_extras=False, groups=(), all_groups=False),
        LockTargets(
            target_envs={}, platforms=(), python_versions=(), no_universal=False
        ),
        ResolverOptions(
            prereleases=False,
            rebuild=False,
            allow_unsafe=False,
            unsafe_packages=frozenset(),
            max_rounds=10,
            cache_dir="",
            pre=False,
        ),
        ToolMetadataOptions(no_metadata=False, skip_metadata_fields=()),
    )


def test_build_honours_source_date_epoch(
    monkeypatch: pytest.MonkeyPatch,
    metadata_inputs: tuple[
        LockSelection, LockTargets, ResolverOptions, ToolMetadataOptions
    ],
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    selection, targets, options, metadata = metadata_inputs
    meta = build(
        selection=selection, targets=targets, options=options, metadata=metadata
    )
    assert meta is not None
    assert meta.generated_at is not None
    assert meta.generated_at.isoformat() == "2023-11-14T22:13:20+00:00"


def test_build_falls_back_to_wall_clock(
    monkeypatch: pytest.MonkeyPatch,
    metadata_inputs: tuple[
        LockSelection, LockTargets, ResolverOptions, ToolMetadataOptions
    ],
) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    selection, targets, options, metadata = metadata_inputs
    before = datetime.now(tz=timezone.utc)
    meta = build(
        selection=selection, targets=targets, options=options, metadata=metadata
    )
    after = datetime.now(tz=timezone.utc)
    assert meta is not None
    assert meta.generated_at is not None
    assert before <= meta.generated_at <= after
