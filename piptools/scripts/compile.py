from __future__ import annotations

import itertools
import os
import sys
import typing as _t
from pathlib import Path

import click
from build import BuildBackendException
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import redact_auth_from_url

from .._compat import canonicalize_name, parse_requirements, tempfile_compat
from .._internal import _pip_api
from ..build import ProjectMetadata, build_project_metadata
from ..cache import DependencyCache
from ..exceptions import NoCandidateFound, PipToolsError
from ..logging import log
from ..repositories import LocalRequirementsRepository, PyPIRepository
from ..repositories.base import BaseRepository
from ..resolver import BacktrackingResolver, LegacyResolver
from ..utils import (
    dedup,
    drop_extras,
    is_pinned_requirement,
    key_from_ireq,
)
from ..writer import OutputWriter
from . import _compile_parser


def _determine_linesep(
    strategy: str = "preserve", filenames: tuple[str, ...] = ()
) -> str:
    """
    Determine and return linesep string for OutputWriter to use.

    Valid strategies: "LF", "CRLF", "native", "preserve"
    When preserving, files are checked in order for existing newlines.
    """
    if strategy == "preserve":
        for fname in filenames:
            try:
                with open(fname, "rb") as existing_file:
                    existing_text = existing_file.read()
            except FileNotFoundError:
                continue
            if b"\r\n" in existing_text:
                strategy = "CRLF"
                break
            elif b"\n" in existing_text:
                strategy = "LF"
                break
    return {
        "native": os.linesep,
        "LF": "\n",
        "CRLF": "\r\n",
        "preserve": "\n",
    }[strategy]


@click.command(name="pip-compile")
@_compile_parser.parse_pip_compile_args
def cli(args: _compile_parser.CompileArgs, ctx: click.Context) -> None:
    """
    Compile requirements.txt from source files.

    Valid sources are requirements.in, pyproject.toml, setup.cfg,
    or setup.py specs.
    """
    if args.config:
        log.debug(f"Using pip-tools configuration defaults found in '{args.config!s}'.")

    if args.pip_args.resolver_name == "legacy":
        log.warning(
            "WARNING: the legacy dependency resolver is deprecated and will be removed"
            " in future versions of pip-tools."
        )

    ###
    # Setup
    ###

    repository: BaseRepository
    repository = PyPIRepository(
        list(args.pip_arg_tuple), cache_dir=args.pip_args.cache_dir
    )

    # Parse all constraints coming from --upgrade-package/-P
    upgrade_reqs_gen = (
        _pip_api.create_install_requirement_from_line(pkg)
        for pkg in args.upgrade_packages
    )
    upgrade_install_reqs = {
        key_from_ireq(install_req): install_req for install_req in upgrade_reqs_gen
    }

    # Exclude packages from --upgrade-package/-P from the existing constraints
    existing_pins = {}

    # Proxy with a LocalRequirementsRepository if --upgrade is not specified
    # (= default invocation)
    output_file_exists = os.path.exists(args.output_file.name)
    if not args.upgrade and output_file_exists:
        output_file_is_empty = os.path.getsize(args.output_file.name) == 0
        if upgrade_install_reqs and output_file_is_empty:
            log.warning(
                f"WARNING: the output file {args.output_file.name} exists but is empty. "
                "Pip-tools cannot upgrade only specific packages (using -P/--upgrade-package) "
                "without an existing pin file to provide constraints. "
                "This often occurs if you redirect standard output to your output file, "
                "as any existing content is truncated."
            )

        # Use a temporary repository to ensure outdated(removed) options from
        # existing requirements.txt wouldn't get into the current repository.
        tmp_repository = PyPIRepository(
            list(args.pip_arg_tuple), cache_dir=args.pip_args.cache_dir
        )
        ireqs = parse_requirements(
            args.output_file.name,
            finder=tmp_repository.finder,
            session=tmp_repository.session,
            options=tmp_repository.options,
        )

        for ireq in filter(is_pinned_requirement, ireqs):
            key = key_from_ireq(ireq)
            if key not in upgrade_install_reqs:
                existing_pins[key] = ireq
        repository = LocalRequirementsRepository(
            existing_pins, repository, reuse_hashes=args.reuse_hashes
        )

    ###
    # Parsing/collecting initial requirements
    ###

    constraints: list[InstallRequirement] = []
    setup_file_found = False
    for src_file in args.src_files:
        if src_file == "-":
            # pip requires filenames and not files. Since we want to support
            # piping from stdin, we need to briefly save the input from stdin
            # to a temporary file and have pip read that.
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
        elif src_file in args.setup_src_files:
            setup_file_found = True
            try:
                metadata = build_project_metadata(
                    src_file=Path(src_file),
                    build_targets=args.build_deps_targets,
                    upgrade_packages=args.upgrade_packages,
                    attempt_static_parse=not bool(args.build_deps_targets),
                    isolated=args.pip_args.build_isolation,
                    quiet=log.verbosity <= 0,
                )
            except BuildBackendException as e:
                log.error(str(e))
                log.error(f"Failed to parse {os.path.abspath(src_file)}")
                sys.exit(2)

            if not args.only_build_deps:
                constraints.extend(metadata.requirements)
                if args.all_extras:
                    args.extras += metadata.extras
            if args.build_deps_targets:
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

    # Parse all constraints from `--constraint` files
    for filename in args.constraint:
        constraints.extend(
            parse_requirements(
                filename,
                constraint=True,
                finder=repository.finder,
                options=repository.options,
                session=repository.session,
            )
        )

    if args.upgrade_packages:
        with tempfile_compat.named_temp_file() as constraints_file:
            constraints_file.write("\n".join(args.upgrade_packages))
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

    extras = tuple(itertools.chain.from_iterable(ex.split(",") for ex in args.extras))

    if extras and not setup_file_found:
        msg = "--extra has effect only with setup.py and PEP-517 input formats"
        raise click.BadParameter(msg)

    primary_packages = {
        key_from_ireq(ireq) for ireq in constraints if not ireq.constraint
    }

    constraints.extend(
        ireq for key, ireq in upgrade_install_reqs.items() if key in primary_packages
    )

    constraints = [req for req in constraints if req.match_markers(extras)]
    for req in constraints:
        drop_extras(req)

    if repository.finder.index_urls:
        log.debug("Using indexes:")
        with log.indentation():
            for index_url in dedup(repository.finder.index_urls):
                log.debug(redact_auth_from_url(index_url))
    else:
        log.debug("Ignoring indexes.")

    if repository.finder.find_links:
        log.debug("")
        log.debug("Using links:")
        with log.indentation():
            for find_link in dedup(repository.finder.find_links):
                log.debug(redact_auth_from_url(find_link))

    unsafe_package = tuple(
        canonicalize_name(pkg_name) for pkg_name in args.unsafe_package
    )

    resolver_cls = (
        LegacyResolver
        if args.pip_args.resolver_name == "legacy"
        else BacktrackingResolver
    )
    try:
        resolver = resolver_cls(
            constraints=constraints,
            existing_constraints=existing_pins,
            repository=repository,
            prereleases=(
                args.pip_args.pre
                or _pip_api.finder_allows_all_prereleases(repository.finder)
            ),
            cache=DependencyCache(args.pip_args.cache_dir),
            clear_caches=args.rebuild,
            allow_unsafe=args.allow_unsafe,
            unsafe_packages=set(unsafe_package),
        )
        results = resolver.resolve(max_rounds=args.max_rounds)
        hashes = resolver.resolve_hashes(results) if args.generate_hashes else None
    except NoCandidateFound as e:
        if resolver_cls == LegacyResolver:  # pragma: no branch
            log.error(
                "Using legacy resolver. "
                "Consider using backtracking resolver with "
                "`--resolver=backtracking`."
            )

        log.error(str(e))
        sys.exit(2)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    log.debug("")

    linesep = _determine_linesep(
        strategy=args.newline, filenames=(args.output_file.name, *args.src_files)
    )

    if args.strip_extras is None:
        args.strip_extras = False
        log.warning(
            "WARNING: --strip-extras is becoming the default "
            "in version 8.0.0. To silence this warning, "
            "either use --strip-extras to opt into the new default "
            "or use --no-strip-extras to retain the existing behavior."
        )

    ##
    # Output
    ##

    writer = OutputWriter(
        _t.cast(_t.BinaryIO, args.output_file),
        click_ctx=ctx,
        dry_run=args.dry_run,
        emit_header=args.header,
        emit_index_url=args.emit_index_url,
        emit_trusted_host=args.emit_trusted_host,
        annotate=args.annotate,
        annotation_style=args.annotation_style,
        strip_extras=args.strip_extras,
        generate_hashes=args.generate_hashes,
        default_index_url=repository.DEFAULT_INDEX_URL,
        index_urls=repository.finder.index_urls,
        trusted_hosts=repository.finder.trusted_hosts,
        format_control=repository.finder.format_control,
        linesep=linesep,
        allow_unsafe=args.allow_unsafe,
        find_links=repository.finder.find_links,
        emit_find_links=args.emit_find_links,
        emit_options=args.emit_options,
    )
    writer.write(
        results=results,
        unsafe_packages=resolver.unsafe_packages,
        unsafe_requirements=resolver.unsafe_constraints,
        markers={
            key_from_ireq(ireq): ireq.markers for ireq in constraints if ireq.markers
        },
        hashes=hashes,
    )

    if args.dry_run:
        log.info("Dry-run, so nothing updated.")
