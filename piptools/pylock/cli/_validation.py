"""Option validation for ``pip-lock``.

Owns the early ``BadParameter`` checks plus the helper that turns
a rejected ``--output-file`` into a PEP 751-valid suggestion. Colocating
both keeps the suggestion helper in the validator's error path.
"""

from __future__ import annotations

import typing as _t
from os.path import exists
from pathlib import Path
from re import Pattern
from re import compile as re_compile

from click import BadParameter
from click.utils import LazyFile
from packaging.pylock import is_valid_pylock_path

from ...scripts.options import BuildTargetT

DEFAULT_REQUIREMENTS_FILES: _t.Final[tuple[str, ...]] = (
    "requirements.in",
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
)

_PYLOCK_SLUG_SAFE: _t.Final[Pattern[str]] = re_compile(r"[^a-z0-9_-]+")


def validate_options(
    all_build_deps: bool,
    build_deps_targets: tuple[BuildTargetT, ...],
    only_build_deps: bool,
    extras: tuple[str, ...],
    all_extras: bool,
    src_files: tuple[str, ...],
    output_file: LazyFile | _t.IO[_t.Any] | None,
) -> None:
    """Reject CLI option combinations that contradict each other.

    :param all_build_deps: Whether ``--all-build-deps`` was supplied.
    :param build_deps_targets: Build-target labels supplied via ``--build-deps-for``.
    :param only_build_deps: Whether the user asked for build deps exclusively.
    :param extras: Explicit extras requested via ``--extra``.
    :param all_extras: Whether ``--all-extras`` was supplied.
    :param src_files: Source files to lock from.
    :param output_file: Configured output destination, possibly streaming.
    :raises click.BadParameter: When two flags conflict, when extras are requested
        without input metadata, or when the output filename violates PEP 751.
    """
    if all_build_deps and build_deps_targets:
        raise BadParameter(
            "--build-deps-for has no effect when used with --all-build-deps"
        )
    if only_build_deps and not (build_deps_targets or all_build_deps):
        raise BadParameter(
            "--only-build-deps requires either --build-deps-for or --all-build-deps"
        )
    if only_build_deps and (extras or all_extras):
        raise BadParameter(
            "--only-build-deps cannot be used with any of --extra, --all-extras"
        )
    if len(src_files) == 0 and not any(exists(p) for p in DEFAULT_REQUIREMENTS_FILES):
        # The caller (``cli``) substitutes the first existing default file
        # into ``src_files`` before reaching the resolver; without a default
        # to substitute, ``collect_constraints`` iterates an empty input
        # set and produces an empty lockfile that looks valid.
        raise BadParameter(
            "If you do not specify an input file, the default is one of: {}".format(
                ", ".join(DEFAULT_REQUIREMENTS_FILES)
            )
        )
    if all_extras and extras:
        raise BadParameter("--extra has no effect when used with --all-extras")
    if output_file and hasattr(output_file, "name"):
        # ``-`` / ``<stdout>`` mean "stream the lockfile to stdout"; PEP 751's
        # filename regex doesn't apply because they aren't on-disk paths.
        # Treat them as a valid output the same way ``--dry-run`` does,
        # so a user piping ``pip-lock -o - | tee pylock.toml`` works.
        if output_file.name not in {"-", "<stdout>"}:
            path = Path(output_file.name)
            if not is_valid_pylock_path(path):
                # PEP 751's regex separates ``pylock`` from the slug with ``.``,
                # not ``-``; spell that out so a user who typed
                # ``pylock-foo.toml`` sees the rule rather than guessing.
                raise BadParameter(
                    f"Output file name must match 'pylock.toml' or "
                    f"'pylock.*.toml' per PEP 751 (note the dot separator "
                    f"between 'pylock' and the slug, not a hyphen), got "
                    f"'{path.name}'. Try '{_pylock_suggestion(path)}'.",
                    param_hint="--output-file",
                )
    if not output_file:
        if src_files == ("-",):
            raise BadParameter("--output-file is required if input is from stdin")
        elif len(src_files) > 1:
            raise BadParameter(
                "--output-file is required if two or more input files are given."
            )


def _pylock_suggestion(path: Path) -> str:
    """Return a PEP 751-valid filename suggestion derived from ``path``.

    PEP 751's regex is ``^pylock\\.[a-z0-9_-]+\\.toml$``. A naive
    ``f"pylock.{stem}.toml"`` can produce multi-dot or uppercase output
    that re-trips the same check, so the stem is lowercased, every
    disallowed character is replaced with ``-``, the result is trimmed,
    and the candidate is re-validated before returning. Falls back to
    ``pylock.toml`` when nothing salvageable remains.
    """
    raw_stem = path.stem.removesuffix(".toml")
    slug = _PYLOCK_SLUG_SAFE.sub("-", raw_stem.lower()).strip("-")
    # Drop a redundant ``pylock-`` prefix the sanitiser introduces: a
    # multi-dot ``pylock.dev.extra.toml`` slugs to ``pylock-dev-extra``,
    # and emitting ``pylock.pylock-dev-extra.toml`` would double the
    # prefix.
    if slug.startswith("pylock-"):
        slug = slug[len("pylock-") :]
    if slug and slug != "pylock":
        return f"pylock.{slug}.toml"
    return "pylock.toml"


__all__ = [
    "DEFAULT_REQUIREMENTS_FILES",
    "validate_options",
]
