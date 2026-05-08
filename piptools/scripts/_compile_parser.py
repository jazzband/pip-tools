"""
This module defines the ``pip-compile`` parser, which consists of two public interfaces:

- ``parse_pip_compile_args``: a decorator which adds parsing to a function.

- ``CompileArgs``: a datatype containing the parsed arguments

``parse_pip_compile_args`` adds ``click`` parameters and wraps the function to convert
those parameters to a ``CompileArgs``.

Parsing can have surprising side-effects. Notably...
- eager options in click, like `--help`, can seize control
- some parsing steps write to other bits of application state, like the click context
  or setting logging verbosity
- some parsing work actually does IO, e.g., to confirm that files exist
"""

from __future__ import annotations

import dataclasses
import functools
import os.path
import pathlib
import shlex
import typing as _t

import click
from click.utils import LazyFile, safecall

from .._internal import _pip_api
from ..logging import log
from . import options
from ._deprecations import filter_deprecated_pip_args

__all__ = ("parse_pip_compile_args", "CompileArgs")


_DEFAULT_REQUIREMENTS_FILES = (
    "requirements.in",
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
)
_DEFAULT_REQUIREMENTS_FILE = "requirements.in"
_DEFAULT_REQUIREMENTS_OUTPUT_FILE = "requirements.txt"
_METADATA_FILENAMES = frozenset({"setup.py", "setup.cfg", "pyproject.toml"})


_COMPILE_EPILOG = """\b
Examples:
\b
    Compile requirements.in to requirements.txt:
    $ pip-compile
\b
    Upgrade all packages to their latest versions:
    $ pip-compile --upgrade
\b
    Upgrade specific packages:
    $ pip-compile -P django -P requests
\b
    Include package hashes for extra security:
    $ pip-compile --generate-hashes
\b
    Compile with optional extras:
    $ pip-compile --extra dev pyproject.toml
"""


@dataclasses.dataclass
class CompileArgs:
    # ctx is provided on init only
    ctx: dataclasses.InitVar[click.Context]
    pip_args: PipArgs
    color: bool | None
    verbosity: int
    dry_run: bool
    rebuild: bool
    extras: tuple[str, ...]
    all_extras: bool
    header: bool
    emit_trusted_host: bool
    annotate: bool
    annotation_style: str
    upgrade: bool
    upgrade_packages: tuple[str, ...]
    newline: str
    allow_unsafe: bool
    strip_extras: bool | None
    generate_hashes: bool
    reuse_hashes: bool
    src_files: tuple[str, ...]
    max_rounds: int
    emit_find_links: bool
    emit_index_url: bool
    emit_options: bool
    unsafe_package: tuple[str, ...]
    config: pathlib.Path | None
    no_config: bool
    constraint: tuple[str, ...]
    build_deps_targets: tuple[options.BuildTargetT, ...]
    all_build_deps: bool
    only_build_deps: bool
    # _output_file is the original, but consumers will use the `output_file` property
    _output_file: LazyFile | _t.IO[_t.Any] | None
    # _pip_arg_tuple is used to store and retrieve the processed PipArgs
    _pip_arg_tuple: tuple[str, ...] = ()

    def __post_init__(self, ctx: click.Context) -> None:
        if self.color is not None:
            ctx.color = self.color
        log.verbosity = self.verbosity

        self._process_build_deps_opts()
        self._process_src_files(ctx)
        self._process_extras_opts()
        self._process_output_file(ctx)
        self._process_pip_args_str()

    # this "type narrowing" property handles the fact that we are not guaranteed a value
    # for 'output_file' from the user, but we are guaranteed one after parsing
    @property
    def output_file(self) -> LazyFile | _t.IO[_t.Any]:
        assert self._output_file is not None
        return self._output_file

    @property
    def pip_arg_tuple(self) -> tuple[str, ...]:
        return self._pip_arg_tuple

    @functools.cached_property
    def setup_src_files(self) -> frozenset[str]:
        return frozenset(
            f for f in self.src_files if os.path.basename(f) in _METADATA_FILENAMES
        )

    def _process_src_files(self, ctx: click.Context) -> None:
        # If ``src-files` was not provided as an input, but rather as config,
        # it will be part of the click context ``ctx``.
        # However, if ``src_files`` is specified, then we want to use that.
        if not self.src_files and ctx.default_map and "src_files" in ctx.default_map:
            self.src_files = ctx.default_map["src_files"]

        if not self.src_files:
            for file_path in _DEFAULT_REQUIREMENTS_FILES:
                if os.path.exists(file_path):
                    self.src_files = (file_path,)
                    break
            else:
                raise click.BadParameter(
                    (
                        "If you do not specify an input file, the default is one of: {}"
                    ).format(", ".join(_DEFAULT_REQUIREMENTS_FILES))
                )

        if (
            any(f not in self.setup_src_files for f in self.src_files)
            and self.build_deps_targets
        ):
            msg = (
                "--build-deps-for and --all-build-deps can be used only with the "
                "setup.py, setup.cfg and pyproject.toml specs."
            )
            raise click.BadParameter(msg)

    def _process_build_deps_opts(self) -> None:
        if self.all_build_deps and self.build_deps_targets:
            raise click.BadParameter(
                "--build-deps-for has no effect when used with --all-build-deps"
            )
        elif self.all_build_deps:
            self.build_deps_targets = options.ALL_BUILD_TARGETS

        if self.only_build_deps and not self.build_deps_targets:
            raise click.BadParameter(
                "--only-build-deps requires either --build-deps-for or --all-build-deps"
            )
        if self.only_build_deps and (self.extras or self.all_extras):
            raise click.BadParameter(
                "--only-build-deps cannot be used with any of --extra, --all-extras"
            )

    def _process_extras_opts(self) -> None:
        if self.all_extras and self.extras:
            msg = "--extra has no effect when used with --all-extras"
            raise click.BadParameter(msg)

    def _process_output_file(self, ctx: click.Context) -> None:
        if not self._output_file:
            # An output file must be provided for stdin
            if self.src_files == ("-",):
                raise click.BadParameter(
                    "--output-file is required if input is from stdin"
                )
            # Use default requirements output file if there is a setup.py the source
            # file
            elif os.path.basename(self.src_files[0]) in _METADATA_FILENAMES:
                file_name = os.path.join(
                    os.path.dirname(self.src_files[0]),
                    _DEFAULT_REQUIREMENTS_OUTPUT_FILE,
                )
            # An output file must be provided if there are multiple source files
            elif len(self.src_files) > 1:
                raise click.BadParameter(
                    "--output-file is required if two or more input files are given."
                )
            # Otherwise derive the output file from the source file
            else:
                base_name = self.src_files[0].rsplit(".", 1)[0]
                file_name = base_name + ".txt"

            self._output_file = click.open_file(
                file_name, "w+b", atomic=True, lazy=True
            )

            # Close the file at the end of the context execution
            assert self._output_file is not None
            # only LazyFile has close_intelligently, newer _t.IO[_t.Any] does not
            if isinstance(self._output_file, LazyFile):  # pragma: no cover
                ctx.call_on_close(safecall(self._output_file.close_intelligently))

        if self._output_file.name != "-" and self._output_file.name in self.src_files:
            raise click.BadArgumentUsage(
                "input and output filenames must not "
                f"be matched: {self._output_file.name}"
            )

    def _process_pip_args_str(self) -> None:
        self._pip_arg_tuple = self.pip_args.as_argument_tuple()


@dataclasses.dataclass
class PipArgs:
    pre: bool
    find_links: tuple[str, ...]
    index_url: str
    no_index: bool
    extra_index_url: tuple[str, ...]
    cert: str | None
    client_cert: str | None
    trusted_host: tuple[str, ...]
    uploaded_prior_to: str | None
    build_isolation: bool
    resolver_name: str
    cache_dir: str
    pip_args_str: str | None

    def as_argument_tuple(self) -> tuple[str, ...]:
        right_args = shlex.split(self.pip_args_str or "")
        pip_arg_list = []
        for link in self.find_links:
            pip_arg_list.extend(["-f", link])
        if self.index_url:
            pip_arg_list.extend(["-i", self.index_url])
        if self.no_index:
            pip_arg_list.extend(["--no-index"])
        for extra_index in self.extra_index_url:
            pip_arg_list.extend(["--extra-index-url", extra_index])
        if self.cert:
            pip_arg_list.extend(["--cert", self.cert])
        if self.client_cert:
            pip_arg_list.extend(["--client-cert", self.client_cert])
        if self.pre:
            pip_arg_list.extend(["--pre"])
        for host in self.trusted_host:
            pip_arg_list.extend(["--trusted-host", host])
        if self.uploaded_prior_to:
            if _pip_api.PIP_VERSION_MAJOR_MINOR < (26, 0):
                raise click.BadParameter(
                    "--uploaded-prior-to requires pip >= 26.0, "
                    f"but you have pip {_pip_api.PIP_VERSION}",
                    param_hint="--uploaded-prior-to",
                )
            pip_arg_list.extend(["--uploaded-prior-to", self.uploaded_prior_to])
        if not self.build_isolation:
            pip_arg_list.append("--no-build-isolation")
        if self.resolver_name == "legacy":
            pip_arg_list.extend(["--use-deprecated", "legacy-resolver"])
        if self.resolver_name == "backtracking" and self.cache_dir:
            pip_arg_list.extend(["--cache-dir", self.cache_dir])
        pip_arg_list.extend(right_args)
        pip_arg_list = filter_deprecated_pip_args(pip_arg_list)
        return tuple(pip_arg_list)


def parse_pip_compile_args(f: _t.Callable[..., None]) -> _t.Callable[..., None]:
    @click.pass_context
    @options.help_option(epilog=_COMPILE_EPILOG)
    @options.version
    @options.color
    @options.verbose
    @options.quiet
    @options.dry_run
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
    @options.header
    @options.emit_trusted_host
    @options.annotate
    @options.annotation_style
    @options.upgrade
    @options.upgrade_package
    @options.output_file
    @options.newline
    @options.allow_unsafe
    @options.strip_extras
    @options.generate_hashes
    @options.reuse_hashes
    @options.max_rounds
    @options.src_files
    @options.build_isolation
    @options.emit_find_links
    @options.cache_dir
    @options.pip_args
    @options.resolver
    @options.emit_index_url
    @options.emit_options
    @options.unsafe_package
    @options.config
    @options.no_config
    @options.constraint
    @options.build_deps_for
    @options.all_build_deps
    @options.only_build_deps
    @functools.wraps(f)
    def wrapper(
        ctx: click.Context,
        color: bool | None,
        verbose: int,
        quiet: int,
        dry_run: bool,
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
        header: bool,
        emit_trusted_host: bool,
        annotate: bool,
        annotation_style: str,
        upgrade: bool,
        upgrade_packages: tuple[str, ...],
        output_file: LazyFile | _t.IO[_t.Any] | None,
        newline: str,
        allow_unsafe: bool,
        strip_extras: bool | None,
        generate_hashes: bool,
        reuse_hashes: bool,
        src_files: tuple[str, ...],
        max_rounds: int,
        build_isolation: bool,
        emit_find_links: bool,
        cache_dir: str,
        pip_args_str: str | None,
        resolver_name: str,
        emit_index_url: bool,
        emit_options: bool,
        unsafe_package: tuple[str, ...],
        config: pathlib.Path | None,
        no_config: bool,
        constraint: tuple[str, ...],
        build_deps_targets: tuple[options.BuildTargetT, ...],
        all_build_deps: bool,
        only_build_deps: bool,
        *remainder_args: _t.Any,
        **remainder_kwargs: _t.Any,
    ) -> None:
        pip_args = PipArgs(
            pre=pre,
            find_links=find_links,
            index_url=index_url,
            no_index=no_index,
            extra_index_url=extra_index_url,
            cert=cert,
            client_cert=client_cert,
            trusted_host=trusted_host,
            uploaded_prior_to=uploaded_prior_to,
            build_isolation=build_isolation,
            resolver_name=resolver_name,
            cache_dir=cache_dir,
            pip_args_str=pip_args_str,
        )
        args = CompileArgs(
            ctx=ctx,
            pip_args=pip_args,
            color=color,
            verbosity=verbose - quiet,
            dry_run=dry_run,
            rebuild=rebuild,
            extras=extras,
            all_extras=all_extras,
            header=header,
            emit_trusted_host=emit_trusted_host,
            annotate=annotate,
            annotation_style=annotation_style,
            upgrade=upgrade,
            upgrade_packages=upgrade_packages,
            newline=newline,
            allow_unsafe=allow_unsafe,
            strip_extras=strip_extras,
            generate_hashes=generate_hashes,
            reuse_hashes=reuse_hashes,
            src_files=src_files,
            max_rounds=max_rounds,
            emit_find_links=emit_find_links,
            emit_index_url=emit_index_url,
            emit_options=emit_options,
            unsafe_package=unsafe_package,
            config=config,
            no_config=no_config,
            constraint=constraint,
            build_deps_targets=build_deps_targets,
            all_build_deps=all_build_deps,
            only_build_deps=only_build_deps,
            _output_file=output_file,
        )

        f(args, ctx, *remainder_args, **remainder_kwargs)

    return wrapper
