"""CLI entry point for ``pip-lock``: produces a PEP 751 ``pylock.toml``.

Owns only the user-facing interface (argument parsing, input
validation, configuration discovery) and delegates the lock pipeline
to the pylock package. Keep business logic out so the CLI surface
stays inspectable as a flat option list.
"""

from __future__ import annotations

import typing as _t
from os import environ
from pathlib import Path

from click import BadParameter, Context, command, open_file, pass_context
from click.utils import LazyFile, safecall
from packaging.pylock import Pylock, PylockValidationError
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import redact_auth_from_url

from ..._compat import canonicalize_name
from ..._internal import _pip_api
from ...exceptions import NoCandidateFound, PipToolsError
from ...logging import log
from ...repositories import PyPIRepository
from ...scripts import options
from ...scripts.options import BuildTargetT
from ...utils import dedup
from .._inputs import (
    LockInputs,
    LockSelection,
    LockTargets,
    ResolverOptions,
    ToolMetadataOptions,
    WorkerSpec,
)
from ..builder import build_pylock_document
from ..config import extract_conflicts, load_default_groups
from ._file_io import (
    _advisory_lock,
    emit_check,
    emit_dry_run,
    emit_write,
)
from ._inputs import build_constraints, resolve_src_files
from ._pip_args import build_pip_args
from ._seeds import seed_pins_from_existing_lock
from ._targets import resolve_groups, resolve_targets
from ._validation import validate_options

_LOCK_EPILOG = """\b
Examples:
\b
    Lock dependencies to pylock.toml:
    $ pip-lock
\b
    Lock for specific platforms:
    $ pip-lock --platform linux-x86_64 --platform windows-amd64
\b
    Lock for current platform only (faster):
    $ pip-lock --no-universal
\b
    Preview the lock without writing:
    $ pip-lock --dry-run > pylock.toml
\b
    Re-lock keeping every pin except one:
    $ pip-lock --upgrade-package requests
"""


@command(
    name="pip-lock",
    # Click's default formatter caps width at ``min(terminal, 80)``, which
    # wraps multi-clause flag descriptions into noisy 4-line paragraphs on
    # wide terminals. 120 keeps help scannable; users on narrow terminals
    # can resize.
    context_settings={"terminal_width": 120, "max_content_width": 120},
)
@pass_context
@options.help_option(epilog=_LOCK_EPILOG)
@options.version
@options.color
@options.verbose
@options.quiet
@options.dry_run
@options.check
@options.pre
@options.rebuild
@options.extra
@options.all_extras
@options.find_links
@options.index_url
@options.no_index
@options.extra_index_url
@options.cert
@options.client_cert
@options.trusted_host
@options.uploaded_prior_to
@options.upgrade_package
@options.upgrade_lock
@options.output_file
@options.allow_unsafe
@options.max_rounds
@options.src_files
@options.build_isolation
@options.cache_dir
@options.pip_args
@options.unsafe_package
@options.config
@options.no_config
@options.constraint
@options.build_deps_for
@options.all_build_deps
@options.only_build_deps
@options.platform
@options.python_version
@options.implementation
@options.no_universal
@options.group
@options.all_groups
@options.no_metadata
@options.skip_metadata_fields
@options.jobs
def cli(
    click_context: Context,
    color: bool | None,
    verbose: int,
    quiet: int,
    dry_run: bool,
    check: bool,
    pre: bool,
    rebuild: bool,
    extras: tuple[str, ...],
    all_extras: bool,
    find_links: tuple[str, ...],
    index_url: str,
    no_index: bool,
    extra_index_url: tuple[str, ...],
    cert: str | None,
    client_cert: str | None,
    trusted_host: tuple[str, ...],
    uploaded_prior_to: str | None,
    upgrade_packages: tuple[str, ...],
    upgrade_lock: bool,
    output_file: LazyFile | _t.IO[_t.Any] | None,
    allow_unsafe: bool,
    src_files: tuple[str, ...],
    max_rounds: int,
    build_isolation: bool,
    cache_dir: str,
    pip_args_str: str | None,
    unsafe_package: tuple[str, ...],
    config: Path | None,
    no_config: bool,
    constraint: tuple[str, ...],
    build_deps_targets: tuple[BuildTargetT, ...],
    all_build_deps: bool,
    only_build_deps: bool,
    platforms: tuple[str, ...],
    python_versions: tuple[str, ...],
    implementations: tuple[str, ...],
    no_universal: bool,
    groups: tuple[str, ...],
    all_groups: bool,
    no_metadata: bool,
    skip_metadata_fields: tuple[str, ...],
    jobs: int,
) -> None:
    """Lock dependencies into a PEP 751 pylock.toml file.

    \b
    EXPERIMENTAL. The CLI surface and the [tool.pip-tools] block may change
    between releases without a deprecation cycle while this command settles.
    Set PIP_TOOLS_HIDE_EXPERIMENTAL_WARNING=1 to silence the runtime banner.
    """
    if color is not None:
        click_context.color = color
    log.verbosity = verbose - quiet
    if not environ.get("PIP_TOOLS_HIDE_EXPERIMENTAL_WARNING"):
        # Marking pip-lock as experimental gives the CLI room to evolve while
        # users start trying it; mirror what pip 26.1 does for ``pip lock``.
        # The env-var escape lets CI suppress the noise once the team has
        # acknowledged the contract is fluid.
        log.warning(
            "pip-lock is experimental: the CLI and the [tool.pip-tools] block "
            "may change between releases. "
            "Set PIP_TOOLS_HIDE_EXPERIMENTAL_WARNING=1 to silence."
        )
    src_files = resolve_src_files(click_context, src_files)
    if check and dry_run:
        raise BadParameter(
            "--check verifies the on-disk lockfile; --dry-run prints what "
            "would be written. Pick one.",
            param_hint="--check / --dry-run",
        )
    if check and upgrade_lock:
        raise BadParameter(
            "--check expects the on-disk lockfile to match what the resolver "
            "produces; --upgrade re-resolves from scratch and ignores seeds, "
            "so the combination only succeeds when no upstream package has "
            "shipped a newer version. Drop --upgrade or run the upgrade as a "
            "separate step.",
            param_hint="--check / --upgrade",
        )
    validate_options(
        all_build_deps,
        build_deps_targets,
        only_build_deps,
        extras,
        all_extras,
        src_files,
        output_file,
    )
    if all_build_deps:
        build_deps_targets = options.ALL_BUILD_TARGETS
    if not output_file:
        output_file = open_file("pylock.toml", "w+b", atomic=True, lazy=True)
        click_context.call_on_close(
            safecall(_t.cast(LazyFile, output_file).close_intelligently)
        )
    lock_dir = (
        Path(output_file.name).resolve().parent
        if output_file is not None and hasattr(output_file, "name")
        else None
    )
    # Hold the advisory lock for seed-resolve-write so two concurrent
    # pip-lock processes against the same output can't both seed from the
    # pre-write file and race on the atomic rename. ``_advisory_lock``
    # raises ``PipToolsError`` if the output's parent directory is missing;
    # catch here so the user sees exit-2 instead of a click-internal
    # traceback.
    try:
        click_context.with_resource(_advisory_lock(output_file))
    except PipToolsError as e:
        log.error(str(e))
        raise SystemExit(2) from e
    # Reuse pins from any existing pylock so unrelated packages don't churn
    # on a re-lock (the pip-compile ``-P pkg`` workflow); ``--upgrade``
    # bypasses, ``--upgrade-package`` exempts the named packages from
    # seeding so they re-resolve.
    seeded_pins: tuple[str, ...] = ()
    if not upgrade_lock and output_file is not None and hasattr(output_file, "name"):
        seeded_pins = seed_pins_from_existing_lock(
            Path(output_file.name),
            upgrade_packages,
            unsafe_packages=unsafe_package,
            allow_unsafe=allow_unsafe,
        )
    if config:
        log.debug(f"Using pip-tools configuration defaults found in '{config!s}'.")

    pip_args = build_pip_args(
        find_links,
        index_url,
        no_index,
        extra_index_url,
        cert,
        client_cert,
        pre,
        trusted_host,
        uploaded_prior_to,
        build_isolation,
        cache_dir,
        pip_args_str,
    )
    repository = PyPIRepository(pip_args, cache_dir=cache_dir)
    raw_constraints, extras, project_requires_python = build_constraints(
        repository=repository,
        src_files=src_files,
        constraint=constraint,
        build_deps_targets=build_deps_targets,
        only_build_deps=only_build_deps,
        all_extras=all_extras,
        extras=extras,
        build_isolation=build_isolation,
        upgrade_packages=tuple(upgrade_packages) + seeded_pins,
    )
    if repository.finder.index_urls:
        log.debug("Using indexes:")
        with log.indentation():
            for idx_url in dedup(repository.finder.index_urls):
                log.debug(redact_auth_from_url(idx_url))
    group_constraints, groups = resolve_groups(src_files, groups, all_groups)
    targets = resolve_targets(
        platforms,
        python_versions,
        implementations,
        no_universal,
        project_requires_python=project_requires_python,
    )

    try:
        doc = _do_build_pylock(
            src_files=src_files,
            repository=repository,
            raw_constraints=raw_constraints,
            extras=extras,
            all_extras=all_extras,
            groups=groups,
            all_groups=all_groups,
            group_constraints=group_constraints,
            targets=targets,
            pre=pre,
            rebuild=rebuild,
            allow_unsafe=allow_unsafe,
            unsafe_package=unsafe_package,
            max_rounds=max_rounds,
            cache_dir=cache_dir,
            jobs=jobs,
            pip_args=pip_args,
            no_metadata=no_metadata,
            skip_metadata_fields=skip_metadata_fields,
            lock_dir=lock_dir,
            project_requires_python=project_requires_python,
        )
    except NoCandidateFound as e:
        log.error(str(e))
        raise SystemExit(2) from e
    except PipToolsError as e:
        log.error(str(e))
        raise SystemExit(2) from e
    except PylockValidationError as e:
        # ``packaging.pylock.Pylock.__init__`` validates at construction;
        # surface the validation message as exit-2 instead of letting a
        # raw traceback through.
        log.error(str(e))
        raise SystemExit(2) from e
    if check:
        emit_check(doc, output_file)
    elif dry_run:
        emit_dry_run(doc)
    else:
        emit_write(doc, output_file)


def _do_build_pylock(
    *,
    src_files: tuple[str, ...],
    repository: PyPIRepository,
    raw_constraints: list[InstallRequirement],
    extras: tuple[str, ...],
    all_extras: bool,
    groups: tuple[str, ...],
    all_groups: bool,
    group_constraints: dict[str, list[InstallRequirement]],
    targets: LockTargets,
    pre: bool,
    rebuild: bool,
    allow_unsafe: bool,
    unsafe_package: tuple[str, ...],
    max_rounds: int,
    cache_dir: str,
    jobs: int,
    pip_args: list[str],
    no_metadata: bool,
    skip_metadata_fields: tuple[str, ...],
    lock_dir: Path | None,
    project_requires_python: tuple[str, ...],
) -> Pylock:
    return build_pylock_document(
        src_files=src_files,
        repository=repository,
        inputs=LockInputs(
            raw_constraints=raw_constraints,
            conflicts=extract_conflicts(src_files),
            group_constraints=group_constraints,
        ),
        selection=LockSelection(
            extras=extras,
            all_extras=all_extras,
            groups=groups,
            all_groups=all_groups,
            default_groups=load_default_groups(src_files),
        ),
        targets=targets,
        options=ResolverOptions(
            prereleases=pre
            or _pip_api.finder_allows_all_prereleases(repository.finder),
            rebuild=rebuild,
            allow_unsafe=allow_unsafe,
            unsafe_packages=frozenset(
                canonicalize_name(pkg_name) for pkg_name in unsafe_package
            ),
            max_rounds=max_rounds,
            cache_dir=cache_dir,
            pre=pre,
        ),
        workers=WorkerSpec(jobs=jobs, pip_args=tuple(pip_args)),
        metadata=ToolMetadataOptions(
            no_metadata=no_metadata,
            skip_metadata_fields=skip_metadata_fields,
        ),
        lock_dir=lock_dir,
        project_requires_python=project_requires_python,
    )


__all__ = [
    "cli",
]
