from __future__ import annotations

import functools
import typing as _t

import click

from . import _parsed_param_types

F = _t.TypeVar("F", bound=_t.Callable[..., _t.Any])


def _add_ctx_arg(f: F) -> F:
    """
    Make ``ParamType`` methods compatible with various click versions, as documented
    in the click docs here:
    https://click.palletsprojects.com/en/stable/support-multiple-versions/
    """

    @functools.wraps(f)
    def wrapper(*args: _t.Any, **kwargs: _t.Any) -> _t.Any:
        # NOTE: this check is skipped in coverage as it requires a lower `click` version
        # NOTE: once we have a coverage plugin for library version pragmas, we can make
        # NOTE: this do the appropriate dispatch
        if "ctx" not in kwargs:  # pragma: no cover
            kwargs["ctx"] = click.get_current_context(silent=True)

        return f(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


class DependencyGroupParamType(click.ParamType):
    @_add_ctx_arg
    def get_metavar(  # type: ignore[override]
        self, param: click.Parameter, ctx: click.Context
    ) -> str:
        return "[pyproject-path:]groupname"

    def convert(
        self, value: str, param: click.Parameter | None, ctx: click.Context | None
    ) -> _parsed_param_types.ParsedDependencyGroupParam:
        """Parse a ``[dependency-groups]`` group reference."""
        return _parsed_param_types.ParsedDependencyGroupParam(value)
