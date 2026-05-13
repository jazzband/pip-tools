from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from piptools.pylock.cli._seeds import seed_pins_from_existing_lock


def test_seed_pins_strips_unsafe_packages_when_allow_unsafe_off(
    tmp_path: Path,
) -> None:
    # ``--allow-unsafe`` controls whether pip / setuptools / distribute are
    # written into the lock; when the flag is off, seeding their old pins
    # would feed the resolver constraints it's supposed to ignore. Strip
    # unsafe names from the seed unconditionally unless the user opts in.

    pylock = tmp_path / "pylock.toml"
    pylock.write_text(
        'lock-version = "1.0"\n'
        '[[packages]]\nname = "pip"\nversion = "26.0"\n'
        '[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
    )
    pins = seed_pins_from_existing_lock(pylock, ())
    assert pins == ("requests==2.31.0",)


def test_seed_pins_keeps_unsafe_when_allow_unsafe_on(tmp_path: Path) -> None:

    pylock = tmp_path / "pylock.toml"
    pylock.write_text(
        'lock-version = "1.0"\n'
        '[[packages]]\nname = "pip"\nversion = "26.0"\n'
        '[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
    )
    pins = seed_pins_from_existing_lock(pylock, (), allow_unsafe=True)
    assert "pip==26.0" in pins
    assert "requests==2.31.0" in pins


def test_seed_pins_excludes_upgrade_packages(tmp_path: Path) -> None:
    # ``--upgrade-package <name>`` exempts the named packages from seeding
    # so they re-resolve. Anything else carries the old pin forward.

    pylock = tmp_path / "pylock.toml"
    pylock.write_text(
        'lock-version = "1.0"\n'
        '[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
        '[[packages]]\nname = "urllib3"\nversion = "2.0.7"\n'
    )
    pins = seed_pins_from_existing_lock(pylock, ("requests",))
    assert pins == ("urllib3==2.0.7",)


@pytest.mark.parametrize(
    ("filename", "content"),
    (
        pytest.param("missing.toml", None, id="missing-file"),
        pytest.param("pylock.toml", "not valid toml [[[", id="unparseable-toml"),
        pytest.param(
            "pylock.toml",
            'lock-version = "2.0"\n[[packages]]\nname = "requests"\nversion = "2.31.0"\n',
            id="unsupported-lock-version",
        ),
        pytest.param(
            "pylock.toml",
            'lock-version = "not-a-version"\n[[packages]]\nname = "x"\nversion = "1.0"\n',
            id="malformed-lock-version",
        ),
    ),
)
def test_seed_pins_returns_empty_for_unusable_lock(
    tmp_path: Path, filename: str, content: str | None
) -> None:
    pylock = tmp_path / filename
    if content is not None:
        pylock.write_text(content)
    assert seed_pins_from_existing_lock(pylock, ()) == ()


def test_seed_pins_skips_entries_missing_version(tmp_path: Path) -> None:
    # VCS / directory entries omit ``version``; a name-only entry can't
    # produce a ``name==version`` constraint, so the seed must skip it
    # rather than emit ``name==`` (which the resolver rejects).

    pylock = tmp_path / "pylock.toml"
    pylock.write_text(
        'lock-version = "1.0"\n'
        '[[packages]]\nname = "vcs-pkg"\n'
        '[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
    )
    pins = seed_pins_from_existing_lock(pylock, ())
    assert pins == ("requests==2.31.0",)


def test_seed_pins_skips_malformed_upgrade_package(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    # ``--upgrade-package`` accepts full requirement specs (``foo[dev]==1.0``);
    # the bare ``canonicalize_name`` would normalize the whole spec into a
    # hyphen blob, the seed would never match, and the resolver would see
    # both the seeded ``foo==<old>`` and the user's ``foo==<new>``. A bogus
    # token (``not a requirement!``) should fall through with a warning,
    # not crash the lock.

    output = tmp_path / "pylock.toml"
    output.write_text(dedent("""
            lock-version = "1.0"
            [[packages]]
            name = "requests"
            version = "2.30.0"
        """))
    log_warning = mocker.patch("piptools.pylock.cli._seeds.log.warning")
    pins = seed_pins_from_existing_lock(output, ("not a requirement!",))
    log_warning.assert_called_once()
    assert pins == ("requests==2.30.0",)


def test_seed_pins_extras_in_upgrade_package_dropped(tmp_path: Path) -> None:
    # ``--upgrade-package foo[dev]==1.0`` with an existing ``foo`` pin must
    # drop the seed (``foo`` is being upgraded); not keep it because a
    # bare canonicalize over the whole spec yields a non-matching blob.

    output = tmp_path / "pylock.toml"
    output.write_text(dedent("""
            lock-version = "1.0"
            [[packages]]
            name = "requests"
            version = "2.30.0"
        """))
    pins = seed_pins_from_existing_lock(output, ("requests[security]==2.31.0",))
    assert pins == ()


def test_seed_pins_drops_duplicate_conflict_group_entries(tmp_path: Path) -> None:
    # H_baseline_reuse_under_conflicts: a re-lock with conflict groups produces
    # multiple same-name ``[[packages]]`` entries (one per group). Flat-seeding
    # them would feed the partition scan ``black==22.1.0`` AND ``black==23.12.0``
    # together; pip's resolver raises ``RequirementsConflicted`` before the
    # per-cohort resolutions ever run.

    output = tmp_path / "pylock.toml"
    output.write_text(dedent("""
            lock-version = "1.0"
            [[packages]]
            name = "black"
            version = "22.1.0"
            marker = "'black22' in dependency_groups"
            [[packages]]
            name = "black"
            version = "23.12.0"
            marker = "'black23' in dependency_groups"
            [[packages]]
            name = "requests"
            version = "2.31.0"
        """))
    pins = seed_pins_from_existing_lock(output, ())
    # ``black`` has two entries; drop both. ``requests`` is unique, keep it.
    assert pins == ("requests==2.31.0",)


def test_seed_pins_accepts_normalised_lock_version(tmp_path: Path) -> None:
    # PEP 751 says ``lock-version`` is a string; tools may write ``1.0``,
    # ``1.0.0``, or any other PEP 440-equivalent normal form. Seed must
    # accept all of them so a uv-written lock round-trips through pip-tools.
    pylock = tmp_path / "pylock.toml"
    pylock.write_text(
        'lock-version = "1.0.0"\n[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
    )
    pins = seed_pins_from_existing_lock(pylock, ())
    assert pins == ("requests==2.31.0",)
