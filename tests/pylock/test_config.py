from __future__ import annotations

from pathlib import Path

import pytest

from piptools.exceptions import PipToolsError
from piptools.pylock.config import (
    ConflictItem,
    build_extras_configs,
    build_group_configs,
    extract_conflicts,
    extract_requires_python,
    load_default_groups,
    load_dependency_groups_table,
)


def test_build_extras_configs_no_conflicts() -> None:
    # Non-conflicting extras coexist in a single combined pass; the
    # one-pass-per-extra cost is what this collapse exists to avoid.
    configs = build_extras_configs(extras=("http", "graphql"), conflicts=[])
    assert configs == [(None, ("http", "graphql"))]


def test_build_extras_configs_with_conflicts() -> None:
    conflicts = [
        [
            ConflictItem(kind="extra", name="gpu"),
            ConflictItem(kind="extra", name="cpu"),
        ],
    ]
    configs = build_extras_configs(extras=("http", "gpu", "cpu"), conflicts=conflicts)

    base_label, base_extras = configs[0]
    assert base_label is None
    # Non-conflicting extras (http) ride along in the combined base pass;
    # the conflicting extras each get their own variant alongside.
    assert base_extras == ("http",)

    gpu_config = next(c for c in configs if c[0] == "gpu")
    assert "gpu" in gpu_config[1]
    assert "http" in gpu_config[1]
    assert "cpu" not in gpu_config[1]

    cpu_config = next(c for c in configs if c[0] == "cpu")
    assert "cpu" in cpu_config[1]
    assert "http" in cpu_config[1]
    assert "gpu" not in cpu_config[1]


def test_build_extras_configs_no_extras() -> None:
    configs = build_extras_configs(extras=(), conflicts=[])
    assert configs == [(None, ())]


@pytest.mark.parametrize(
    ("toml_content", "expected"),
    (
        pytest.param('[project]\nrequires-python = ">=3.10"\n', ">=3.10", id="found"),
        pytest.param('[project]\nname = "test"\n', None, id="missing-key"),
    ),
)
def test_extract_requires_python(
    tmp_path: Path, toml_content: str, expected: str | None
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(toml_content)
    assert extract_requires_python((str(pyproject),)) == expected


def test_extract_requires_python_no_pyproject() -> None:
    assert extract_requires_python(("requirements.in",)) is None


def test_extract_requires_python_skips_non_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.12"\n')
    assert extract_requires_python(("setup.cfg", str(pyproject))) == ">=3.12"


def test_extract_requires_python_intersects_multiple_pyprojects(
    tmp_path: Path,
) -> None:
    project_a = tmp_path / "a" / "pyproject.toml"
    project_a.parent.mkdir()
    project_a.write_text('[project]\nrequires-python = ">=3.9"\n')
    project_b = tmp_path / "b" / "pyproject.toml"
    project_b.parent.mkdir()
    project_b.write_text('[project]\nrequires-python = ">=3.10"\n')
    combined = extract_requires_python((str(project_a), str(project_b)))
    assert combined is not None
    assert ">=3.9" in combined
    assert ">=3.10" in combined


def test_extract_requires_python_uses_metadata_specifiers_fallback(
    tmp_path: Path,
) -> None:
    # ``setup.cfg`` carries ``python_requires`` for setuptools-style projects;
    # the static ``pyproject.toml`` read can't see it, so the bound has to flow
    # in via ``metadata_specifiers`` from ``build_project_metadata``. Without
    # that backend-agnostic path the lockfile loses the lower bound for any
    # project that hasn't migrated to ``[project]`` yet.
    setup_cfg = tmp_path / "setup.cfg"
    setup_cfg.write_text("[options]\npython_requires = >=3.10\n")
    assert (
        extract_requires_python(
            (str(setup_cfg),),
            metadata_specifiers=(">=3.10",),
        )
        == ">=3.10"
    )


def test_extract_requires_python_prefers_static_pyproject_over_metadata(
    tmp_path: Path,
) -> None:
    # The static read is a perf optimization; if pyproject.toml carries the
    # bound, intersecting with the same value from metadata is idempotent and
    # produces the same result whether the backend ran or not.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.11"\n')
    assert (
        extract_requires_python(
            (str(pyproject),),
            metadata_specifiers=(">=3.11",),
        )
        == ">=3.11"
    )


def test_extract_requires_python_skips_invalid_specifier(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = "not-a-specifier"\n')
    assert extract_requires_python((str(pyproject),)) is None


@pytest.mark.parametrize(
    ("pyproject_spec", "python_versions", "expected_substrings"),
    (
        pytest.param(
            ">=3.9",
            ("3.12", "3.13"),
            (">=3.9", ">=3.12"),
            id="cli-floor-tighter-than-pyproject",
        ),
        pytest.param(
            ">=3.13",
            ("3.12", "3.13"),
            (">=3.13", ">=3.12"),
            id="pyproject-floor-tighter-than-cli",
        ),
        pytest.param(
            ">=3.9",
            ("3.12.5",),
            (">=3.9", ">=3.12.5"),
            id="patch-component-preserved",
        ),
    ),
)
def test_extract_requires_python_intersects_with_cli_versions(
    tmp_path: Path,
    pyproject_spec: str,
    python_versions: tuple[str, ...],
    expected_substrings: tuple[str, ...],
) -> None:
    # PEP 751's top-level ``requires-python`` is the lockfile-wide floor; if
    # ``--python-version 3.12`` constrains the lock, the floor must reflect
    # that or a 3.10 installer passes the top-level check then fails every
    # per-package check.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f'[project]\nrequires-python = "{pyproject_spec}"\n')
    result = extract_requires_python((str(pyproject),), python_versions)
    assert result is not None
    for substr in expected_substrings:
        assert substr in result


def test_extract_requires_python_with_cli_versions_only(tmp_path: Path) -> None:
    # ``--python-version`` should still produce a floor when no ``pyproject``
    # is present; otherwise the lockfile would emit no ``requires-python``,
    # and the spec's "lowest viable Python" guarantee would not hold.
    result = extract_requires_python((), ("3.12", "3.13"))
    assert result == ">=3.12"


def test_extract_conflicts_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.pip-tools]\n"
        "conflicts = [\n"
        '    [{extra = "gpu"}, {extra = "cpu"}],\n'
        '    [{extra = "a"}, {extra = "b"}, {extra = "c"}],\n'
        "]\n"
    )
    result = extract_conflicts((str(pyproject),))
    assert len(result) == 2
    assert result[0] == [
        ConflictItem(kind="extra", name="gpu"),
        ConflictItem(kind="extra", name="cpu"),
    ]
    assert len(result[1]) == 3


@pytest.mark.parametrize(
    ("toml_content", "src_files_suffix"),
    (
        pytest.param(
            '[project]\nname = "test"\n', "pyproject.toml", id="no-pip-tools-section"
        ),
        pytest.param("", "requirements.in", id="non-pyproject-file"),
    ),
)
def test_extract_conflicts_returns_empty(
    tmp_path: Path, toml_content: str, src_files_suffix: str
) -> None:
    f = tmp_path / src_files_suffix
    f.write_text(toml_content)
    assert extract_conflicts((str(f),)) == []


def test_extract_conflicts_skips_items_without_extra_or_group(
    tmp_path: Path,
) -> None:
    # An empty inline table has no unknown keys to raise on, yet nothing to
    # contribute; silently dropping it keeps user input forward-compatible.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.pip-tools]\n"
        "conflicts = [\n"
        '    [{extra = "gpu"}, {}, {extra = "cpu"}],\n'
        "]\n"
    )
    result = extract_conflicts((str(pyproject),))
    assert result == [
        [
            ConflictItem(kind="extra", name="gpu"),
            ConflictItem(kind="extra", name="cpu"),
        ]
    ]


def test_extract_conflicts_with_groups(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.pip-tools]\n"
        "conflicts = [\n"
        '    [{group = "black22"}, {group = "black24"}],\n'
        "]\n"
    )
    result = extract_conflicts((str(pyproject),))
    assert result == [
        [
            ConflictItem(kind="group", name="black22"),
            ConflictItem(kind="group", name="black24"),
        ]
    ]


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    (
        pytest.param(
            "pyproject.toml",
            '[dependency-groups]\ntest = ["pytest"]\ndefault-groups = ["test"]\n',
            ("test",),
            id="single-default",
        ),
        pytest.param(
            "pyproject.toml",
            '[dependency-groups]\ntest = ["pytest"]\nlint = ["ruff"]\n'
            'default-groups = ["test", "lint"]\n',
            ("test", "lint"),
            id="multiple-defaults",
        ),
        pytest.param(
            "pyproject.toml",
            '[dependency-groups]\ntest = ["pytest"]\n',
            (),
            id="missing-key",
        ),
        pytest.param(
            "pyproject.toml",
            '[dependency-groups]\ntest = ["pytest"]\ndefault-groups = "test"\n',
            (),
            id="non-list-value-ignored",
        ),
        pytest.param("requirements.in", "", (), id="non-pyproject-file"),
    ),
)
def test_load_default_groups(
    tmp_path: Path, filename: str, content: str, expected: tuple[str, ...]
) -> None:
    src = tmp_path / filename
    src.write_text(content)
    assert load_default_groups((str(src),)) == expected


def test_load_dependency_groups_table_strips_default_groups_key(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[dependency-groups]\ntest = ["pytest"]\ndefault-groups = ["test"]\n'
    )
    result = load_dependency_groups_table((str(pyproject),))
    assert "default-groups" not in result
    assert result == {"test": ["pytest"]}


def test_load_dependency_groups_table_basic(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[dependency-groups]\ntest = ["pytest>=8", "coverage"]\ndev = ["black"]\n'
    )
    result = load_dependency_groups_table((str(pyproject),))
    assert result == {"test": ["pytest>=8", "coverage"], "dev": ["black"]}


def test_load_dependency_groups_table_preserves_includes(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[dependency-groups]\n"
        'base = ["requests"]\n'
        'extra = [{include-group = "base"}, "httpx"]\n'
    )
    result = load_dependency_groups_table((str(pyproject),))
    assert result["extra"] == [{"include-group": "base"}, "httpx"]


@pytest.mark.parametrize(
    ("filename", "content"),
    (
        pytest.param("pyproject.toml", '[project]\nname = "test"\n', id="no-section"),
        pytest.param("requirements.in", "pytest\n", id="non-pyproject"),
        pytest.param("pyproject.toml", "not valid toml [[[", id="invalid-toml"),
    ),
)
def test_load_dependency_groups_table_returns_empty(
    tmp_path: Path, filename: str, content: str
) -> None:
    src = tmp_path / filename
    src.write_text(content)
    assert load_dependency_groups_table((str(src),)) == {}


@pytest.mark.parametrize(
    ("groups", "expected"),
    (
        pytest.param(
            ("test", "dev"),
            [(None, ()), ("test", ("test",)), ("dev", ("dev",))],
            id="with-groups",
        ),
        pytest.param((), [(None, ())], id="no-groups"),
    ),
)
def test_build_group_configs_no_conflicts(
    groups: tuple[str, ...], expected: list[tuple[str | None, tuple[str, ...]]]
) -> None:
    assert build_group_configs(groups=groups, conflicts=[]) == expected


def test_build_group_configs_with_conflicts() -> None:
    conflicts = [
        [
            ConflictItem(kind="group", name="black22"),
            ConflictItem(kind="group", name="black24"),
        ]
    ]
    configs = build_group_configs(
        groups=("test", "black22", "black24"), conflicts=conflicts
    )

    base_label, base_groups = configs[0]
    assert base_label is None
    assert base_groups == ()

    black22_config = next(conf for conf in configs if conf[0] == "black22")
    assert "black22" in black22_config[1]
    assert "test" in black22_config[1]
    assert "black24" not in black22_config[1]

    black24_config = next(conf for conf in configs if conf[0] == "black24")
    assert "black24" in black24_config[1]
    assert "test" in black24_config[1]
    assert "black22" not in black24_config[1]


@pytest.mark.parametrize(
    "content",
    (
        pytest.param("not valid toml [[[", id="invalid-toml"),
        pytest.param(
            '[tool.pip-tools]\nconflicts = [\n    [{extra = "only-one"}],\n]\n',
            id="group-with-single-item",
        ),
    ),
)
def test_extract_conflicts_returns_empty_for_edge_cases(
    tmp_path: Path, content: str
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content)
    assert extract_conflicts((str(pyproject),)) == []


def test_extract_conflicts_raises_on_unknown_key(tmp_path: Path) -> None:
    # A typo'd ``extras = "..."`` (plural) needs to surface as an error
    # rather than be silently dropped: a silent drop would leave the user
    # to discover the issue only when the disjointness check later
    # rejects the lock.

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.pip-tools]\nconflicts = [\n    [{extras = "foo"}, {extra = "bar"}],\n]\n'
    )
    with pytest.raises(PipToolsError, match="unknown key"):
        extract_conflicts((str(pyproject),))


def test_load_dependency_groups_table_keeps_unknown_dict_items(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[dependency-groups]\ntest = [{some-other-key = "value"}, "pytest"]\n'
    )
    result = load_dependency_groups_table((str(pyproject),))
    assert result["test"] == [{"some-other-key": "value"}, "pytest"]


def test_extract_requires_python_invalid_toml(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("not valid toml [[[")
    assert extract_requires_python((str(pyproject),)) is None


def test_build_extras_configs_non_extra_conflict_items_ignored() -> None:
    conflicts = [
        [
            ConflictItem(kind="group", name="test"),
            ConflictItem(kind="group", name="dev"),
        ]
    ]
    configs = build_extras_configs(extras=("http",), conflicts=conflicts)
    # Group-only conflicts don't make any extra "conflicting", so http
    # rides in the combined base pass; same shape as the no-conflicts case.
    assert configs == [(None, ("http",))]


def test_extract_requires_python_accepts_python1(tmp_path: Path) -> None:
    # The emptiness probe must not false-positive on legacy pins like
    # ``==1.5.0``; the grid covers Python 1-4 so any genuine release falls
    # inside it; rejecting it here would block locking a legacy codebase.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = "==1.5.0"\nname = "x"\n')
    result = extract_requires_python((str(pyproject),))
    assert result is not None
    assert "1.5.0" in result


def test_extract_requires_python_accepts_python4(tmp_path: Path) -> None:
    # Forward-looking ``==4.0.0`` pins must also pass the probe.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = "==4.0.0"\nname = "x"\n')
    result = extract_requires_python((str(pyproject),))
    assert result is not None
    assert "4.0.0" in result


def test_extract_requires_python_rejects_genuinely_empty(tmp_path: Path) -> None:
    # ``>=3.12,<3.10`` admits no release; the probe must still flag this.

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.12,<3.10"\nname = "x"\n')
    with pytest.raises(PipToolsError, match="empty"):
        extract_requires_python((str(pyproject),))


def test_extract_requires_python_skips_invalid_metadata_specifier(
    tmp_path: Path,
) -> None:
    # ``setup.cfg``-style projects can hand back a malformed ``Requires-Python``
    # via ``metadata_specifiers``; the ``InvalidSpecifier`` branch must skip
    # rather than raise so a single bad metadata read doesn't tank the lock.
    # An empty string in the list is also legal (backend may return ``""`` for
    # a project that declares dynamic metadata but doesn't set the field).
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.10"\n')
    result = extract_requires_python(
        (str(pyproject),),
        metadata_specifiers=("", "not-a-spec", ">=3.11"),
    )
    assert result is not None
    assert ">=3.11" in result


def test_extract_requires_python_skips_metadata_when_pyproject_invalid(
    tmp_path: Path,
) -> None:
    # Both pyproject and metadata can carry malformed specifiers; the static
    # read's ``InvalidSpecifier`` branch must skip too.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = "not-a-spec"\n')
    assert extract_requires_python((str(pyproject),)) is None
