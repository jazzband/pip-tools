from __future__ import annotations

import sys
from typing import Any, Iterable, Iterator

import click
from dependency_groups import DependencyGroupResolver
from pip._internal.req import InstallRequirement
from pip._vendor.packaging.requirements import Requirement

from .utils import ParsedDependencyGroupParam

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def parse_dependency_groups(
    params: tuple[ParsedDependencyGroupParam, ...],
) -> list[InstallRequirement]:
    resolvers = _build_resolvers(param.path for param in params)
    reqs: list[InstallRequirement] = []
    for param in params:
        resolver = resolvers[param.path]
        try:
            reqs.extend(
                InstallRequirement(
                    Requirement(str(req)),
                    comes_from=f"--group '{param.path}:{param.group}'",
                )
                for req in resolver.resolve(param.group)
            )
        except (ValueError, TypeError, LookupError) as e:
            raise click.UsageError(
                f"[dependency-groups] resolution failed for '{param.group}' "
                f"from '{param.path}': {e}"
            ) from e
    return reqs


def _resolve_all_groups(
    resolvers: dict[str, DependencyGroupResolver], groups: list[tuple[str, str]]
) -> Iterator[str]:
    """
    Run all resolution, converting any error from `DependencyGroupResolver` into
    a UsageError.
    """
    for path, groupname in groups:
        resolver = resolvers[path]
        try:
            yield from (str(req) for req in resolver.resolve(groupname))
        except (ValueError, TypeError, LookupError) as e:
            raise click.UsageError(
                f"[dependency-groups] resolution failed for '{groupname}' "
                f"from '{path}': {e}"
            ) from e


def _build_resolvers(paths: Iterable[str]) -> dict[str, Any]:
    resolvers = {}
    for path in paths:
        if path in resolvers:
            continue

        pyproject = _load_pyproject(path)
        if "dependency-groups" not in pyproject:
            raise click.UsageError(
                f"[dependency-groups] table was missing from '{path}'. "
                "Cannot resolve '--group' option."
            )
        raw_dependency_groups = pyproject["dependency-groups"]
        if not isinstance(raw_dependency_groups, dict):
            raise click.UsageError(
                f"[dependency-groups] table was malformed in {path}. "
                "Cannot resolve '--group' option."
            )

        resolvers[path] = DependencyGroupResolver(raw_dependency_groups)
    return resolvers


def _load_pyproject(path: str) -> dict[str, Any]:
    try:
        with open(path, "rb") as fp:
            return tomllib.load(fp)
    except FileNotFoundError:
        raise click.UsageError(f"{path} not found. Cannot resolve '--group' option.")
    except tomllib.TOMLDecodeError as e:
        raise click.UsageError(f"Error parsing {path}: {e}") from e
    except OSError as e:
        raise click.UsageError(f"Error reading {path}: {e}") from e
