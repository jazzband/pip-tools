from __future__ import annotations

import typing as _t
from pathlib import Path

import pytest
from click.utils import LazyFile
from pytest_mock import MockerFixture

from piptools.pylock.cli._validation import _pylock_suggestion, validate_options


def test_pylock_suggestion_sanitises_uppercase_and_dots() -> None:

    # The earlier ``f"pylock.{stem}.toml"`` produced suggestions that
    # re-tripped PEP 751's regex; the sanitiser collapses disallowed chars
    # and verifies the result before returning.
    # ``Path.stem`` strips the trailing ``.toml`` once, so inner dots
    # survive into the slug; ``[^a-z0-9_-]+`` collapses them to ``-`` and a
    # leading ``pylock-`` is stripped so the suggestion is not doubled.
    assert _pylock_suggestion(Path("pylock.dev.extra.toml")) == "pylock.dev-extra.toml"
    # ``PYLOCK.toml``'s stem reduces to ``pylock`` after lower-casing, so
    # the valid suggestion is bare ``pylock.toml``; the slug is dropped to
    # avoid a redundant ``pylock.pylock.toml`` hint.
    assert _pylock_suggestion(Path("PYLOCK.toml")) == "pylock.toml"
    # If nothing salvageable remains the suggestion falls back to bare
    # ``pylock.toml`` instead of producing another invalid hint.
    assert _pylock_suggestion(Path("...toml")) == "pylock.toml"


@pytest.mark.parametrize(
    "output_file_name",
    (
        pytest.param("-", id="stdout-dash"),
        pytest.param("<stdout>", id="stdout-marker"),
    ),
)
def test_validate_options_accepts_stream_output_names(
    mocker: MockerFixture, output_file_name: str
) -> None:
    # ``-`` and ``<stdout>`` are not on-disk paths so PEP 751's filename
    # regex must not gate them; the streaming pipeline depends on it.
    output_file = mocker.MagicMock(spec=LazyFile, name=output_file_name)
    output_file.name = output_file_name
    validate_options(
        all_build_deps=False,
        build_deps_targets=(),
        only_build_deps=False,
        extras=(),
        all_extras=False,
        src_files=("requirements.in",),
        output_file=output_file,
    )


def test_validate_options_skips_name_check_for_attrless_output(
    mocker: MockerFixture,
) -> None:
    # A bare ``BinaryIO`` carries no ``.name``; falling through keeps
    # streaming consumers unblocked by the path-shape rule.
    output_file = mocker.MagicMock(spec=[])
    validate_options(
        all_build_deps=False,
        build_deps_targets=(),
        only_build_deps=False,
        extras=(),
        all_extras=False,
        src_files=("requirements.in",),
        output_file=_t.cast("_t.IO[_t.Any]", output_file),
    )
