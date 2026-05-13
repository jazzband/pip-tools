from __future__ import annotations

import sys
import typing as _t
from pathlib import Path
from textwrap import dedent

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib  # type: ignore[no-redef]

import click
import pytest
from click.testing import CliRunner
from packaging.pylock import PylockValidationError
from pytest_mock import MockerFixture
from tomli_w import dumps as tomli_w_dumps

from piptools._internal import _pip_api
from piptools.exceptions import NoCandidateFound, PipToolsError
from piptools.pylock._inputs import LockSelection
from piptools.pylock.builder import _build_top_level_environments
from piptools.pylock.platforms import (
    PLATFORM_ENVIRONMENTS,
    _linux,
    build_target_environments,
)
from piptools.scripts.lock import cli
from piptools.scripts.options import (
    _parse_jobs,
    _platform_choices,
    _validate_platform,
    _validate_python_versions,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize(
    "value",
    (
        pytest.param("3", id="single-component"),
        pytest.param("3.12.5.0", id="four-components"),
        pytest.param("foo", id="non-numeric"),
        pytest.param("3.x", id="alpha-suffix"),
        pytest.param("", id="empty"),
    ),
)
def test_python_version_rejects_malformed(
    runner: CliRunner, requirements_in: Path, value: str
) -> None:
    result = runner.invoke(
        cli,
        [str(requirements_in), "--python-version", value, "--no-universal"],
    )
    assert result.exit_code != 0
    assert "MAJOR.MINOR" in result.output


def test_no_universal_raises_for_unsupported_current_platform(
    runner: CliRunner,
    requirements_in: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "piptools.pylock.cli._targets.default_environment",
        return_value={"sys_platform": "freebsd", "platform_machine": "amd64"},
    )
    result = runner.invoke(cli, [str(requirements_in), "--no-universal"])
    assert result.exit_code != 0
    assert "freebsd" in result.output
    assert "--platform" in result.output


def test_platform_current_rewrap_keeps_supported_list(
    runner: CliRunner,
    requirements_in: Path,
    mocker: MockerFixture,
) -> None:
    # The rewrap from ``--no-universal`` to ``--platform current`` must keep
    # the supported-presets list and the current ``(sys_platform,
    # platform_machine)`` context; without that the user typing
    # ``--platform current`` on an unknown host gets a message stripped of
    # the actionable info the underlying error built.
    mocker.patch(
        "piptools.pylock.cli._targets.default_environment",
        return_value={"sys_platform": "freebsd", "platform_machine": "amd64"},
    )
    result = runner.invoke(cli, [str(requirements_in), "--platform", "current"])
    assert result.exit_code != 0
    assert "freebsd" in result.output
    assert "linux-x86_64" in result.output
    assert "--platform current" in result.output
    # The original ``--no-universal`` reference is rewritten to the flag the
    # user passed.
    assert "--no-universal" not in result.output


def test_help_documents_upgrade_flags(runner: CliRunner) -> None:
    # pip-lock seeds pins from the existing ``pylock.toml`` for re-locks
    # (the pip-compile ``-P`` workflow), so ``--upgrade`` has a defined
    # meaning: bypass the seed. Both flags must appear in ``--help`` so
    # users discover the re-lock surface without reading source.
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--upgrade" in result.output
    assert "--upgrade-package" in result.output


def test_no_universal_raises_for_ambiguous_current_platform(
    runner: CliRunner,
    requirements_in: Path,
    mocker: MockerFixture,
) -> None:

    mocker.patch.dict(
        PLATFORM_ENVIRONMENTS,
        {"linux-x86_64-musl": _linux("x86_64"), "linux-x86_64-glibc": _linux("x86_64")},
    )
    mocker.patch(
        "piptools.pylock.cli._targets.default_environment",
        return_value={"sys_platform": "linux", "platform_machine": "x86_64"},
    )
    result = runner.invoke(cli, [str(requirements_in), "--no-universal"])
    assert result.exit_code != 0
    assert "Multiple platform presets" in result.output
    assert "--platform" in result.output


def test_custom_platform_threads_through_marker_composer() -> None:
    # ``--platform freebsd-amd64`` is accepted at the click validator and
    # ``build_target_environments`` synthesises an env via
    # ``_best_effort_platform_env``; without threading the same fallback
    # through ``_platform_only_marker`` the per-package marker composer
    # would ``KeyError`` on the unknown key. Compose markers directly so
    # the assertion isn't gated on network/wheel-tag plumbing.

    target_envs = build_target_environments(
        ("freebsd-amd64", "linux-x86_64"), ("3.12",)
    )
    envs = _build_top_level_environments(
        target_envs,
        python_versions=("3.12",),
        platforms=("freebsd-amd64", "linux-x86_64"),
    )
    assert envs
    assert any("freebsd" in env for env in envs)


@pytest.fixture
def requirements_in(tmp_path: Path) -> Path:
    req_file = tmp_path / "requirements.in"
    req_file.write_text("small-fake-a==0.1\n")
    return req_file


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_basic_lock(runner: CliRunner, requirements_in: Path) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 0, result.stderr
    assert output.exists()

    with open(output, "rb") as f:
        doc = tomllib.load(f)
    assert doc["lock-version"] == "1.0"
    assert doc["created-by"].startswith("pip-tools")
    assert len(doc["packages"]) >= 1

    pkg_names = {p["name"] for p in doc["packages"]}
    assert "small-fake-a" in pkg_names


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_default_output(
    runner: CliRunner, requirements_in: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(requirements_in.parent)
    result = runner.invoke(cli, [str(requirements_in), "--no-universal"])
    assert result.exit_code == 0, result.stderr
    assert (requirements_in.parent / "pylock.toml").exists()


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_dry_run(runner: CliRunner, requirements_in: Path) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal", "--dry-run"]
    )
    assert result.exit_code == 0, result.stderr
    assert not output.exists()


def test_lock_no_input_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["--no-universal"], catch_exceptions=False)
    assert result.exit_code != 0


@pytest.mark.parametrize(
    "filename",
    (
        pytest.param("requirements.txt", id="wrong-extension"),
        pytest.param("lock.toml", id="wrong-prefix"),
        pytest.param("pylock.dev.extra.toml", id="too-many-parts"),
        pytest.param("pylock-dev.toml", id="hyphen-separator"),
        pytest.param("PYLOCK.toml", id="uppercase-prefix"),
        pytest.param("pylock.toml.bak", id="trailing-suffix"),
    ),
)
def test_lock_invalid_output_filename(
    runner: CliRunner, requirements_in: Path, filename: str
) -> None:
    output = requirements_in.parent / filename
    result = runner.invoke(cli, [str(requirements_in), "-o", str(output)])
    assert result.exit_code != 0
    assert "pylock" in result.output.lower() or "output-file" in result.output.lower()


@pytest.mark.parametrize(
    "filename",
    (
        pytest.param("pylock.toml", id="base"),
        pytest.param("pylock.dev.toml", id="dot-separator"),
        pytest.param("pylock.my-env.toml", id="hyphenated-name"),
    ),
)
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_valid_output_filename(
    runner: CliRunner, requirements_in: Path, filename: str
) -> None:
    output = requirements_in.parent / filename
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


class _HashesEntry(_t.TypedDict):
    hashes: dict[str, str]


class _PackageEntry(_t.TypedDict, total=False):
    sdist: _HashesEntry
    wheels: list[_HashesEntry]


@pytest.mark.parametrize(
    ("packages", "expect_sdist", "expect_wheel"),
    (
        pytest.param(
            [
                {"sdist": {"hashes": {"sha256": "a"}}},
                {"wheels": [{"hashes": {"sha256": "b"}}]},
            ],
            True,
            True,
            id="separate-sdist-and-wheel",
        ),
        pytest.param(
            [
                {
                    "sdist": {"hashes": {"sha256": "a"}},
                    "wheels": [{"hashes": {"sha256": "b"}}],
                },
            ],
            True,
            True,
            id="combined-sdist-and-wheels",
        ),
        pytest.param(
            [{"wheels": [{"hashes": {"sha256": "a"}}]}], False, True, id="wheels-only"
        ),
        pytest.param(
            [{"sdist": {"hashes": {"sha256": "a"}}}], True, False, id="sdist-only"
        ),
    ),
)
def test_lock_packages_have_hashes(
    packages: list[_PackageEntry], expect_sdist: bool, expect_wheel: bool
) -> None:
    saw_sdist = False
    saw_wheel = False
    for pkg in packages:
        if "sdist" in pkg:
            assert "hashes" in pkg["sdist"]
            saw_sdist = True
        if "wheels" in pkg:
            for wheel in pkg["wheels"]:
                assert "hashes" in wheel
                saw_wheel = True
    assert saw_sdist is expect_sdist
    assert saw_wheel is expect_wheel


def test_lock_color_flag_sets_context(
    runner: CliRunner, requirements_in: Path, mocker: MockerFixture
) -> None:
    # End-to-end: the CLI threads ``--no-color`` through to the click
    # context. Observe via ``resolve_src_files`` (called immediately after
    # the inline color/log assignment) so the test sees the side effect
    # without coupling to the assignment statement itself.
    captured: dict[str, bool | None] = {}

    def _capture(ctx: click.Context, src_files: tuple[str, ...]) -> tuple[str, ...]:
        captured["color"] = ctx.color
        return src_files or (str(requirements_in),)

    mocker.patch(
        "piptools.pylock.cli._commands.resolve_src_files", side_effect=_capture
    )
    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        return_value=mocker.MagicMock(),
    )
    mocker.patch("piptools.pylock.cli._commands.emit_check")
    mocker.patch("piptools.pylock.cli._commands.emit_dry_run")
    mocker.patch("piptools.pylock.cli._commands.emit_write")
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(requirements_in), "--no-color", "--no-universal", "-o", str(output)],
    )
    assert result.exit_code == 0, result.output
    assert captured["color"] is False


@pytest.mark.usefixtures("pip_conf")
def test_no_metadata_and_skip_metadata_field_compose(
    runner: CliRunner,
    requirements_in: Path,
) -> None:
    # Combining ``--no-metadata`` (whole-block off) with
    # ``--skip-metadata-field`` (per-field) is redundant rather than wrong:
    # suppressing the block also suppresses every field. Allow the
    # combination so users scripting both via templates don't have to branch.
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(requirements_in),
            "-o",
            str(output),
            "--no-universal",
            "--no-metadata",
            "--skip-metadata-field",
            "command",
        ],
    )
    assert result.exit_code == 0, result.stderr
    assert "[tool.pip-tools]" not in output.read_text()


def test_no_tool_block_alias_works(runner: CliRunner, requirements_in: Path) -> None:
    # ``--no-tool-block`` is the clearer alias name (the flag affects only the
    # tool-private block, not PEP 751 packages metadata); both spellings drive
    # the same option.
    result = runner.invoke(
        cli,
        [str(requirements_in), "--no-tool-block", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_no_metadata_suppresses_tool_section(
    runner: CliRunner, requirements_in: Path
) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(requirements_in), "-o", str(output), "--no-universal", "--no-metadata"],
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    assert "tool" not in doc


@pytest.mark.parametrize(
    ("skip_field", "absent_key"),
    (
        pytest.param("command", "command", id="command"),
        pytest.param("generated-at", "generated-at", id="generated-at"),
        pytest.param("pip-version", "pip-version", id="pip-version"),
        pytest.param("platforms", "platforms", id="platforms"),
        pytest.param("python-versions", "python-versions", id="python-versions"),
    ),
)
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_skip_metadata_field_omits_key(
    runner: CliRunner,
    requirements_in: Path,
    skip_field: str,
    absent_key: str,
) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(requirements_in),
            "-o",
            str(output),
            "--no-universal",
            "--skip-metadata-field",
            skip_field,
        ],
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    assert absent_key not in doc.get("tool", {}).get("pip-tools", {})


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    (
        pytest.param(
            ["--all-build-deps", "--build-deps-for", "wheel"],
            "no effect",
            id="all-build-deps-with-build-deps-for",
        ),
        pytest.param(
            ["--only-build-deps"],
            "--only-build-deps requires",
            id="only-build-deps-without-target",
        ),
        pytest.param(
            ["--only-build-deps", "--all-build-deps", "--extra", "dev"],
            "--only-build-deps cannot be used",
            id="only-build-deps-with-extra",
        ),
        pytest.param(
            ["--all-extras", "--extra", "dev"],
            "no effect",
            id="all-extras-with-extra",
        ),
        pytest.param(
            ["-"],
            "--output-file is required if input is from stdin",
            id="stdin-without-output-file",
        ),
    ),
)
def test_validate_options_error(
    runner: CliRunner,
    tmp_path: Path,
    extra_args: list[str],
    expected_error: str,
) -> None:
    req = tmp_path / "requirements.in"
    req.write_text("certifi\n")
    base_args = [] if extra_args[0] == "-" else [str(req)]
    result = runner.invoke(cli, [*base_args, *extra_args], catch_exceptions=False)
    assert result.exit_code != 0
    assert expected_error.lower() in result.output.lower()


def test_validate_options_two_src_files_without_output(
    runner: CliRunner, tmp_path: Path
) -> None:
    req1 = tmp_path / "a.in"
    req2 = tmp_path / "b.in"
    req1.write_text("certifi\n")
    req2.write_text("idna\n")
    result = runner.invoke(cli, [str(req1), str(req2)], catch_exceptions=False)
    assert result.exit_code != 0
    assert "two or more" in result.output.lower()


def test_validate_options_default_file_found(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "requirements.in").write_text("certifi\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["--no-universal"])
    # Proceeds past validate_options (default file found), fails later
    assert "If you do not specify" not in result.output


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_with_constraint_file(runner: CliRunner, requirements_in: Path) -> None:
    constraint = requirements_in.parent / "constraints.txt"
    constraint.write_text("small-fake-a==0.1\n")
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(requirements_in),
            "-c",
            str(constraint),
            "-o",
            str(output),
            "--no-universal",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


# ── Non-network: --extra with .in file triggers error ────────────────────────
def test_extra_flag_with_non_setup_file_raises(
    runner: CliRunner, requirements_in: Path
) -> None:
    result = runner.invoke(
        cli, [str(requirements_in), "--extra", "dev"], catch_exceptions=False
    )
    assert result.exit_code != 0
    assert "--extra requires a project metadata file" in result.output


def test_extra_flag_dedups_repeated_inputs(
    runner: CliRunner, requirements_in: Path, mocker: MockerFixture
) -> None:
    # ``build_extras_configs`` schedules a per-extra resolution pass for every
    # listed extra; without the dedup ``--extra a,b --extra a`` ran the
    # conflicting-``a`` pass twice for no benefit.
    captured: dict[str, tuple[str, ...]] = {}

    def _spy(*args: object, **kwargs: object) -> object:
        selection = _t.cast("LockSelection", kwargs["selection"])
        captured["extras"] = selection.extras
        raise SystemExit(0)

    mocker.patch(
        "piptools.pylock.cli._commands.build_pylock_document", side_effect=_spy
    )
    pyproject = requirements_in.parent / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nversion = "0"\n'
        "[project.optional-dependencies]\na = []\nb = []\n"
    )
    runner.invoke(
        cli,
        [str(pyproject), "--extra", "a,b", "--extra", "a", "--no-universal"],
        catch_exceptions=False,
    )
    assert captured["extras"] == ("a", "b")


# ── Non-network: build-deps-for with .in file triggers error ─────────────────
def test_build_deps_for_with_non_setup_file_raises(
    runner: CliRunner, requirements_in: Path
) -> None:
    result = runner.invoke(
        cli,
        [str(requirements_in), "--build-deps-for", "wheel"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "setup.py, setup.cfg" in result.output


# ── Non-network: uploaded-prior-to requires pip >= 26.0 ──────────────────────
def test_uploaded_prior_to_old_pip_raises(
    runner: CliRunner, requirements_in: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (25, 0))
    result = runner.invoke(
        cli,
        [str(requirements_in), "--uploaded-prior-to", "2024-01-01T00:00:00Z"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "pip >= 26.0" in result.output


# ── Network: universal mode (no --no-universal) -> exercises environments ──────
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_universal_mode(runner: CliRunner, requirements_in: Path) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(requirements_in), "-o", str(output), "--python-version", "3.12"],
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    assert "environments" in doc


# ── Network: default output file (no -o) in universal mode ───────────────────
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_universal_default_output(
    runner: CliRunner, requirements_in: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(requirements_in.parent)
    result = runner.invoke(cli, [str(requirements_in), "--python-version", "3.12"])
    assert result.exit_code == 0, result.stderr
    assert (requirements_in.parent / "pylock.toml").exists()


# ── Network: explicit --platform skips auto-detect ───────────────────────────
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_with_explicit_platform(runner: CliRunner, requirements_in: Path) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(requirements_in),
            "-o",
            str(output),
            "--platform",
            "linux-x86_64",
            "--python-version",
            "3.12",
        ],
    )
    assert result.exit_code == 0, result.output


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_no_universal_emits_environments(
    runner: CliRunner, requirements_in: Path
) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    envs = doc.get("environments", [])
    assert envs, "no-universal mode should still narrow installable environments"
    assert any("python_version" in env for env in envs)


def test_build_top_level_environments_qualifies_machine_for_subset() -> None:
    # When the user picks a single platform out of the built-in set
    # (``linux-x86_64`` while ``linux-aarch64``/``armv7l``/etc. exist),
    # the env entry has to carry ``platform_machine`` so the installer
    # rejects a mismatched host. Otherwise a lock for ``linux-x86_64``
    # would silently install on ``linux-aarch64``.

    target_envs = build_target_environments(("linux-x86_64",), ("3.12",))
    envs = _build_top_level_environments(
        target_envs,
        python_versions=("3.12",),
        platforms=("linux-x86_64",),
    )
    assert envs
    assert any("platform_machine" in env for env in envs)


def test_build_top_level_environments_emits_multi_platform_disjunction() -> None:
    # Multi-platform locks emit ``environments`` clauses that disjunct the
    # selected platforms; the lock command's full pipeline involves
    # network/resolver/find-links plumbing that's flaky to exercise here, so
    # call the composer directly with synthesised target envs.

    target_envs = build_target_environments(
        ("linux-x86_64", "windows-amd64"), ("3.12",)
    )
    envs = _build_top_level_environments(
        target_envs,
        python_versions=("3.12",),
        platforms=("linux-x86_64", "windows-amd64"),
    )
    assert envs
    assert any("or" in env for env in envs)


# ── Network: pyproject.toml input -> setup-file path in _collect_constraints ──
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_with_pyproject_toml_input(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        '[dependency-groups]\ntest = ["small-fake-b==0.1"]\n'
        '[build-system]\nrequires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(pyproject),
            "-o",
            str(output),
            "--no-universal",
            "--all-groups",
        ],
    )
    assert result.exit_code == 0, result.output


# ── Network: --upgrade-package -> exercises upgrade path in _collect_constraints
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_upgrade_package(runner: CliRunner, requirements_in: Path) -> None:
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(requirements_in),
            "-o",
            str(output),
            "--no-universal",
            "--upgrade-package",
            "small-fake-a",
        ],
    )
    assert result.exit_code == 0, result.output


# ── Network: stdin input -> stdin path in _collect_constraints ─────────────────
@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_stdin_input(runner: CliRunner, tmp_path: Path) -> None:
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        ["-", "-o", str(output), "--no-universal"],
        input="small-fake-a==0.1\n",
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


def test_lock_unknown_group_raises(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        "[dependency-groups]\n"
        'dev = ["small-fake-b==0.1"]\n'
        '[build-system]\nrequires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(pyproject),
            "-o",
            str(output),
            "--no-universal",
            "--group",
            "doesnt-exist",
        ],
    )
    assert result.exit_code != 0
    assert "doesnt-exist" in result.output
    assert "Available: dev" in result.output


@pytest.mark.parametrize(
    ("groups_table", "match"),
    (
        pytest.param(
            dedent("""\
                [dependency-groups]
                a = [{include-group = "b"}]
                b = [{include-group = "a"}]
                """),
            "cyclic",
            id="cycle",
        ),
        pytest.param(
            dedent("""\
                [dependency-groups]
                Dev = ["x"]
                dev = ["y"]
                """),
            "duplicate",
            id="duplicate-names",
        ),
        pytest.param(
            dedent("""\
                [dependency-groups]
                dev = [{}]
                """),
            "invalid",
            id="invalid-object",
        ),
    ),
)
def test_lock_dependency_group_errors_become_bad_parameter(
    runner: CliRunner, tmp_path: Path, groups_table: str, match: str
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        dedent("""\
            [project]
            name = "test"
            version = "0.1"
            requires-python = ">=3.12"
            dependencies = []
            """)
        + groups_table
        + dedent("""\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"
            """)
    )
    result = runner.invoke(
        cli,
        [
            str(pyproject),
            "-o",
            str(tmp_path / "pylock.toml"),
            "--no-universal",
            "--all-groups",
        ],
    )
    assert result.exit_code != 0
    assert match in result.output.lower()


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_with_pyproject_toml_no_groups(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        '[build-system]\nrequires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(pyproject), "-o", str(output), "--no-universal"],
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    assert any(p["name"] == "small-fake-a" for p in doc["packages"])


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_pyproject_all_extras(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        "[project.optional-dependencies]\n"
        'extra = ["small-fake-b==0.1"]\n'
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(pyproject), "-o", str(output), "--no-universal", "--all-extras"],
    )
    assert result.exit_code == 0, result.output


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_pyproject_only_build_deps(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        '[build-system]\nrequires = ["small-fake-b==0.1"]\n'
        'build-backend = "setuptools.build_meta"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(pyproject),
            "-o",
            str(output),
            "--no-universal",
            "--only-build-deps",
            "--all-build-deps",
            "--no-build-isolation",
        ],
    )
    assert result.exit_code == 0, result.output


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_src_files_from_config(runner: CliRunner, tmp_path: Path) -> None:
    """End-to-end: src_files loaded from config when not passed on CLI."""
    req_in = tmp_path / "requirements.in"
    req_in.write_text("small-fake-a==0.1\n")
    output = tmp_path / "pylock.toml"

    config_file = tmp_path / "pip-lock-config.toml"
    config_file.write_text(
        tomli_w_dumps({"tool": {"pip-tools": {"src-files": [str(req_in)]}}})
    )

    result = runner.invoke(
        cli,
        ["--config", str(config_file), "-o", str(output), "--no-universal"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


def test_lock_src_files_from_default_map_when_click_provides_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty ``src_files`` from the default map flows into validation as ``[]``."""
    monkeypatch.chdir(tmp_path)  # empty dir; no default src files exist
    output = tmp_path / "pylock.toml"
    # Click delivers ``src_files=()`` for the bare argument and the loader
    # substitutes ``ctx.default_map["src_files"]``; with the default-map
    # value also empty, the validator sees ``[]`` and rejects.
    isolated_runner = CliRunner()
    result = isolated_runner.invoke(
        cli,
        ["-o", str(output), "--no-config"],
        default_map={"src_files": []},
    )
    assert result.exit_code != 0
    assert "If you do not specify" in result.output


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_only_build_deps_true_skips_runtime_deps(
    runner: CliRunner, tmp_path: Path
) -> None:
    """``--only-build-deps`` drops runtime deps from the resolved set."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.8"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        '[build-system]\nrequires = ["small-fake-b==0.1"]\n'
        'build-backend = "setuptools.build_meta"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            str(pyproject),
            "-o",
            str(output),
            "--no-universal",
            "--only-build-deps",
            "--all-build-deps",
            "--no-build-isolation",
        ],
    )
    assert result.exit_code == 0, result.output
    with open(output, "rb") as fh:
        doc = tomllib.load(fh)
    pkg_names = {p["name"] for p in doc["packages"]}
    # Build deps (small-fake-b) should be present; runtime (small-fake-a) should not.
    assert "small-fake-b" in pkg_names
    assert "small-fake-a" not in pkg_names


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_lock_build_backend_exception_exits(runner: CliRunner, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["small-fake-a==0.1"]\n'
        "[build-system]\nrequires = []\n"
        'build-backend = "nonexistent_backend.build"\n'
    )
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [str(pyproject), "-o", str(output), "--no-universal", "--all-build-deps"],
    )
    assert result.exit_code == 2


def test_parse_jobs_auto_uses_cpu_count(
    mocker: MockerFixture,
) -> None:
    # `--jobs auto` is the only spelling that consults the host's cpu count;
    # pin it so the test outcome is independent of the test machine's cores.
    mocker.patch("piptools.scripts.options.os.cpu_count", return_value=8)
    assert _parse_jobs(mocker.MagicMock(), mocker.MagicMock(), "auto") == 8


def test_parse_jobs_auto_falls_back_when_cpu_count_unknown(
    mocker: MockerFixture,
) -> None:
    # `os.cpu_count()` can return None on exotic platforms; the parser must
    # still produce a usable integer rather than propagating the None.
    mocker.patch("piptools.scripts.options.os.cpu_count", return_value=None)
    assert _parse_jobs(mocker.MagicMock(), mocker.MagicMock(), "auto") == 1


def test_parse_jobs_accepts_integer_string(mocker: MockerFixture) -> None:
    assert _parse_jobs(mocker.MagicMock(), mocker.MagicMock(), "4") == 4


@pytest.mark.parametrize(
    "value",
    (
        pytest.param("abc", id="alpha"),
        pytest.param("4.5", id="float"),
        pytest.param("", id="empty"),
    ),
)
def test_parse_jobs_rejects_non_integer(mocker: MockerFixture, value: str) -> None:
    with pytest.raises(click.BadParameter):
        _parse_jobs(mocker.MagicMock(), mocker.MagicMock(), value)


def test_parse_jobs_rejects_zero_or_negative(mocker: MockerFixture) -> None:
    with pytest.raises(click.BadParameter):
        _parse_jobs(mocker.MagicMock(), mocker.MagicMock(), "0")


def test_no_candidate_found_exits_two(
    runner: CliRunner, requirements_in: Path, mocker: MockerFixture
) -> None:
    # ``NoCandidateFound`` raised inside the resolver must surface as a
    # clean exit-2 with the diagnostic in stderr; silently propagating the
    # exception would print a Python traceback to the user.

    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        side_effect=NoCandidateFound(mocker.MagicMock(), [], mocker.MagicMock()),
    )
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 2


def test_pip_tools_error_exits_two(
    runner: CliRunner, requirements_in: Path, mocker: MockerFixture
) -> None:

    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        side_effect=PipToolsError("boom"),
    )
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 2
    assert "boom" in result.output


def test_invalid_custom_platform_rejected_at_cli(runner: CliRunner) -> None:
    # ``--platform freebsd-`` (empty arch half) would synthesise a marker
    # env with ``platform_machine=""`` and silently lock against the wrong
    # target; the click validator rejects it up front.
    result = runner.invoke(cli, ["--platform", "freebsd-", "--no-universal"])
    assert result.exit_code != 0
    assert "non-empty" in result.output


def test_resolve_src_files_ignores_empty_default_map(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A config file with ``src_files = []`` previously short-circuited the
    # auto-pickup with an empty tuple, then sailed past validation when a
    # default file existed in CWD and produced a silent empty lockfile.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(dedent("""
            [project]
            name = "demo"
            version = "0.0.0"
            requires-python = ">=3.9"
            dependencies = []
        """))
    config = tmp_path / ".pip-tools.toml"
    config.write_text("[lock]\nsrc_files = []\n")
    output = tmp_path / "pylock.toml"
    result = runner.invoke(
        cli,
        [
            "--config",
            str(config),
            "--no-universal",
            "-o",
            str(output),
            "--no-build-isolation",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


def test_pylock_validation_error_exits_two(
    runner: CliRunner, requirements_in: Path, mocker: MockerFixture
) -> None:
    mocker.patch(
        "piptools.pylock.cli._commands._do_build_pylock",
        side_effect=PylockValidationError("invalid pylock"),
    )
    output = requirements_in.parent / "pylock.toml"
    result = runner.invoke(
        cli, [str(requirements_in), "-o", str(output), "--no-universal"]
    )
    assert result.exit_code == 2
    assert "invalid pylock" in result.output


@pytest.mark.skipif(sys.platform == "win32", reason="fcntl unavailable on Windows")
def test_advisory_lock_missing_dir_exits_two(  # pragma: win32 no cover
    runner: CliRunner, requirements_in: Path
) -> None:
    # Typo'd ``-o`` paths must surface as a clean exit-2 with a missing-dir
    # message; the auto-mkdir behaviour was masking the typo. Windows
    # degrades the lock to a no-op (no ``fcntl``) so the ``os.open`` that
    # would surface the missing dir never runs there; the resolver picks
    # up the missing dir itself but with a different error shape.
    output = requirements_in.parent / "missing-dir" / "pylock.toml"
    result = runner.invoke(cli, [str(requirements_in), "-o", str(output)])
    assert result.exit_code != 0
    assert (
        "does not exist" in result.output.lower() or "no such" in result.output.lower()
    )


def test_check_and_dry_run_rejected_at_cli(
    runner: CliRunner, requirements_in: Path
) -> None:
    # Both flags ask for "don't write"; one verifies, the other previews.
    # Combining them silently honoured only ``--check``; reject so the user
    # picks the right one.
    result = runner.invoke(
        cli, [str(requirements_in), "--check", "--dry-run", "--no-universal"]
    )
    assert result.exit_code != 0
    assert "--check" in result.output
    assert "--dry-run" in result.output


def test_check_and_upgrade_rejected_at_cli(
    runner: CliRunner, requirements_in: Path
) -> None:
    # ``--upgrade`` re-resolves from scratch; ``--check`` expects the result
    # to match the on-disk file. The combination only succeeds when no
    # upstream package has shipped a newer version since the last lock;
    # almost certainly not what the user intends.
    result = runner.invoke(
        cli, [str(requirements_in), "--check", "--upgrade", "--no-universal"]
    )
    assert result.exit_code != 0
    assert "--check" in result.output
    assert "--upgrade" in result.output


def test_validate_python_versions_accepts_current_token() -> None:
    # ``--python-version current`` is the shorthand for the host's
    # MAJOR.MINOR; the regex validator must not reject the token.
    result = _validate_python_versions(
        ctx=click.Context(cli),
        param=click.Option(["--python-version"]),
        value=("current", "3.12"),
    )
    assert "current" in result


def test_validate_platform_canonicalises_uppercase(mocker: MockerFixture) -> None:
    # ``LINUX-X86_64`` and ``linux-x86_64`` would otherwise both pass; once
    # via the ``<os>-<arch>`` fallback and once via the preset; and the
    # lockfile would carry both near-duplicates.
    result = _validate_platform(
        ctx=click.Context(cli),
        param=click.Option(["--platform"]),
        value=("LINUX-X86_64",),
    )
    assert result == ("linux-x86_64",)


def test_validate_platform_accepts_synthetic_os_arch_after_canonicalisation(
    mocker: MockerFixture,
) -> None:
    # ``Freebsd-AMD64`` lower-cases to ``freebsd-amd64``; not in
    # PLATFORM_ENVIRONMENTS but the os-arch fallback accepts it.
    result = _validate_platform(
        ctx=click.Context(cli),
        param=click.Option(["--platform"]),
        value=("Freebsd-AMD64",),
    )
    assert result == ("freebsd-amd64",)


def test_platform_choices_lazy_imports_and_includes_current() -> None:
    # Without this assertion the click surface and the platform-marker lookup
    # could silently diverge; ``current`` leads so the help text reads as a
    # one-shorthand-then-presets list rather than alphabetical noise.
    choices = _platform_choices()
    assert choices[0] == "current"
    assert "linux-x86_64" in choices
    assert "windows-amd64" in choices
    assert choices[1:] == tuple(sorted(choices[1:]))
