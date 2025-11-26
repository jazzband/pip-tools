from __future__ import annotations

import copy
from typing import Any

from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from .pip_version import PIP_VERSION_MAJOR_MINOR


def create_install_requirement(
    name: str, version: str | Version, ireq: InstallRequirement
) -> InstallRequirement:
    # If no extras are specified, the extras string is blank
    extras_string = ""
    extras = ireq.extras
    if extras:
        # Sort extras for stability
        extras_string = f"[{','.join(sorted(extras))}]"

    version_pin_operator = "=="
    version_as_str = str(version)
    for specifier in ireq.specifier:
        if specifier.operator == "===" and specifier.version == version_as_str:
            version_pin_operator = "==="
            break

    return create_install_requirement_from_line(
        str(f"{name}{extras_string}{version_pin_operator}{version}"),
        constraint=ireq.constraint,
    )


def create_install_requirement_from_line(
    *args: Any, **kwargs: Any
) -> InstallRequirement:
    return copy_install_requirement(install_req_from_line(*args, **kwargs))


def copy_install_requirement(
    template: InstallRequirement, **extra_kwargs: Any
) -> InstallRequirement:
    """Make a copy of a template ``InstallRequirement`` with extra kwargs."""
    # Prepare install requirement kwargs.
    kwargs = {
        "comes_from": template.comes_from,
        "editable": template.editable,
        "link": template.link,
        "markers": template.markers,
        "isolated": template.isolated,
        "hash_options": template.hash_options,
        "constraint": template.constraint,
        "extras": template.extras,
        "user_supplied": template.user_supplied,
    }
    if PIP_VERSION_MAJOR_MINOR < (25, 3):  # pragma: <3.9 cover
        # Ref: https://github.com/jazzband/pip-tools/issues/2252
        kwargs["use_pep517"] = template.use_pep517
        kwargs["global_options"] = template.global_options
    kwargs.update(extra_kwargs)

    if PIP_VERSION_MAJOR_MINOR >= (25, 3):  # pragma: >=3.9 cover
        # Ref: https://github.com/jazzband/pip-tools/issues/2252
        kwargs.pop("use_pep517", None)
        kwargs.pop("global_options", None)

    if PIP_VERSION_MAJOR_MINOR <= (23, 0):
        kwargs["install_options"] = template.install_options

    # Original link does not belong to install requirements constructor,
    # pop it now to update later.
    original_link = kwargs.pop("original_link", None)

    # Copy template.req if not specified in extra kwargs.
    if "req" not in kwargs:
        kwargs["req"] = copy.deepcopy(template.req)

    kwargs["extras"] = set(map(canonicalize_name, kwargs["extras"]))
    if kwargs["req"]:
        kwargs["req"].extras = set(kwargs["extras"])

    ireq = InstallRequirement(**kwargs)

    # If the original_link was None, keep it so. Passing `link` as an
    # argument to `InstallRequirement` sets it as the original_link.
    ireq.original_link = (
        template.original_link if original_link is None else original_link
    )

    return ireq
