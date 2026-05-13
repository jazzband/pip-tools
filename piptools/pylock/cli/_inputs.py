"""Collect resolver inputs from CLI-supplied source files and constraints.

Walks ``src_files``, expands setup-style metadata via the build backend,
threads constraint files in, and bolts ``--upgrade-package`` overrides
on top before the resolver consumes the union.
"""

from __future__ import annotations

import sys
from itertools import chain
from os.path import abspath, basename, exists
from pathlib import Path

from build import BuildBackendException
from click import BadParameter, Context
from pip._internal.req import InstallRequirement

from ..._compat import canonicalize_name, parse_requirements, tempfile_compat
from ..._internal import _pip_api
from ...build import ProjectMetadata, build_project_metadata
from ...logging import log
from ...repositories import PyPIRepository
from ...scripts.options import BuildTargetT
from ...utils import dedup, key_from_ireq
from ._validation import DEFAULT_REQUIREMENTS_FILES

_METADATA_FILENAMES: frozenset[str] = frozenset(
    {"setup.py", "setup.cfg", "pyproject.toml"}
)


def resolve_src_files(
    click_context: Context, src_files: tuple[str, ...]
) -> tuple[str, ...]:
    """Return the input files to lock against.

    Honours an explicit CLI value first, then a configured default-map value,
    then falls back to the first existing default requirements file in the
    current working directory.

    :param click_context: The click context whose default-map carries
        configuration-supplied values.
    :param src_files: Files supplied on the command line (possibly empty).
    :returns: The files to feed to the resolver, possibly empty when no
        defaults exist.
    """
    if src_files:
        return src_files
    # Truthy check on the default-map value: a config file with
    # ``src_files = []`` would short-circuit auto-pickup with an empty
    # tuple, then sail past validation when a default file exists in
    # CWD and produce an empty lockfile.
    if click_context.default_map and (
        configured := click_context.default_map.get("src_files")
    ):
        return tuple(configured)
    # ``--help`` advertises auto-pickup ("$ pip-lock # reads pyproject.toml");
    # without substituting the first existing default file, the resolver
    # iterates an empty input set and emits an empty lockfile that looks
    # valid.
    for file_path in DEFAULT_REQUIREMENTS_FILES:
        if exists(file_path):
            return (file_path,)
    return src_files


def build_constraints(
    *,
    repository: PyPIRepository,
    src_files: tuple[str, ...],
    constraint: tuple[str, ...],
    build_deps_targets: tuple[BuildTargetT, ...],
    only_build_deps: bool,
    all_extras: bool,
    extras: tuple[str, ...],
    build_isolation: bool,
    upgrade_packages: tuple[str, ...],
) -> tuple[list[InstallRequirement], tuple[str, ...], tuple[str, ...]]:
    """Collect resolver constraints from source files and the CLI flags.

    Threads requirements files, project metadata, constraint files, and
    upgrade-package overrides into one list the resolver consumes.
    Canonicalises and deduplicates extras at the input boundary.

    :param repository: Index-backed source needed by pip's requirement parser.
    :param src_files: Requirements or project metadata files to read.
    :param constraint: Constraint files to thread in alongside ``src_files``.
    :param build_deps_targets: Build-target labels to expand (PEP 517 hooks).
    :param only_build_deps: Skip runtime requirements when true.
    :param all_extras: Pull every extra from the project metadata.
    :param extras: Extras explicitly requested on the command line.
    :param build_isolation: Whether to invoke build backends in isolation.
    :param upgrade_packages: Pin overrides supplied via ``--upgrade-package``.
    :returns: A triple of ``(constraints, normalised extras, project requires-python strings)``.
    :raises click.BadParameter: When extras are requested without a project metadata input.
    :raises SystemExit: When a project metadata backend fails to expand.
    """
    # ``upgrade_packages`` runs through two passes on purpose. The first pass
    # adds them as primary requirements so a name that the project never
    # pinned still shows up in the lock. ``_collect_constraints`` runs the
    # second pass and threads the same names in as ``-c``-shaped bindings so
    # an existing pin yields to the override. A single pass would skip
    # never-pinned upgrades or leave already-pinned ones untouched.
    upgrade_install_reqs = {
        key_from_ireq(
            ireq := _pip_api.create_install_requirement_from_line(package)
        ): ireq
        for package in upgrade_packages
    }
    raw_constraints, extras, project_specifiers = _collect_constraints(
        src_files=src_files,
        constraint_files=constraint,
        repository=repository,
        build_deps_targets=build_deps_targets,
        only_build_deps=only_build_deps,
        all_extras=all_extras,
        extras=extras,
        build_isolation=build_isolation,
        upgrade_packages=upgrade_packages,
    )
    # Canonicalise at the input boundary: without this, ``--extra Foo --extra foo``
    # survives as two distinct entries until the output layer collapses them,
    # doubling per-extra resolutions in between.
    extras = tuple(
        dedup(
            canonicalize_name(e)
            for e in chain.from_iterable(ex.split(",") for ex in extras)
        )
    )
    setup_file_found = any(basename(src) in _METADATA_FILENAMES for src in src_files)
    if extras and not setup_file_found:
        raise BadParameter(
            "--extra requires a project metadata file as input "
            "(setup.py, setup.cfg, or pyproject.toml)"
        )
    primary_packages = {
        key_from_ireq(ireq) for ireq in raw_constraints if not ireq.constraint
    }
    raw_constraints.extend(
        ireq for key, ireq in upgrade_install_reqs.items() if key in primary_packages
    )
    return raw_constraints, extras, project_specifiers


def _collect_constraints(
    src_files: tuple[str, ...],
    constraint_files: tuple[str, ...],
    repository: PyPIRepository,
    build_deps_targets: tuple[BuildTargetT, ...],
    only_build_deps: bool,
    all_extras: bool,
    extras: tuple[str, ...],
    build_isolation: bool,
    upgrade_packages: tuple[str, ...],
) -> tuple[list[InstallRequirement], tuple[str, ...], tuple[str, ...]]:
    constraints: list[InstallRequirement] = []
    project_specifiers: list[str] = []
    for src_file in src_files:
        is_setup_file = basename(src_file) in _METADATA_FILENAMES
        if not is_setup_file and build_deps_targets:
            raise BadParameter(
                "--build-deps-for and --all-build-deps can be used only with the "
                "setup.py, setup.cfg and pyproject.toml specs."
            )

        if src_file == "-":
            with tempfile_compat.named_temp_file() as tmpfile:
                tmpfile.write(sys.stdin.read())
                tmpfile.flush()
                reqs = list(
                    parse_requirements(
                        tmpfile.name,
                        finder=repository.finder,
                        session=repository.session,
                        options=repository.options,
                        comes_from_stdin=True,
                    )
                )
            constraints.extend(reqs)
        elif is_setup_file:
            try:
                metadata = build_project_metadata(
                    src_file=Path(src_file),
                    build_targets=build_deps_targets,
                    upgrade_packages=upgrade_packages,
                    attempt_static_parse=not bool(build_deps_targets),
                    isolated=build_isolation,
                    quiet=log.verbosity <= 0,
                )
            except BuildBackendException as e:
                log.error(str(e))
                log.error(f"Failed to parse {abspath(src_file)}")
                raise SystemExit(2) from e

            if not only_build_deps:
                constraints.extend(metadata.requirements)
                if all_extras:
                    extras += metadata.extras  # noqa: PLW2901
            if metadata.requires_python:
                project_specifiers.append(metadata.requires_python)
            if build_deps_targets:
                assert isinstance(metadata, ProjectMetadata)
                constraints.extend(metadata.build_requirements)
        else:
            constraints.extend(
                parse_requirements(
                    src_file,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                )
            )

    constraints.extend(
        chain.from_iterable(
            parse_requirements(
                filename,
                constraint=True,
                finder=repository.finder,
                options=repository.options,
                session=repository.session,
            )
            for filename in constraint_files
        )
    )

    if upgrade_packages:
        with tempfile_compat.named_temp_file() as constraints_file:
            constraints_file.write("\n".join(upgrade_packages))
            constraints_file.flush()
            reqs = list(
                parse_requirements(
                    constraints_file.name,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                    constraint=True,
                )
            )
            for req in reqs:
                req.comes_from = None
        constraints.extend(reqs)

    return constraints, extras, tuple(project_specifiers)


__all__ = [
    "build_constraints",
    "resolve_src_files",
]
