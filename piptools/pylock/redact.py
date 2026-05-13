"""Redact secrets from the ``[tool.pip-tools].command`` field.

The lockfile records the command line that produced it so reviewers can reproduce the resolution.
Argv strings often carry credentials (URLs with embedded basic-auth, paths to client
certificates), so this module rewrites the captured argv before serialization.
"""

from __future__ import annotations

import typing as _t
from re import Pattern
from re import compile as re_compile

from pip._internal.utils.misc import redact_auth_from_url

# Options whose argument is sensitive; redaction replaces the value wholesale.
_REDACTED_PATH_OPTIONS: _t.Final[frozenset[str]] = frozenset(
    {
        "--cert",
        "--client-cert",
        "--proxy",
        "--config-settings",
        "-C",
    }
)
# Tab and newline are valid TOML basic-string escapes; the rest of the C0/C1 control range either
# fails ``tomli_w`` outright or produces a lockfile that no downstream parser accepts. Replace
# with U+FFFD so the field round-trips as a readable diagnostic.
_CONTROL_CHARS: _t.Final[Pattern[str]] = re_compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def redact_command(argv: _t.Sequence[str]) -> list[str]:
    """Strip credentials and unprintable characters from a recorded argv.

    URL-bearing values pass through pip's auth redactor. Path arguments to known
    credential-related options are replaced wholesale. For PEP 517 build-hook flags the redactor
    keeps the key and masks the value so the lockfile documents which knobs were tuned.

    :param argv: The recorded command line tokens to clean.
    :returns: A new list of tokens safe to commit alongside the lockfile.
    """
    cleaned: list[str] = []
    skip_next: str | None = None
    for arg in argv:
        if skip_next is not None:
            if skip_next in {"--config-settings", "-C"} and "=" in arg:
                key, _, _ = arg.partition("=")
                cleaned.append(f"{key}=<REDACTED>")
            else:
                cleaned.append("<REDACTED>")
            skip_next = None
            continue
        if arg in _REDACTED_PATH_OPTIONS:
            cleaned.append(arg)
            skip_next = arg
            continue
        if "://" in arg:
            cleaned.append(redact_auth_from_url(arg))
            continue
        cleaned.append(arg)
    return [_CONTROL_CHARS.sub("�", arg) for arg in cleaned]


__all__ = [
    "redact_command",
]
