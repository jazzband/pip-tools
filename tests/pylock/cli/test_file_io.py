from __future__ import annotations

import importlib
import os
import sys
import typing as _t
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from piptools.exceptions import PipToolsError
from piptools.pylock.cli._file_io import (
    _advisory_lock,
    _render,
    emit_check,
    emit_dry_run,
    emit_write,
)

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock

# Used by Windows-skipped advisory-lock tests; ``importlib`` keeps the
# import out of isort's eager block so it doesn't fail at module import on win32.
_fcntl = importlib.import_module("fcntl") if sys.platform != "win32" else None


class FakeFileFactory(_t.Protocol):
    def __call__(self, path: str) -> MagicMock: ...


@pytest.fixture
def make_fake_file(mocker: MockerFixture) -> FakeFileFactory:
    # ``LazyFile.__getattr__`` proxies to a real file, so ``create_autospec``
    # doesn't expose ``write`` or settable ``name``. Tests stub the duck shape
    # of click's ``LazyFile`` (``name`` + ``write`` + ``close_intelligently``)
    # via plain ``MagicMock``.
    def _factory(path: str) -> MagicMock:
        fake = _t.cast("MagicMock", mocker.MagicMock())
        fake.name = path
        return fake

    return _factory


def test_emit_write_wraps_oserror_as_pip_tools_error(mocker: MockerFixture) -> None:
    # Disk-full / permission-denied / EBADF surfacing here as a raw
    # ``OSError`` would give the user a Python traceback with no signal it
    # was the lockfile write that failed. The render path runs against a
    # ``BytesIO`` so the OSError comes from the file write itself.
    failing_file = mocker.MagicMock()
    failing_file.write.side_effect = OSError("read-only")
    with pytest.raises(PipToolsError, match="Failed to write lockfile"):
        emit_write(mocker.MagicMock(), failing_file)


def test_advisory_lock_no_op_when_output_is_stdout(
    make_fake_file: FakeFileFactory,
) -> None:
    # ``-o -`` (stdout) sets ``output_file.name`` to ``"-"``; locking a
    # virtual file would either hang or create a stray ``.-.lock`` file.

    fake = make_fake_file("-")
    with _advisory_lock(fake):
        pass


def test_advisory_lock_silent_when_fcntl_unavailable_and_no_contention(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # Windows path: ``O_CREAT|O_EXCL`` on a sibling lockfile gives best-
    # effort mutual exclusion without ``fcntl``. A clean run (no
    # concurrent process holding the lock) must NOT emit a warning; the
    # warning is reserved for the contention case so quiet runs stay
    # quiet.
    mocker.patch("piptools.pylock.cli._file_io._fcntl", None)
    log_warning = mocker.patch("piptools.pylock.cli._file_io.log.warning")
    fake = make_fake_file(str(tmp_path / "pylock.toml"))
    with _advisory_lock(fake):
        pass
    log_warning.assert_not_called()


def test_advisory_lock_warns_on_windows_under_contention(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # When a sibling ``.lock`` already exists, ``O_CREAT|O_EXCL`` raises
    # ``FileExistsError`` and the warning fires; telling the user a
    # concurrent invocation may be racing them.
    mocker.patch("piptools.pylock.cli._file_io._fcntl", None)
    output_path = tmp_path / "pylock.toml"
    (tmp_path / ".pylock.toml.lock").touch()
    log_warning = mocker.patch("piptools.pylock.cli._file_io.log.warning")
    fake = make_fake_file(str(output_path))
    with _advisory_lock(fake):
        pass
    log_warning.assert_called_once()


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl unavailable on Windows")
def test_advisory_lock_blocks_second_acquirer(  # pragma: win32 no cover
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # Without this assertion the contention path is untested and the lock
    # could regress to a no-op (e.g. F1's release-before-rename) and ship
    # green. Exercise actual mutual exclusion: while one ``_advisory_lock``
    # holds the file, a non-blocking second acquire on the same lockfile
    # must fail with ``BlockingIOError``.
    assert _fcntl is not None
    output_path = tmp_path / "pylock.toml"
    output_path.touch()
    fake = make_fake_file(str(output_path))
    with _advisory_lock(fake):
        lock_path = tmp_path / ".pylock.toml.lock"
        assert lock_path.exists()
        fd = os.open(str(lock_path), os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        finally:
            os.close(fd)


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl unavailable on Windows")
def test_advisory_lock_raises_for_missing_parent_dir(  # pragma: win32 no cover
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # Auto-creating the parent directory would mask a typo'd ``-o`` path;
    # the user wants the missing-dir error, not a brand-new directory.

    fake = make_fake_file(str(tmp_path / "does-not-exist" / "pylock.toml"))
    lock_cm = _advisory_lock(fake)
    with pytest.raises(PipToolsError, match="does not exist"):
        lock_cm.__enter__()


def test_emit_write_closes_atomic_file_inside_lock_window(
    mocker: MockerFixture,
) -> None:
    # Click's atomic ``LazyFile`` renames at close. Without the explicit
    # ``close_intelligently()`` call inside ``emit_write`` the rename
    # would happen *after* ``ctx.with_resource(_advisory_lock(...))``
    # released the lock (LIFO release on click's ``ExitStack``), leaving
    # a window for a competing pip-lock to seed from the stale file.

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump")
    fake_file = mocker.MagicMock()
    emit_write(mocker.MagicMock(), fake_file)
    fake_file.close_intelligently.assert_called_once()


def test_emit_write_skips_close_for_plain_binary_io(mocker: MockerFixture) -> None:
    # ``-o -`` (stdout) and other non-lazy targets must not attempt a
    # ``close_intelligently`` that would crash on a vanilla ``BinaryIO``.
    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump")
    plain = mocker.MagicMock(spec=["write"])
    emit_write(mocker.MagicMock(), plain)
    plain.write.assert_called_once()


def test_emit_dry_run_writes_to_stdout(mocker: MockerFixture) -> None:
    # ``--dry-run`` streams the rendered lockfile to stdout without touching
    # disk; the log banner goes to stderr so a piped capture stays clean.
    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    echo = mocker.patch("piptools.pylock.cli._file_io.echo")
    log_info = mocker.patch("piptools.pylock.cli._file_io.log.info")
    emit_dry_run(mocker.MagicMock())
    echo.assert_called_once()
    assert "lock-version" in echo.call_args.args[0]
    log_info.assert_called_once()


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl unavailable on Windows")
def test_advisory_lock_unlock_swallows_oserror(  # pragma: win32 no cover
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # ``LOCK_UN`` failing during teardown (e.g. fd already closed by a
    # signal handler) must not bubble out; the lock release is best-effort
    # and the user already has a valid lockfile by this point.
    assert _fcntl is not None
    output_path = tmp_path / "pylock.toml"
    output_path.touch()
    fake = make_fake_file(str(output_path))
    real_flock = _fcntl.flock

    def flock_unlock_raises(fd: int, op: int) -> None:
        if op == _fcntl.LOCK_UN:
            raise OSError("fd no longer valid")
        real_flock(fd, op)

    mocker.patch.object(_fcntl, "flock", side_effect=flock_unlock_raises)
    with _advisory_lock(fake):
        pass


def test_emit_check_passes_when_file_matches(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # ``--check`` exits cleanly when the on-disk lockfile matches what the
    # resolver would emit. CI uses this to detect drift without writing.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\nfoo = "bar"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    output_path.write_bytes(b'lock-version = "1.0"\nfoo = "bar"\n')
    fake_file = make_fake_file(str(output_path))
    emit_check(mocker.MagicMock(), fake_file)


def test_emit_check_exits_one_when_file_differs(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # Drift: the on-disk file diverges from what the resolver just produced;
    # ``--check`` exits 1 so a CI step fails.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\npkg = "1.2.3"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    output_path.write_bytes(b'lock-version = "1.0"\npkg = "1.0.0"\n')
    fake_file = make_fake_file(str(output_path))
    with pytest.raises(SystemExit, match="1"):
        emit_check(mocker.MagicMock(), fake_file)


def test_emit_check_exits_one_when_file_missing(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # No file = total drift; ``--check`` must exit non-zero so CI doesn't
    # accidentally pass on the very first commit before a lockfile lands.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\npkg = "1.2.3"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    fake_file = make_fake_file(str(output_path))
    with pytest.raises(SystemExit, match="1"):
        emit_check(mocker.MagicMock(), fake_file)


def test_emit_check_uses_semantic_equality(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # A tomli_w bump that reformats whitespace, key ordering on collision, or
    # multi-line-string heuristics must not flag every existing lock as
    # out-of-date. ``--check`` compares parsed TOML, not raw bytes.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        # Render with one whitespace shape; existing file has another.
        dst.write(b'lock-version = "1.0"\nfoo = "bar"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    output_path.write_text('foo = "bar"\nlock-version = "1.0"\n')
    fake_file = make_fake_file(str(output_path))
    emit_check(mocker.MagicMock(), fake_file)


def test_emit_check_writes_new_file_on_drift(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # On drift, write the proposed bytes alongside the existing file as
    # ``.new`` so the user can ``diff`` directly. Without this the error
    # message tells them what's wrong but not which packages drifted.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\npkg = "1.2.3"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    output_path.write_bytes(b'lock-version = "1.0"\npkg = "1.0.0"\n')
    fake_file = make_fake_file(str(output_path))
    with pytest.raises(SystemExit, match="1"):
        emit_check(mocker.MagicMock(), fake_file)
    new_path = output_path.with_suffix(".toml.new")
    assert new_path.exists()
    assert b'pkg = "1.2.3"' in new_path.read_bytes()


def test_emit_check_recovers_from_corrupt_existing(
    tmp_path: Path, mocker: MockerFixture, make_fake_file: FakeFileFactory
) -> None:
    # An unparseable on-disk pylock.toml shouldn't crash ``--check``; it
    # should be treated as "drift" so the user re-runs and overwrites.
    output_path = tmp_path / "pylock.toml"

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    output_path.write_bytes(b"this is not valid toml = [[[")
    fake_file = make_fake_file(str(output_path))
    with pytest.raises(SystemExit, match="1"):
        emit_check(mocker.MagicMock(), fake_file)


def test_emit_check_with_stdout_falls_back_to_simple_error(
    mocker: MockerFixture,
    make_fake_file: FakeFileFactory,
) -> None:
    # ``-o -`` (stdout) has no on-disk path to write ``.new`` to; the simple
    # "out of date; re-run" message still surfaces and the function exits 1.

    def fake_write(doc: object, dst: _t.BinaryIO) -> None:
        dst.write(b'lock-version = "1.0"\n')

    mocker.patch("piptools.pylock.cli._file_io.tomli_w_dump", side_effect=fake_write)
    fake_file = make_fake_file("-")
    log_error = mocker.patch("piptools.pylock.cli._file_io.log.error")
    with pytest.raises(SystemExit, match="1"):
        emit_check(mocker.MagicMock(), fake_file)
    log_error.assert_called_once()
    assert "out of date" in log_error.call_args.args[0]


def test_render_places_wheels_before_sdist(mocker: MockerFixture) -> None:
    lock_doc = mocker.MagicMock(name="lock_doc")
    lock_doc.to_dict.return_value = {
        "lock-version": "1.0",
        "packages": [
            {
                "name": "pkg",
                "sdist": {"name": "pkg-1.0.tar.gz", "hashes": {"sha256": "a"}},
                "wheels": [
                    {"name": "pkg-1.0-py3-none-any.whl", "hashes": {"sha256": "b"}}
                ],
            }
        ],
    }
    rendered = _render(lock_doc).decode("utf-8")
    assert rendered.index("wheels") < rendered.index("sdist")


@pytest.mark.parametrize(
    "package",
    (
        pytest.param(
            {"name": "pkg", "sdist": {"hashes": {"sha256": "a"}}}, id="sdist-only"
        ),
        pytest.param(
            {"name": "pkg", "wheels": [{"hashes": {"sha256": "a"}}]}, id="wheels-only"
        ),
        pytest.param({"name": "pkg"}, id="no-files"),
    ),
)
def test_render_leaves_partial_package_shapes_alone(
    mocker: MockerFixture, package: dict[str, _t.Any]
) -> None:
    lock_doc = mocker.MagicMock(name="lock_doc")
    lock_doc.to_dict.return_value = {"lock-version": "1.0", "packages": [package]}
    _render(lock_doc)
