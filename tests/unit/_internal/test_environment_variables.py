from __future__ import annotations

import os
from unittest import mock

import pytest

from piptools._internal import _environment_variables


def test_setenv_context_does_simple_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPAM_VAR", "1")
    with _environment_variables.setenv_context("SPAM_VAR", "spam"):
        assert os.environ["SPAM_VAR"] == "spam"
    assert os.environ["SPAM_VAR"] == "1"


@pytest.mark.parametrize("value_was_previously_set", (True, False))
@pytest.mark.parametrize("successfully_sets_value", (True, False))
def test_setenv_context_does_reset_even_if_setitem_raises(
    monkeypatch: pytest.MonkeyPatch,
    value_was_previously_set: bool,
    successfully_sets_value: bool,
) -> None:
    if value_was_previously_set:
        monkeypatch.setenv("SPAM_VAR", "1")
    else:
        monkeypatch.delenv("SPAM_VAR", raising=False)

    # we will inject an error on `__setitem__` to simulate an interruption *right after*
    # the setitem succeeds
    original_setitem = os.environ.__setitem__

    def setitem_and_raise(self, key, value):
        if successfully_sets_value:
            original_setitem(key, value)
        raise KeyboardInterrupt("injected interrupt")

    with mock.patch.object(os.environ.__class__, "__setitem__", setitem_and_raise):
        # PT012 flags any use of pytest.raises() which contains more than a single
        # simple statement. This is not appropriate to testing the behavior of a context
        # manager with an error injected into the middle of execution, so it is ignored.
        with pytest.raises(  # noqa: PT012
            KeyboardInterrupt,
            match="injected interrupt",
        ):
            with _environment_variables.setenv_context("SPAM_VAR", "spam"):
                pytest.fail(
                    "unreachable statement inside of context manager was reached"
                )

        if value_was_previously_set:
            assert os.environ["SPAM_VAR"] == "1"
        else:
            assert "SPAM_VAR" not in os.environ
