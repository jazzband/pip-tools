from __future__ import annotations

import os
import typing as _t

import pytest

from piptools._internal import _environment_variables


def test_setenv_context_does_simple_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPAM_VAR", "1")
    with _environment_variables.setenv_context("SPAM_VAR", "spam"):
        assert os.environ["SPAM_VAR"] == "spam"
    assert os.environ["SPAM_VAR"] == "1"


@pytest.mark.parametrize(
    ("value_was_previously_set", "unset_in_block"),
    (
        pytest.param(True, False, id="was_set"),
        pytest.param(True, True, id="was_set_and_got_unset"),
        pytest.param(False, False, id="was_not_set"),
        pytest.param(False, True, id="was_not_set_and_got_unset"),
    ),
)
def test_setenv_context_does_reset_even_if_inner_block_raises(
    monkeypatch: pytest.MonkeyPatch,
    value_was_previously_set: bool,
    unset_in_block: bool,
) -> None:
    if value_was_previously_set:
        monkeypatch.setenv("SPAM_VAR", "1")
    else:
        monkeypatch.delenv("SPAM_VAR", raising=False)

    @_environment_variables.setenv_context("SPAM_VAR", "spam")
    def _ctrl_c() -> _t.NoReturn:
        if unset_in_block:
            del os.environ["SPAM_VAR"]
        raise KeyboardInterrupt("interrupt")

    with pytest.raises(KeyboardInterrupt, match="^interrupt$"):
        _ctrl_c()

    if value_was_previously_set:
        assert os.environ["SPAM_VAR"] == "1"
    else:
        assert "SPAM_VAR" not in os.environ
