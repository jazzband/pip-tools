from __future__ import annotations

import collections.abc as _c
import contextlib
import enum
import os
import typing as _t


class _Sentinel(enum.Enum):
    _SENTINEL = object()


_SENTINEL = _Sentinel._SENTINEL


@contextlib.contextmanager
def setenv_context(
    env_var_name: str,
    env_var_value: str,
    /,
) -> _c.Iterator[None]:
    """
    A context manager which sets an environment variable and resets on exit.

    It is robust to interruptions and exceptions, so long as its ``finally`` block is
    allowed to run to completion.
    """
    original_value: str | _t.Literal[_Sentinel._SENTINEL] = os.getenv(
        env_var_name, _SENTINEL
    )

    os.environ[env_var_name] = env_var_value
    try:
        yield
    finally:
        # if the variable was not set, delete it and suppress any exception
        # if setting it (in the try block above) failed or was interrupted
        if original_value is _SENTINEL:
            with contextlib.suppress(KeyError):
                del os.environ[env_var_name]
        # otherwise, we got a value when we called getenv(), and we should reset it
        else:
            os.environ[env_var_name] = original_value
