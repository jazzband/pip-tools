from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from piptools.scripts.options import color, help_option


def test_help_opt_no_epilog(runner: CliRunner) -> None:
    """
    Test that the customized ``--help`` option can be used without an epilog declared.
    """

    @click.command("my-command")
    @help_option()
    def my_command() -> None:
        pytest.fail("command ran unexpectedly")

    result = runner.invoke(my_command, ["--help"])
    assert result.exit_code == 0
    assert result.stdout.startswith("Usage: my-command")
    # --help option helptext should be last, whitespace aside
    assert result.stdout.rstrip().endswith("Show this message and exit.")


def test_help_opt_with_epilog(runner: CliRunner) -> None:
    """
    Test that the ``epilog`` option for customized ``--help`` test appends the given
    text to the end of the helptext.
    """

    @click.command("my-command")
    @help_option(epilog="hello there")
    def my_command() -> None:
        pytest.fail("command ran unexpectedly")

    result = runner.invoke(my_command, ["--help"])
    assert result.exit_code == 0
    assert result.stdout.startswith("Usage: my-command")
    # the epilog should be last, whitespace aside
    assert result.stdout.rstrip().endswith("hello there")


@pytest.mark.parametrize(
    ("args", "expect_setting"),
    (
        ([], None),
        (["--color"], True),
        (["--no-color"], False),
        # last one wins semantics
        (["--color", "--no-color"], False),
        (["--no-color", "--color"], True),
    ),
)
def test_color_opt_sets_context_color(
    runner: CliRunner, args: list[str], expect_setting: bool | None
) -> None:
    @click.command("my-command")
    @color
    @click.pass_context
    def my_command(ctx: click.Context) -> None:
        assert ctx.color == expect_setting

    result = runner.invoke(my_command, args)
    assert result.exit_code == 0
