"""Output-side helpers for ``pip-lock``: locking, writing, ``--check``.

Keeps file I/O (advisory flock, atomic-rename plumbing, bytes renderer,
``--check`` drift detector) out of the resolver-facing modules.
"""

from __future__ import annotations

import typing as _t
from contextlib import contextmanager
from importlib import import_module
from io import BytesIO
from os import O_CREAT, O_EXCL, O_RDWR
from os import close as os_close
from os import open as os_open
from os import unlink
from pathlib import Path
from sys import platform as sys_platform
from types import ModuleType

from click import echo
from click.utils import LazyFile
from packaging.pylock import Pylock
from tomli_w import dump as tomli_w_dump

from ..._compat import _tomllib_compat
from ...exceptions import PipToolsError
from ...logging import log

# ``fcntl`` is POSIX-only. ``msvcrt.locking`` byte-range semantics on Windows
# differ enough that pip-tools degrades to "no advisory lock, warn the user"
# rather than maintain two backends. The ``importlib`` indirection keeps
# isort/black from reordering it back above the other imports and tripping
# ``E402``.
_fcntl = import_module("fcntl") if sys_platform != "win32" else None


@contextmanager
def _advisory_lock(
    output_file: LazyFile | _t.IO[_t.Any] | None,
) -> _t.Iterator[None]:
    """Serialize concurrent ``pip-lock`` invocations against the same output.

    Two parallel locks read the same seed, resolve in parallel, then race on
    the atomic-rename write, leaving a non-deterministic surviving file. A
    sibling ``.<name>.lock`` file held under ``fcntl.LOCK_EX`` for the
    seed-to-write window collapses the race to "second invocation waits for
    the first." Windows lacks ``fcntl``; degrade to a warning so the user
    knows concurrent runs against the same artifact dir are unsafe.
    """
    if (
        output_file is None
        or not hasattr(output_file, "name")
        or output_file.name in {"-", "<stdout>"}
    ):
        yield
        return
    if _fcntl is None:  # pragma: win32 cover
        # Windows fallback: best-effort ``O_CREAT|O_EXCL`` exclusive-create on
        # a sibling ``.lock`` file. A successful create means no concurrent
        # ``pip-lock`` holds the output; ``FileExistsError`` means one does.
        # Warn only on contention so quiet runs stay quiet.
        output_path = Path(output_file.name)
        lock_path = output_path.parent / f".{output_path.name}.lock"
        try:
            fd = os_open(lock_path, O_RDWR | O_CREAT | O_EXCL, 0o600)
        except FileExistsError:
            log.warning(
                f"Another pip-lock invocation appears to be running against "
                f"{output_path.name}; running concurrently may produce "
                f"non-deterministic results. Remove {lock_path.name} after "
                f"that invocation finishes if it crashed and left the file."
            )
            yield
            return
        except FileNotFoundError as exc:
            raise PipToolsError(
                f"Output directory {output_path.parent!s} does not exist. "
                f"Create it before re-running, or pass a different --output-file."
            ) from exc
        try:
            yield
        finally:
            os_close(fd)
            try:
                unlink(lock_path)
            except OSError:
                pass
        return
    # Local rebind narrows the type for mypy; the ``_fcntl is None`` guard
    # above keeps this branch off win32.
    fcntl_mod: ModuleType = _fcntl  # pragma: win32 no cover
    output_path = Path(output_file.name)
    lock_path = output_path.parent / f".{output_path.name}.lock"
    # Don't ``mkdir`` the parent: a typo'd ``-o /typo/dir/pylock.toml``
    # would otherwise silently materialise a brand-new directory and land
    # the lock there. ``os.open`` raising ``FileNotFoundError`` becomes a
    # ``PipToolsError`` so the CLI exits 2 with a single line instead of
    # a Python traceback.
    try:  # pragma: win32 no cover
        fd = os_open(lock_path, O_RDWR | O_CREAT, 0o600)
    except FileNotFoundError as exc:  # pragma: win32 no cover
        raise PipToolsError(
            f"Output directory {output_path.parent!s} does not exist. "
            f"Create it before re-running, or pass a different --output-file."
        ) from exc
    try:  # pragma: win32 no cover
        fcntl_mod.flock(fd, fcntl_mod.LOCK_EX)
        yield
    finally:  # pragma: win32 no cover
        # Don't ``os.unlink(lock_path)`` here. ``flock`` is on the inode,
        # not the path; unlinking while a blocked second acquirer still
        # holds an open fd lets a third process create a *new* inode at the
        # same path and grab a separate ``flock`` on that, breaking mutual
        # exclusion. The 0-byte sibling lock file on disk is the cost.
        try:
            fcntl_mod.flock(fd, fcntl_mod.LOCK_UN)
        except OSError:
            pass
        os_close(fd)


def emit_check(doc: Pylock, output_file: LazyFile | _t.IO[_t.Any]) -> None:
    """Verify the on-disk lockfile matches ``doc`` and exit non-zero on drift.

    Compares parsed TOML rather than raw bytes so reformatter changes do not
    flag every lockfile out of date. Writes the proposed bytes to a sibling
    ``.new`` file when drift is detected so the user can diff the two.

    :param doc: Lockfile produced by the resolver this run.
    :param output_file: File handle pointing at the lockfile path on disk.
    :raises SystemExit: With code ``1`` when the existing lockfile differs.
    """
    rendered = _render(doc)
    new_doc = _tomllib_compat.loads(rendered.decode("utf-8"))
    existing_doc: dict[str, _t.Any] = {}
    existing_path: Path | None = None
    if hasattr(output_file, "name") and output_file.name not in {"-", "<stdout>"}:
        existing_path = Path(output_file.name)
        if existing_path.exists():
            try:
                with open(existing_path, "rb") as f:
                    existing_doc = _tomllib_compat.load(f)
            except (OSError, ValueError):
                existing_doc = {}
    if new_doc == existing_doc:
        log.info("pylock.toml is up to date.")
        return
    if existing_path is not None:
        new_path = existing_path.with_suffix(existing_path.suffix + ".new")
        new_path.write_bytes(rendered)
        log.error(
            f"pylock.toml is out of date; wrote proposed lockfile to "
            f"{new_path!s}. Diff against {existing_path!s} to see the "
            f"changes, then re-run pip-lock to apply."
        )
    else:
        log.error("pylock.toml is out of date; re-run pip-lock to update.")
    raise SystemExit(1)


def emit_dry_run(doc: Pylock) -> None:
    """Stream the rendered lockfile to stdout without touching disk.

    :param doc: Lockfile to render.
    """
    rendered = _render(doc)
    # ``click.echo`` writes to stdout (not the log's stderr) so
    # ``pip-lock --dry-run | tee pylock.toml`` produces a clean TOML
    # stream without log banners. ``errors="replace"`` defends against a
    # future writer change that emits non-UTF-8 bytes; tomli_w is UTF-8.
    echo(rendered.decode("utf-8", errors="replace"), nl=False)
    log.info("Dry-run, so nothing updated.")


def emit_write(doc: Pylock, output_file: LazyFile | _t.IO[_t.Any]) -> None:
    """Render ``doc`` to bytes and atomically commit them to ``output_file``.

    :param doc: Lockfile to render.
    :param output_file: Destination file. When backed by an atomic writer,
        the rename is forced inside the advisory-lock window so a blocked
        concurrent invocation cannot read the stale lockfile as its seed.
    :raises PipToolsError: When the underlying write fails.
    """
    rendered = _render(doc)
    try:
        _t.cast("_t.BinaryIO", output_file).write(rendered)
        # Click's ``LazyFile(atomic=True)`` writes to a tempfile and renames
        # at close. ``ctx.call_on_close`` would run that close LIFO after
        # ``ctx.with_resource(_advisory_lock(...))`` releases the lock,
        # opening a window for a blocked competitor to read the *old*
        # pylock.toml as its seed before the rename lands. Closing here
        # keeps the rename inside the locked region; click's ``safecall``
        # makes the trailing ``call_on_close`` a no-op.
        if hasattr(output_file, "close_intelligently"):
            _t.cast("LazyFile", output_file).close_intelligently()
    except OSError as exc:
        raise PipToolsError(
            f"Failed to write lockfile: {exc}. Check disk space and "
            f"permissions on the output directory, then re-run."
        ) from exc


def _render(doc: Pylock) -> bytes:
    """Serialize ``doc`` to bytes once for every emit path to consume."""
    data = dict(doc.to_dict())
    # PEP 751 leaves sdist/wheels order to the writer; place wheels before
    # the single sdist so a reader's eye lands on the installable artifact
    # they will likely pick before the source fallback.
    packages = data.get("packages")
    if isinstance(packages, list):
        for package in packages:
            if isinstance(package, dict) and "sdist" in package and "wheels" in package:
                package["sdist"] = package.pop("sdist")
    buf = BytesIO()
    tomli_w_dump(data, buf)
    return buf.getvalue()


__all__ = [
    "emit_check",
    "emit_dry_run",
    "emit_write",
]
