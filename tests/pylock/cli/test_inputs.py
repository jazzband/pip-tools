from __future__ import annotations

from pytest_mock import MockerFixture

from piptools.pylock.cli._inputs import resolve_src_files


def test_resolve_src_files_uses_truthy_default_map_value(
    mocker: MockerFixture,
) -> None:
    # When the config file carries paths in ``src_files``, the resolver
    # uses that list rather than the auto-pickup. The N1 fix's truthy
    # check gates this branch.

    click_context = mocker.MagicMock()
    click_context.default_map = {"src_files": ["from-config.in"]}
    assert resolve_src_files(click_context, ()) == ("from-config.in",)
