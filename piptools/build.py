from __future__ import annotations

import collections
import contextlib
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Any, Iterator, Protocol, TypeVar, overload

import build
import build.env
import pyproject_hooks
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import parse_req_from_line
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement

from .utils import copy_install_requirement, install_req_from_line

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PYPROJECT_TOML = "pyproject.toml"

_T = TypeVar("_T")


if sys.version_info >= (3, 10):
    from importlib.metadata import PackageMetadata
else:

    class PackageMetadata(Protocol):
        @overload
        def get_all(self, name: str, failobj: None = None) -> list[Any] | None: ...

        @overload
        def get_all(self, name: str, failobj: _T) -> list[Any] | _T: ...


@dataclass
class StaticProjectMetadata:
    extras: tuple[str, ...]
    requirements: tuple[InstallRequirement, ...]


@dataclass
class ProjectMetadata:
    extras: tuple[str, ...]
    requirements: tuple[InstallRequirement, ...]
    build_requirements: tuple[InstallRequirement, ...]


def maybe_statically_parse_project_metadata(
    src_file: pathlib.Path,
) -> StaticProjectMetadata | None:
    """
    Return the metadata for a project, if it can be statically parsed from ``pyproject.toml``.

    This function is typically significantly faster than invoking a build backend.
    Returns None if the project metadata cannot be statically parsed.
    """
    if src_file.name != PYPROJECT_TOML:
        return None

    try:
        with open(src_file, "rb") as f:
            pyproject_contents = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return None

    # Not valid PEP 621 metadata
    if (
        "project" not in pyproject_contents
        or "name" not in pyproject_contents["project"]
    ):
        return None

    project_table = pyproject_contents["project"]

    # Dynamic dependencies require build backend invocation
    dynamic = project_table.get("dynamic", [])
    if "dependencies" in dynamic or "optional-dependencies" in dynamic:
        return None

    package_name = project_table["name"]
    comes_from = f"{package_name} ({src_file})"

    extras = project_table.get("optional-dependencies", {}).keys()
    install_requirements = [
        InstallRequirement(Requirement(req), comes_from)
        for req in project_table.get("dependencies", [])
    ]
    for extra, reqs in (
        pyproject_contents.get("project", {}).get("optional-dependencies", {}).items()
    ):
        for req in reqs:
            requirement = Requirement(req)
            if requirement.name == package_name:
                # Similar to logic for handling self-referential requirements
                # from _prepare_requirements
                requirement.url = src_file.parent.as_uri()
            # Note we don't need to modify `requirement` to include this extra
            marker = Marker(f"extra == '{extra}'")
            install_requirements.append(
                InstallRequirement(requirement, comes_from, markers=marker)
            )

    return StaticProjectMetadata(
        extras=tuple(extras),
        requirements=tuple(install_requirements),
    )


def build_project_metadata(
    src_file: pathlib.Path,
    build_targets: tuple[str, ...],
    *,
    upgrade_packages: tuple[str, ...] | None = None,
    attempt_static_parse: bool,
    isolated: bool,
    quiet: bool,
) -> ProjectMetadata | StaticProjectMetadata:
    """
    Return the metadata for a project.

    First, optionally attempt to determine the metadata statically from the
    ``pyproject.toml`` file. This will not work if build_targets are specified,
    since we cannot determine build requirements statically.

    Uses the ``prepare_metadata_for_build_wheel`` hook for the wheel metadata
    if available, otherwise ``build_wheel``.

    Uses the ``prepare_metadata_for_build_{target}`` hook for each ``build_targets``
    if available.

    :param src_file: Project source file
    :param build_targets: A tuple of build targets to get the dependencies
                                of (``sdist`` or ``wheel`` or ``editable``).
    :param attempt_static_parse: Whether to attempt to statically parse the
                                 project metadata from ``pyproject.toml``.
                                 Cannot be used with ``build_targets``.
    :param isolated: Whether to run invoke the backend in the current
                     environment or to create an isolated one and invoke it
                     there.
    :param quiet: Whether to suppress the output of subprocesses.
    """

    if attempt_static_parse:
        if build_targets:
            raise ValueError(
                "Cannot execute the PEP 517 optional get_requires_for_build* "
                "hooks statically, as build requirements are requested"
            )
        project_metadata = maybe_statically_parse_project_metadata(src_file)
        if project_metadata is not None:
            return project_metadata

    src_dir = src_file.parent
    with _create_project_builder(
        src_dir,
        upgrade_packages=upgrade_packages,
        isolated=isolated,
        quiet=quiet,
    ) as builder:
        metadata = _build_project_wheel_metadata(builder)
        extras = tuple(metadata.get_all("Provides-Extra") or ())
        requirements = tuple(
            _prepare_requirements(metadata=metadata, src_file=src_file)
        )
        build_requirements = tuple(
            _prepare_build_requirements(
                builder=builder,
                src_file=src_file,
                build_targets=build_targets,
                package_name=_get_name(metadata),
            )
        )
        return ProjectMetadata(
            extras=extras,
            requirements=requirements,
            build_requirements=build_requirements,
        )


@contextlib.contextmanager
def _env_var(
    env_var_name: str,
    env_var_value: str,
    /,
) -> Iterator[None]:
    sentinel = object()
    original_pip_constraint = os.getenv(env_var_name, sentinel)
    pip_constraint_was_unset = original_pip_constraint is sentinel

    os.environ[env_var_name] = env_var_value
    try:
        yield
    finally:
        if pip_constraint_was_unset:
            del os.environ[env_var_name]
            return

        # Assert here is necessary because MyPy can't infer type
        # narrowing in the complex case.
        assert isinstance(original_pip_constraint, str)
        os.environ[env_var_name] = original_pip_constraint


@contextlib.contextmanager
def _temporary_constraints_file_set_for_pip(
    upgrade_packages: tuple[str, ...],
) -> Iterator[None]:
    with tempfile.NamedTemporaryFile(
        mode="w+t",
        delete=False,  # FIXME: switch to `delete_on_close` in Python 3.12+
    ) as tmpfile:
        # NOTE: `delete_on_close=False` here (or rather `delete=False`,
        # NOTE: temporarily) is important for cross-platform execution. It is
        # NOTE: required on Windows so that the underlying `pip install`
        # NOTE: invocation by pypa/build will be able to access the constraint
        # NOTE: file via a subprocess and not fail installing it due to a
        # NOTE: permission error related to this file handle still open in our
        # NOTE: parent process. To achieve this, we `.close()` the file
        # NOTE: descriptor before we hand off the control to the build frontend
        # NOTE: and with `delete_on_close=False`, the
        # NOTE: `tempfile.NamedTemporaryFile()` context manager does not remove
        # NOTE: it from disk right away.
        # NOTE: Due to support of versions below Python 3.12, we are forced to
        # NOTE: temporarily resort to using `delete=False`, meaning that the CM
        # NOTE: never attempts removing the file from disk, not even on exit.
        # NOTE: So we do this manually until we can migrate to using the more
        # NOTE: ergonomic argument `delete_on_close=False`.

        # Write packages to upgrade to a temporary file to set as
        # constraints for the installation to the builder environment,
        # in case build requirements are among them
        tmpfile.write("\n".join(upgrade_packages))

        # FIXME: replace `delete` with `delete_on_close` in Python 3.12+
        # FIXME: and replace `.close()` with `.flush()`
        tmpfile.close()

        try:
            with _env_var("PIP_CONSTRAINT", tmpfile.name):
                yield
        finally:
            # FIXME: replace `delete` with `delete_on_close` in Python 3.12+
            # FIXME: and drop this manual deletion
            os.unlink(tmpfile.name)


@contextlib.contextmanager
def _create_project_builder(
    src_dir: pathlib.Path,
    *,
    upgrade_packages: tuple[str, ...] | None = None,
    isolated: bool,
    quiet: bool,
) -> Iterator[build.ProjectBuilder]:
    if quiet:
        runner = pyproject_hooks.quiet_subprocess_runner
    else:
        runner = pyproject_hooks.default_subprocess_runner

    if not isolated:
        yield build.ProjectBuilder(src_dir, runner=runner)
        return

    maybe_pip_constrained_context = (
        contextlib.nullcontext()
        if upgrade_packages is None
        else _temporary_constraints_file_set_for_pip(upgrade_packages)
    )

    with maybe_pip_constrained_context, build.env.DefaultIsolatedEnv() as env:
        builder = build.ProjectBuilder.from_isolated_env(env, src_dir, runner)
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build("wheel"))
        yield builder


def _build_project_wheel_metadata(
    builder: build.ProjectBuilder,
) -> PackageMetadata:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(builder.metadata_path(tmpdir))
        return importlib_metadata.PathDistribution(path).metadata


def _get_name(metadata: PackageMetadata) -> str:
    retval = metadata.get_all("Name")[0]  # type: ignore[index]
    assert isinstance(retval, str)
    return retval


def _prepare_requirements(
    metadata: PackageMetadata, src_file: pathlib.Path
) -> Iterator[InstallRequirement]:
    package_name = _get_name(metadata)
    comes_from = f"{package_name} ({src_file})"
    package_dir = src_file.parent

    for req in metadata.get_all("Requires-Dist") or []:
        parts = parse_req_from_line(req, comes_from)
        if parts.requirement.name == package_name:
            # Replace package name with package directory in the requirement
            # string so that pip can find the package as self-referential.
            # Note the string can contain extras, so we need to replace only
            # the package name, not the whole string.
            replaced_package_name = req.replace(package_name, str(package_dir), 1)
            parts = parse_req_from_line(replaced_package_name, comes_from)

        yield copy_install_requirement(
            InstallRequirement(
                parts.requirement,
                comes_from,
                link=parts.link,
                markers=parts.markers,
                extras=parts.extras,
            )
        )


def _prepare_build_requirements(
    builder: build.ProjectBuilder,
    src_file: pathlib.Path,
    build_targets: tuple[str, ...],
    package_name: str,
) -> Iterator[InstallRequirement]:
    result = collections.defaultdict(set)

    # Build requirements will only be present if a pyproject.toml file exists,
    # but if there is also a setup.py file then only that will be explicitly
    # processed due to the order of `DEFAULT_REQUIREMENTS_FILES`.
    src_file = src_file.parent / PYPROJECT_TOML

    for req in builder.build_system_requires:
        result[req].add(f"{package_name} ({src_file}::build-system.requires)")
    for build_target in build_targets:
        for req in builder.get_requires_for_build(build_target):
            result[req].add(
                f"{package_name} ({src_file}::build-system.backend::{build_target})"
            )

    for req, comes_from_sources in result.items():
        for comes_from in comes_from_sources:
            yield install_req_from_line(req, comes_from=comes_from)
