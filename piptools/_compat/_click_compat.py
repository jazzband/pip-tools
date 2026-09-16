"""
Compatibility helpers and wrappers for working with :external+click:doc:`click <index>`.
"""

from __future__ import annotations

import contextlib
import typing as _t

import click


def open_output_file(ctx: click.Context, filename: str) -> _t.BinaryIO:
    """
    Open a file with the desirable flags set for writing output.

    The file will be lazy and atomic unless it's stdout.
    """
    # open_file() returns a typing.IO , but we know it will be binary because of the
    # mode flag -- so type-ignore the assignment issue
    file: _t.BinaryIO = click.open_file(  # type: ignore[assignment]
        filename, "w+b", atomic=True, lazy=True
    )
    _defer_lazy_file_close(ctx, file)
    return file


def _defer_lazy_file_close(ctx: click.Context, fileobj: _t.BinaryIO) -> None:
    """Setup a click "lazy file" to close on exit."""
    ctx.call_on_close(lambda: _close_intelligently(fileobj))


def _close_intelligently(fileobj: _t.BinaryIO) -> None:
    """
    Close the file if it defines ``should_close`` and gives it a truthy value.

    This relies on click's internal ``LazyFile`` type's ``should_close`` behavior, and
    suppresses errors which may occur when closing a file.
    """
    # Note that the LazyFile type is not public, so we are passed a BinaryIO and we will
    # try to use the attribute (which we know `click` provides).
    if not getattr(fileobj, "should_close", None):
        return

    with contextlib.suppress(OSError):
        fileobj.close()
