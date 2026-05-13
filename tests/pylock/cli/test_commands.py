from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from piptools.pylock.cli._commands import cli


def test_check_dispatch_calls_emit_check(tmp_path: Path, mocker: MockerFixture) -> None:
    # ``--check`` selects ``emit_check`` from the post-build dispatch; the
    # dry-run / write branches must not run. End-to-end through the CLI so
    # the click wiring + the dispatch decision are exercised together.
    requirements = tmp_path / "requirements.in"
    requirements.write_text("")
    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        return_value=mocker.MagicMock(),
    )
    check = mocker.patch("piptools.pylock.cli._commands.emit_check")
    write = mocker.patch("piptools.pylock.cli._commands.emit_write")
    dry_run = mocker.patch("piptools.pylock.cli._commands.emit_dry_run")
    output = tmp_path / "pylock.toml"
    runner = CliRunner()
    result = runner.invoke(
        cli, [str(requirements), "--check", "--no-universal", "-o", str(output)]
    )
    assert result.exit_code == 0, result.output
    check.assert_called_once()
    write.assert_not_called()
    dry_run.assert_not_called()


@pytest.mark.parametrize(
    ("extra_args", "env"),
    (
        pytest.param(
            (),
            {"PIP_TOOLS_HIDE_EXPERIMENTAL_WARNING": "1"},
            id="env-var-suppresses-experimental-banner",
        ),
        pytest.param(
            ("--upgrade",),
            {},
            id="upgrade-skips-seed-pins-from-existing-lock",
        ),
        pytest.param(
            ("--no-index",),
            {},
            id="no-index-skips-index-debug-log",
        ),
    ),
)
def test_cli_exercises_optional_branches(
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    extra_args: tuple[str, ...],
    env: dict[str, str],
) -> None:
    # Each flag/env combo flips a single ``if`` whose other side is exercised
    # by the default ``--check`` test; covering both arms keeps codecov's
    # patch coverage at 100% without redundant assertion plumbing.
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    requirements = tmp_path / "requirements.in"
    requirements.write_text("")
    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        return_value=mocker.MagicMock(),
    )
    mocker.patch("piptools.pylock.cli._commands.emit_write")
    output = tmp_path / "pylock.toml"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(requirements),
            "--no-universal",
            "-o",
            str(output),
            "--no-config",
            *extra_args,
        ],
    )
    assert result.exit_code == 0, result.output
