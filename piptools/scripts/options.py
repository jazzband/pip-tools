from __future__ import annotations

import os
import re
import typing as _t

import click
from pip._internal.commands import create_command
from pip._internal.utils.misc import redact_auth_from_url

from piptools.locations import CACHE_DIR, DEFAULT_CONFIG_FILE_NAMES
from piptools.pylock.tool_block import TOOL_FIELDS as _TOOL_FIELDS
from piptools.utils import UNSAFE_PACKAGES, override_defaults_from_config_file

_PYTHON_VERSION_RE = re.compile(
    r"""
    ^ (?P<major> \d+ )                # major version
    \. (?P<minor> \d+ )               # minor version
    (?: \. (?P<patch> \d+ ) )?        # optional patch version
    $
    """,
    re.VERBOSE,
)


def _validate_python_versions(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    for version in value:
        # ``current`` is a valid shorthand expanded by ``resolve_targets``
        # to the host's ``MAJOR.MINOR``, mirroring ``--platform current``.
        # Saves the user from looking up their interpreter version.
        if version == "current":
            continue
        if not _PYTHON_VERSION_RE.fullmatch(version):
            raise click.BadParameter(
                f"{value!r}: --python-version expects MAJOR.MINOR or "
                f"MAJOR.MINOR.PATCH (e.g. 3.12 or 3.12.5) or 'current'",
                ctx=ctx,
                param=param,
            )
    return value


_FC = _t.TypeVar("_FC", bound="_t.Callable[..., _t.Any] | click.Command")

BuildTargetT = _t.Literal["sdist", "wheel", "editable"]
ALL_BUILD_TARGETS: tuple[BuildTargetT, ...] = (
    "editable",
    "sdist",
    "wheel",
)


def help_option(*, epilog: str | None = None) -> _t.Callable[[_FC], _FC]:
    """A variant of the built-in click ``--help`` option, customized for pip-tools.

    Unlike ``click.help_option``, this decorator accepts its own ``epilog`` text which
    is printed *without indentation* after help text.
    """

    def show_help(ctx: click.Context, param: click.Parameter, value: bool) -> None:
        """Callback that print the help page on ``<stdout>`` and exits."""
        if value and not ctx.resilient_parsing:
            click.echo(ctx.get_help(), color=ctx.color)
            if epilog is not None:
                formatter = ctx.make_formatter()
                formatter.write_text(epilog)
                click.echo("\n" + formatter.getvalue().rstrip("\n"), color=ctx.color)
            ctx.exit()

    return click.option(  # type: ignore[return-value]
        "-h",
        "--help",
        help="Show this message and exit.",
        callback=show_help,
        is_eager=True,
        expose_value=False,
        is_flag=True,
    )


def _get_default_option(option_name: str) -> _t.Any:
    """
    Get default value of the pip's option (including option from pip.conf)
    by a given option name.
    """
    install_command = create_command("install")
    default_values = install_command.parser.get_default_values()
    return getattr(default_values, option_name)


# The options used by pip-compile and pip-sync are presented in no specific order.

version = click.version_option(package_name="pip-tools")

color = click.option(
    "--color/--no-color",
    default=None,
    help="Force output to be colorized or not, instead of auto-detecting color support",
)

verbose = click.option(
    "-v",
    "--verbose",
    count=True,
    help="Show more output",
)
quiet = click.option(
    "-q",
    "--quiet",
    count=True,
    help="Give less output",
)

dry_run = click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Only show what would happen, don't change anything",
)

pre = click.option(
    "-p",
    "--pre",
    is_flag=True,
    default=None,
    help="Allow resolving to prereleases (default is not)",
)

rebuild = click.option(
    "-r",
    "--rebuild",
    is_flag=True,
    help="Clear any caches upfront, rebuild from scratch",
)

extra = click.option(
    "--extra",
    "extras",
    multiple=True,
    help=(
        "Name of an extras_require group to install; may be used more than "
        "once. Pass ``--all-extras`` to include every declared extra."
    ),
)

all_extras = click.option(
    "--all-extras",
    is_flag=True,
    default=False,
    help="Install all extras_require groups (see also: ``--extra`` for one at a time)",
)

find_links = click.option(
    "-f",
    "--find-links",
    multiple=True,
    help="Look for archives in this directory or on this HTML page; may be used more than once",
)

index_url = click.option(
    "-i",
    "--index-url",
    help="Change index URL (defaults to {index_url})".format(
        index_url=redact_auth_from_url(_get_default_option("index_url"))
    ),
)

no_index = click.option(
    "--no-index",
    is_flag=True,
    help="Ignore package index (only looking at --find-links URLs instead).",
)

extra_index_url = click.option(
    "--extra-index-url",
    multiple=True,
    help="Add another index URL to search; may be used more than once",
)

cert = click.option("--cert", help="Path to alternate CA bundle.")

client_cert = click.option(
    "--client-cert",
    help=(
        "Path to SSL client certificate, a single file containing "
        "the private key and the certificate in PEM format."
    ),
)

trusted_host = click.option(
    "--trusted-host",
    multiple=True,
    help=(
        "Mark this host as trusted, even though it does not have "
        "valid or any HTTPS; may be used more than once"
    ),
)

uploaded_prior_to = click.option(
    "--uploaded-prior-to",
    default=None,
    help=(
        "Only consider package versions uploaded prior to the given date/time. "
        "Accepts ISO 8601 strings (e.g., '2023-01-01T00:00:00Z'). "
        "Requires pip >= 26.0."
    ),
)

header = click.option(
    "--header/--no-header",
    is_flag=True,
    default=True,
    help="Add header to generated file",
)

emit_trusted_host = click.option(
    "--emit-trusted-host/--no-emit-trusted-host",
    is_flag=True,
    default=True,
    help="Add trusted host option to generated file",
)

annotate = click.option(
    "--annotate/--no-annotate",
    is_flag=True,
    default=True,
    help="Annotate results, indicating where dependencies come from",
)

annotation_style = click.option(
    "--annotation-style",
    type=click.Choice(("line", "split")),
    default="split",
    help="Choose the format of annotation comments",
)

upgrade = click.option(
    "-U",
    "--upgrade/--no-upgrade",
    is_flag=True,
    default=False,
    help="Try to upgrade all dependencies to their latest versions",
)

upgrade_package = click.option(
    "-P",
    "--upgrade-package",
    "upgrade_packages",
    nargs=1,
    multiple=True,
    help=(
        "Re-resolve the named package against the index, ignoring any pin "
        "from the existing requirements file or lockfile. May be used more "
        "than once. Other packages keep their seeded pins."
    ),
)

upgrade_lock = click.option(
    "-U",
    "--upgrade/--no-upgrade",
    "upgrade_lock",
    is_flag=True,
    default=False,
    help=(
        "Re-resolve every package, ignoring pins from any existing "
        "``pylock.toml``. Without this flag the existing lock seeds "
        "constraints so unrelated packages don't churn; pass "
        "``--upgrade-package <name>`` to upgrade just one."
    ),
)

check = click.option(
    "--check",
    is_flag=True,
    default=False,
    help=(
        "Re-resolve in memory and exit non-zero if the result differs from "
        "the existing ``pylock.toml``. Use in CI to detect lockfile drift "
        "without writing the file. Mirrors ``uv lock --check``."
    ),
)

output_file = click.option(
    "-o",
    "--output-file",
    nargs=1,
    default=None,
    type=click.File("w+b", atomic=True, lazy=True),
    help=(
        "Output file name. Required if more than one input file is given. "
        "Will be derived from input file otherwise."
    ),
)

newline = click.option(
    "--newline",
    type=click.Choice(("LF", "CRLF", "native", "preserve"), case_sensitive=False),
    default="preserve",
    help="Override the newline control characters used",
)

allow_unsafe = click.option(
    "--allow-unsafe/--no-allow-unsafe",
    is_flag=True,
    default=False,
    help=(
        "Pin packages considered unsafe: {}.\n\n"
        "WARNING: Future versions of pip-tools will enable this behavior by default. "
        "Use --no-allow-unsafe to keep the old behavior. It is recommended to pass the "
        "--allow-unsafe now to adapt to the upcoming change.".format(
            ", ".join(sorted(UNSAFE_PACKAGES))
        )
    ),
)

strip_extras = click.option(
    "--strip-extras/--no-strip-extras",
    is_flag=True,
    default=None,
    help="Assure output file is constraints compatible, avoiding use of extras.",
)

generate_hashes = click.option(
    "--generate-hashes",
    is_flag=True,
    default=False,
    help="Generate pip 8 style hashes in the resulting requirements file.",
)

reuse_hashes = click.option(
    "--reuse-hashes/--no-reuse-hashes",
    is_flag=True,
    default=True,
    help=(
        "Improve the speed of --generate-hashes by reusing the hashes from an "
        "existing output file."
    ),
)

max_rounds = click.option(
    "--max-rounds",
    default=10,
    help="Maximum number of rounds before resolving the requirements aborts.",
)


def _parse_jobs(ctx: click.Context, param: click.Parameter, value: str) -> int:
    """Parse the ``--jobs`` argument: integer >= 1, or ``auto`` for cpu_count."""
    if value == "auto":
        return os.cpu_count() or 1
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise click.BadParameter(f"expected an integer or 'auto', got {value!r}")
    if parsed < 1:
        raise click.BadParameter("must be at least 1")
    return parsed


jobs = click.option(
    "--jobs",
    "-j",
    default="auto",
    callback=_parse_jobs,
    help=(
        "Number of resolution cohorts to lock in parallel. Pass an integer "
        "or 'auto' (the count of available CPUs, the default). Workers are "
        "processes; the value is capped at the number of cohorts, and the "
        "dispatch runs in-process when the cap is 1 (no worker fork)."
    ),
)


src_files = click.argument(
    "src_files",
    nargs=-1,
    type=click.Path(exists=True, allow_dash=True),
)

build_isolation = click.option(
    "--build-isolation/--no-build-isolation",
    is_flag=True,
    default=True,
    help=(
        "Enable isolation when building a modern source distribution. With "
        "``--no-build-isolation`` you must pre-install every PEP 518 build "
        "dependency (``setuptools``, ``wheel``, ``hatchling``, etc.) into "
        "the active environment; missing build deps surface as "
        "import errors during the backend invocation, far from the "
        "underlying cause."
    ),
)

emit_find_links = click.option(
    "--emit-find-links/--no-emit-find-links",
    is_flag=True,
    default=True,
    help="Add the find-links option to generated file",
)

cache_dir = click.option(
    "--cache-dir",
    help="Store the cache data in DIRECTORY.",
    default=CACHE_DIR,
    envvar="PIP_TOOLS_CACHE_DIR",
    show_default=True,
    show_envvar=True,
    type=click.Path(file_okay=False, writable=True),
)

pip_args = click.option(
    "--pip-args",
    "pip_args_str",
    help="Arguments to pass directly to the pip command.",
)

resolver = click.option(
    "--resolver",
    "resolver_name",
    type=click.Choice(("legacy", "backtracking")),
    default="backtracking",
    envvar="PIP_TOOLS_RESOLVER",
    help="Choose the dependency resolver.",
)

emit_index_url = click.option(
    "--emit-index-url/--no-emit-index-url",
    is_flag=True,
    default=True,
    help="Add index URL to generated file",
)

emit_options = click.option(
    "--emit-options/--no-emit-options",
    is_flag=True,
    default=True,
    help="Add options to generated file",
)

unsafe_package = click.option(
    "--unsafe-package",
    multiple=True,
    help=(
        "Specify a package to consider unsafe; may be used more than once. "
        f"Replaces default unsafe packages: {', '.join(sorted(UNSAFE_PACKAGES))}"
    ),
)

config = click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        allow_dash=False,
        path_type=str,
    ),
    help=(
        f"Read configuration from TOML file. By default, looks for the following "
        f"files in the given order: {', '.join(DEFAULT_CONFIG_FILE_NAMES)}."
    ),
    is_eager=True,
    callback=override_defaults_from_config_file,
)

no_config = click.option(
    "--no-config",
    is_flag=True,
    default=False,
    help="Do not read any config file.",
    is_eager=True,
)

constraint = click.option(
    "-c",
    "--constraint",
    multiple=True,
    help="Constrain versions using the given constraints file; may be used more than once.",
)

ask = click.option(
    "-a",
    "--ask",
    is_flag=True,
    help="Show what would happen, then ask whether to continue",
)

force = click.option(
    "--force", is_flag=True, help="Proceed even if conflicts are found"
)

python_executable = click.option(
    "--python-executable",
    help="Custom python executable path if targeting an environment other than current.",
)

user = click.option(
    "--user",
    "user_only",
    is_flag=True,
    help="Restrict attention to user directory",
)

build_deps_for = click.option(
    "--build-deps-for",
    "build_deps_targets",
    multiple=True,
    type=click.Choice(ALL_BUILD_TARGETS),
    help="Name of a build target to extract dependencies for. "
    "Static dependencies declared in 'pyproject.toml::build-system.requires' will be included as "
    "well; may be used more than once.",
)

all_build_deps = click.option(
    "--all-build-deps",
    is_flag=True,
    default=False,
    help="Extract dependencies for all build targets. "
    "Static dependencies declared in 'pyproject.toml::build-system.requires' will be included as "
    "well.",
)

only_build_deps = click.option(
    "--only-build-deps",
    is_flag=True,
    default=False,
    help="Extract a package only if it is a build dependency.",
)

group = click.option(
    "--group",
    "groups",
    multiple=True,
    help=(
        "Name of a dependency group to include; may be used more than once. "
        "Pass ``--all-groups`` to include every declared group."
    ),
)

all_groups = click.option(
    "--all-groups",
    is_flag=True,
    default=False,
    help=(
        "Include all dependency groups defined in pyproject.toml "
        "(cf. ``--group`` for one at a time)"
    ),
)


def _platform_choices() -> tuple[str, ...]:
    # Sourced from `PLATFORM_ENVIRONMENTS` so the click choice and the
    # env lookup table never drift apart. ``current`` is the host's
    # auto-detected preset, which spares the user from spelling out
    # ``linux-x86_64`` etc. for one-off "lock for what I'm on now" runs.
    from piptools.pylock.platforms import PLATFORM_ENVIRONMENTS

    return ("current", *sorted(PLATFORM_ENVIRONMENTS))


def _validate_platform(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    """Accept the built-in choices, ``current``, or any ``<os>-<arch>`` shape.

    Restricting strictly to ``PLATFORM_ENVIRONMENTS`` means users on FreeBSD,
    OpenBSD, AIX, Solaris, and similar can't lock with ``--no-universal``;
    relaxing to ``<os>-<arch>`` lets them name the target while a sibling
    helper in ``platforms.py`` deduces best-effort markers.
    """
    from piptools.pylock.platforms import PLATFORM_ENVIRONMENTS

    valid = {"current", *PLATFORM_ENVIRONMENTS}
    canonical: list[str] = []
    for raw in value:
        # Canonicalise to lowercase before matching: ``LINUX-X86_64``
        # and ``linux-x86_64`` would otherwise both pass (the first via
        # the ``<os>-<arch>`` fallback as a synthesised platform, the
        # second through the built-in preset) and the lockfile would
        # carry both near-duplicates.
        normalised = raw.lower()
        if normalised in valid:
            canonical.append(normalised)
            continue
        os_name, sep, arch = normalised.partition("-")
        if not sep or not os_name or not arch:
            raise click.BadParameter(
                f"unknown platform {raw!r}; expected one of "
                f"{sorted(PLATFORM_ENVIRONMENTS)} or an ``<os>-<arch>`` "
                f"string (e.g. ``freebsd-amd64``). Both halves must be "
                f"non-empty so the synthesised marker has a real "
                f"``platform_machine`` value.",
                param_hint="--platform",
            )
        canonical.append(normalised)
    return tuple(canonical)


platform = click.option(
    "--platform",
    "platforms",
    multiple=True,
    callback=_validate_platform,
    help=(
        "Target platform for cross-platform resolution; may be used more "
        "than once. Pass 'current' to target the host's auto-detected "
        "preset, or any ``<os>-<arch>`` string to lock for a platform "
        "outside the built-in presets (best-effort markers). Pass "
        "``--no-universal`` to skip cross-platform resolution entirely."
    ),
)

python_version = click.option(
    "--python-version",
    "python_versions",
    multiple=True,
    callback=_validate_python_versions,
    help="Target Python version (e.g., 3.12 or 3.12.5); may be used more than once.",
)

implementation = click.option(
    "--implementation",
    "implementations",
    multiple=True,
    default=("cpython",),
    show_default=True,
    help=(
        "Target Python implementation (e.g., cpython, pypy, graalpy); may be "
        "used more than once. Defaults to ``cpython``."
    ),
)

no_universal = click.option(
    "--no-universal",
    is_flag=True,
    default=False,
    help=(
        "Resolve for current platform only instead of cross-platform. "
        "Use ``--platform`` to pick specific targets."
    ),
)

no_metadata = click.option(
    "--no-metadata/--metadata",
    "--no-tool-block/--tool-block",
    "no_metadata",
    is_flag=True,
    default=False,
    help=(
        "Suppress the entire [tool.pip-tools] metadata block. The "
        "--no-tool-block alias is the clearer name (this affects only the "
        "tool-private block, not PEP 751 packages metadata). May be combined "
        "with --skip-metadata-field; suppressing the whole block wins."
    ),
)

skip_metadata_fields = click.option(
    "--skip-metadata-field",
    "skip_metadata_fields",
    multiple=True,
    type=click.Choice(tuple(sorted(_TOOL_FIELDS)), case_sensitive=True),
    help=(
        "Omit a field from the [tool.pip-tools] metadata block; may be used "
        "more than once. Omitting all fields suppresses the block entirely. "
        "Useful for reproducible lock files where volatile values would cause "
        "spurious diffs."
    ),
)
