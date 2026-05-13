"""``[tool.pip-tools]`` block: the schema pip-tools owns.

PEP 751's ``[[packages]]`` and top-level fields live in
``packaging.pylock`` (``Pylock``, ``Package``, ``PackageWheel``, ...);
PEP 751 keeps the ``tool.pip-tools`` block opaque by design. The typed
container plus the (de)serialization helpers live together so a future
schema change touches one file.
"""

from __future__ import annotations

import os
import typing as _t
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from importlib.metadata import version as _pkg_version
from sys import argv

from .._internal import _pip_api
from ._inputs import LockSelection, LockTargets, ResolverOptions, ToolMetadataOptions
from .redact import redact_command

# Source of truth for ``[tool.pip-tools]`` field names. Stays in sync with
# ``PylockToolOptions``; drift lands unrecognised keys in the lockfile.
TOOL_FIELDS: _t.Final[frozenset[str]] = frozenset(
    {
        "version",
        "pip-version",
        "command",
        "generated-at",
        "platforms",
        "python-versions",
        "target-environments",
        "no-universal",
        "extras",
        "all-extras",
        "groups",
        "all-groups",
        "pre",
        "allow-unsafe",
        "rebuild",
    }
)


@dataclass
class PylockToolOptions:
    """Resolver-side switches recorded in the ``[tool.pip-tools]`` block."""

    platforms: list[str] | None = None
    python_versions: list[str] | None = None
    target_environments: list[str] | None = None
    no_universal: bool | None = None
    extras: list[str] | None = None
    all_extras: bool | None = None
    groups: list[str] | None = None
    all_groups: bool | None = None
    pre: bool | None = None
    allow_unsafe: bool | None = None
    rebuild: bool | None = None


def _default_generated_at() -> datetime:
    # Reproducible builds set ``SOURCE_DATE_EPOCH`` to a Unix timestamp;
    # honour it so two consecutive lock runs against identical inputs
    # produce byte-identical lockfiles. Without the env var, fall back to
    # the wall clock.
    if (epoch := os.environ.get("SOURCE_DATE_EPOCH")) is not None:
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc)
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


@dataclass
class PylockToolMetadata:
    """Top-level container for the ``[tool.pip-tools]`` lockfile section."""

    version: str
    pip_version: str = ""
    generated_at: datetime | None = field(default_factory=_default_generated_at)
    command: list[str] = field(default_factory=list)
    options: PylockToolOptions | None = None


_ToolValue: _t.TypeAlias = (
    "str | int | bool | datetime | list[str] | dict[str, _ToolValue]"
)


def build(
    *,
    selection: LockSelection,
    targets: LockTargets,
    options: ResolverOptions,
    metadata: ToolMetadataOptions,
) -> PylockToolMetadata | None:
    """Build the ``[tool.pip-tools]`` metadata block honouring user opt-outs.

    :param selection: Extras and groups the lock covers.
    :param targets: Resolved target environments and platform/python axes.
    :param options: Resolver options whose recorded toggles end up in the block.
    :param metadata: User-supplied opt-outs for the metadata block.
    :returns: The populated metadata, or ``None`` when every field was suppressed.
    """
    skip = frozenset(metadata.skip_metadata_fields)
    if metadata.no_metadata or TOOL_FIELDS.issubset(skip):
        return None

    _Opt = _t.TypeVar("_Opt")

    def _opt(key: str, value: _Opt) -> _Opt | None:
        return None if key in skip else value

    tool_options = PylockToolOptions(
        platforms=_opt("platforms", sorted(targets.platforms)),
        python_versions=_opt("python-versions", sorted(targets.python_versions)),
        target_environments=_opt("target-environments", sorted(targets.target_envs)),
        no_universal=_opt("no-universal", targets.no_universal),
        extras=_opt("extras", sorted(selection.extras)),
        all_extras=_opt("all-extras", selection.all_extras),
        groups=_opt("groups", sorted(selection.groups)),
        all_groups=_opt("all-groups", selection.all_groups),
        pre=_opt("pre", options.pre),
        allow_unsafe=_opt("allow-unsafe", options.allow_unsafe),
        rebuild=_opt("rebuild", options.rebuild),
    )
    return PylockToolMetadata(
        version=_opt("version", _pkg_version("pip-tools")) or "",
        pip_version=_opt("pip-version", str(_pip_api.PIP_VERSION)) or "",
        # _default_generated_at reads SOURCE_DATE_EPOCH. A direct
        # datetime.now() call here bypasses the env var on every
        # CLI-driven path and leaves reproducible-build pipelines with
        # wall-clock drift in the lockfile.
        generated_at=_opt("generated-at", _default_generated_at()),
        # ``argv[0]`` is whatever launched the process: a venv path, a
        # ``/usr/local/bin`` link, ``python -m piptools.scripts.lock``.
        # Two users on different machines committing the same lock see
        # different ``command[0]`` entries without normalisation (noisy
        # diffs). Normalise to the script name; uv does the same with
        # ``"uv"``.
        command=_opt("command", ["pip-lock", *redact_command(argv[1:])]) or [],
        options=tool_options,
    )


def to_dict(meta: PylockToolMetadata) -> dict[str, _ToolValue]:
    """Render the metadata as the dict shape ``tomli_w`` writes verbatim.

    :param meta: Metadata block to serialise.
    :returns: Dict with hyphenated TOML keys, ready for the writer.
    """
    result: dict[str, _ToolValue] = {}
    # ``version`` defaults to ``""`` when the user opted it out via
    # ``--skip-metadata-field version``; writing an empty string emits
    # an invalid metadata field rather than omitting it. Treat falsy as
    # opt-out (``_pkg_version("pip-tools")`` is never empty in normal
    # operation).
    if meta.version:
        result["version"] = meta.version
    if meta.pip_version:
        result["pip-version"] = meta.pip_version
    if meta.command:
        result["command"] = meta.command
    if meta.generated_at is not None:
        result["generated-at"] = meta.generated_at
    if (opts := meta.options) is None:
        return result
    for f in fields(opts):
        if (value := getattr(opts, f.name)) is None:
            continue
        result[f.name.replace("_", "-")] = value
    return result


__all__ = [
    "TOOL_FIELDS",
    "PylockToolMetadata",
    "PylockToolOptions",
    "build",
    "to_dict",
]
