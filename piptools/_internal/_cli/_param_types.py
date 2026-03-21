from __future__ import annotations

import click

from . import _parsed_param_types


class DependencyGroupParamType(click.ParamType):
    def get_metavar(self, param: click.Parameter) -> str:
        return "[pyproject-path:]groupname"

    def convert(
        self, value: str, param: click.Parameter | None, ctx: click.Context | None
    ) -> _parsed_param_types.ParsedDependencyGroupParam:
        """Parse a ``[dependency-groups]`` group reference."""
        return _parsed_param_types.ParsedDependencyGroupParam(value)
