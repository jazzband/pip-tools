from __future__ import annotations

import pytest

from piptools.pylock.redact import redact_command


@pytest.mark.parametrize(
    ("argv", "expected"),
    (
        pytest.param(
            ["pip-lock", "-i", "https://pypi.org/simple/"],
            ["pip-lock", "-i", "https://pypi.org/simple/"],
            id="no-secret-passthrough",
        ),
        pytest.param(
            ["pip-lock", "--index-url", "https://user:token@example.com/simple/"],
            ["pip-lock", "--index-url", "https://user:****@example.com/simple/"],
            id="basic-auth-redacted",
        ),
        pytest.param(
            ["pip-lock", "--cert", "/secret/path.pem"],
            ["pip-lock", "--cert", "<REDACTED>"],
            id="cert-path-replaced",
        ),
        pytest.param(
            ["pip-lock", "--client-cert", "/secret/key.pem"],
            ["pip-lock", "--client-cert", "<REDACTED>"],
            id="client-cert-path-replaced",
        ),
        pytest.param(
            ["pip-lock", "--config-settings", "build-arg=secret-token"],
            ["pip-lock", "--config-settings", "build-arg=<REDACTED>"],
            id="config-settings-key-preserved",
        ),
        pytest.param(
            ["pip-lock", "-C", "compile-flag=-Dval=secret"],
            ["pip-lock", "-C", "compile-flag=<REDACTED>"],
            id="config-settings-short-form",
        ),
        pytest.param(
            ["pip-lock", "--proxy", "http://user:pw@proxy/"],
            ["pip-lock", "--proxy", "<REDACTED>"],
            id="proxy-value-replaced-wholesale",
        ),
        pytest.param(
            ["pip-lock", "--keyring-provider", "subprocess"],
            ["pip-lock", "--keyring-provider", "subprocess"],
            id="keyring-provider-survives-roundtrip",
        ),
    ),
)
def test_redact_command(argv: list[str], expected: list[str]) -> None:
    assert redact_command(argv) == expected


def test_redact_command_replaces_control_chars() -> None:
    # tomli_w accepts all printable Unicode but a NUL or BEL would either
    # corrupt the lockfile or trip the writer's validator. Replace with
    # U+FFFD so the field still round-trips as a readable diagnostic.
    argv = ["pip-lock", "/path\x00with-nul", "/path\x07with-bel"]
    assert redact_command(argv) == ["pip-lock", "/path�with-nul", "/path�with-bel"]


def test_redact_command_preserves_tab_and_newline() -> None:
    # Tab and newline are valid TOML basic-string escapes; replacing them
    # would mangle pip-tools args that legitimately carry them (e.g. a
    # ``--config-settings`` that wraps a multi-line CMake script).
    argv = ["pip-lock", "first\tsecond", "line\nwrap"]
    assert redact_command(argv) == argv
