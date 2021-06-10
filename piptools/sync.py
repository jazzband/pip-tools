import collections
import json
import os
import sys
import tempfile
from pathlib import Path
from subprocess import run  # nosec
from typing import (
    Deque,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    ValuesView,
)

import click
from pip._internal.commands.freeze import DEV_PKGS
from pip._internal.locations import get_src_prefix
from pip._internal.operations.prepare import unpack_vcs_link
from pip._internal.req import InstallRequirement
from pip._internal.utils.compat import stdlib_pkgs
from pip._internal.utils.parallel import map_multithread
from pip._internal.utils.temp_dir import TempDirectory, global_tempdir_manager
from pip._internal.vcs import vcs
from pip._vendor.pkg_resources import Distribution, WorkingSet

from .exceptions import IncompatibleRequirements
from .logging import log
from .utils import (
    flat_map,
    format_requirement,
    get_hashes_from_ireq,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
)

PACKAGES_TO_IGNORE = [
    "-markerlib",
    "pip",
    "pip-tools",
    "pip-review",
    "pkg-resources",
    *stdlib_pkgs,
    *DEV_PKGS,
]

VCS_INFO_METADATA_FILE_NAME = "PIP_TOOLS_VCS_INFO"


def dependency_tree(
    installed_keys: Mapping[str, Distribution], root_key: str
) -> Set[str]:
    """
    Calculate the dependency tree for the package `root_key` and return
    a collection of all its dependencies.  Uses a DFS traversal algorithm.

    `installed_keys` should be a {key: requirement} mapping, e.g.
        {'django': from_line('django==1.8')}
    `root_key` should be the key to return the dependency tree for.
    """
    dependencies = set()
    queue: Deque[Distribution] = collections.deque()

    if root_key in installed_keys:
        dep = installed_keys[root_key]
        queue.append(dep)

    while queue:
        v = queue.popleft()
        key = key_from_req(v)
        if key in dependencies:
            continue

        dependencies.add(key)

        for dep_specifier in v.requires():
            dep_name = key_from_req(dep_specifier)
            if dep_name in installed_keys:
                dep = installed_keys[dep_name]

                if dep_specifier.specifier.contains(dep.version):
                    queue.append(dep)

    return dependencies


def get_dists_to_ignore(installed: Iterable[Distribution]) -> List[str]:
    """
    Returns a collection of package names to ignore when performing pip-sync,
    based on the currently installed environment.  For example, when pip-tools
    is installed in the local environment, it should be ignored, including all
    of its dependencies (e.g. click).  When pip-tools is not installed
    locally, click should also be installed/uninstalled depending on the given
    requirements.
    """
    installed_keys = {key_from_req(d): d for d in installed}
    return list(
        flat_map(lambda dist: dependency_tree(installed_keys, dist), PACKAGES_TO_IGNORE)
    )


def merge(
    requirements: Iterable[InstallRequirement], ignore_conflicts: bool
) -> ValuesView[InstallRequirement]:
    by_key: Dict[str, InstallRequirement] = {}

    for ireq in requirements:
        # Limitation: URL requirements are merged by precise string match, so
        # "file:///example.zip#egg=example", "file:///example.zip", and
        # "example==1.0" will not merge with each other
        if ireq.match_markers():
            key = key_from_ireq(ireq)

            if not ignore_conflicts:
                existing_ireq = by_key.get(key)
                if existing_ireq:
                    # NOTE: We check equality here since we can assume that the
                    # requirements are all pinned
                    if ireq.specifier != existing_ireq.specifier:
                        raise IncompatibleRequirements(ireq, existing_ireq)

            # TODO: Always pick the largest specifier in case of a conflict
            by_key[key] = ireq
    return by_key.values()


def diff_key_from_ireq(ireq: InstallRequirement) -> str:
    """
    Calculate a key for comparing a compiled requirement with installed modules.
    For URL requirements, only provide a useful key if the url includes
    #egg=name==version, which will set ireq.req.name and ireq.specifier.
    Otherwise return ireq.link so the key will not match and the package will
    reinstall. Reinstall is necessary to ensure that packages will reinstall
    if the URL is changed but the version is not.
    """
    if is_url_requirement(ireq):
        if (
            ireq.req
            and (getattr(ireq.req, "key", None) or getattr(ireq.req, "name", None))
            and ireq.specifier
        ):
            return key_from_ireq(ireq)
        return str(ireq.link)
    return key_from_ireq(ireq)


class VcsInfo(NamedTuple):
    """Stores relevant information about a VCS installation.

    Used to determine if two VCS installations are/would be equivalent,
    since things like version aren't reliable for VCS because the version
    may be the same across two different commits.

    Can be converted to/from a string using the `serialize` and `deserialize` methods.
    """

    url: str
    revision: str

    @classmethod
    def deserialize(cls, serialized: str) -> "VcsInfo":
        return VcsInfo(**json.loads(serialized))

    def serialize(self) -> str:
        return json.dumps(self._asdict())


def _reload_installed_distributions_by_key() -> Mapping[str, Distribution]:
    """
    Reload `site` to pick up new `sys.path` entries from newly installed packages,
    then create a new `WorkingSet` to see all those packages. The `site` reload is
    particularly important for newly installed editable packages.
    """
    import site
    from importlib import reload

    reload(site)
    ws = WorkingSet()
    return ws.by_key  # type: ignore[no-any-return]


def _write_vcs_infos_to_env_where_relevant(
    installed: Iterable[InstallRequirement],
) -> None:
    """Munge installed VCS packages to have VCS info.

    For each VCS ireq, will write a special metadata file to the installed
    distribution containing the VCS information about the package. This information
    can be read with the corresponding `_read_vcs_info_from_env` method and used to
    determine whether or not a VCS package actually needs to be reinstalled. In the
    case of non-editable distributions, this will also update the `RECORD` file so it
    knows about the newly written metadata file.

    Note that this will (re)fetch VCS information from the given ireq, since by
    definition the information is not stored in the installed package (otherwise
    there'd be no need to do this).

    Runs each given ireq in parallel.
    """
    installed_distributions_by_key = _reload_installed_distributions_by_key()

    def write_vcs_info_to_env_if_relevant(ireq: InstallRequirement) -> None:
        vcs_info = _fetch_vcs_info_for_ireq(ireq)
        if vcs_info is None:
            # Nothing to write
            return

        dist = installed_distributions_by_key.get(key_from_ireq(ireq))
        if dist is None:
            # Not actually installed (shouldn't happen?)
            return

        # Actually write the metadata file
        vcs_info_path = Path(
            dist._provider._get_metadata_path(VCS_INFO_METADATA_FILE_NAME)
        )
        vcs_info_path.write_text(vcs_info.serialize())

        # Update the RECORD file if present (eg for non-editable installs).
        record_path = Path(dist._provider._get_metadata_path("RECORD"))
        if not record_path.is_file():
            return
        record_entry = vcs_info_path.relative_to(record_path.parents[1])
        record_contents = record_path.read_text()
        if str(record_entry) not in record_contents:
            record_contents = (
                record_contents.rstrip(os.linesep)
                + f"{os.linesep}{record_entry},,{os.linesep}"
            )
            record_path.write_text(record_contents)

    with global_tempdir_manager():
        map_multithread(func=write_vcs_info_to_env_if_relevant, iterable=installed)


def _read_vcs_info_from_env(dist: Optional[Distribution]) -> Optional[VcsInfo]:
    """Read VCS info for the given installed package.

    Will read and return VCS info from the special metadata file written by
    `_write_vcs_infos_to_env_where_relevant`. If the package isn't installed,
    doesn't have VCS info written in it, or the VCS info can't be deserialized
    properly this will return None.
    """
    if dist is None:
        # Not installed in local env
        return None

    vcs_info_path = Path(dist._provider._get_metadata_path(VCS_INFO_METADATA_FILE_NAME))
    if not vcs_info_path.is_file():
        # Couldn't find special metadata file
        return None

    try:
        return VcsInfo.deserialize(vcs_info_path.read_text())
    except TypeError:
        # Eg if the format changes since it's last been serialized
        return None


def _fetch_vcs_info_for_ireq(ireq: InstallRequirement) -> Optional[VcsInfo]:
    """Calculate VCS info for a given ireq.

    Will go through the steps to prepare the ireq for installation (namely clone it
    down/update any existing clones) and fetch the revision from that prepared
    location to calculate the VCS info. Will return None for non-VCS ireqs.

    Expects a pip global tempdir manager to be active.
    """
    if ireq.link is None or not ireq.link.is_vcs:
        return None

    # Setup the ireq's source directory
    if ireq.editable:
        ireq.ensure_has_source_dir(get_src_prefix())
        ireq.update_editable()
    else:
        build_dir = TempDirectory(delete=True, kind="install", globally_managed=True)
        ireq.ensure_has_source_dir(
            build_dir.path, autodelete=True, parallel_builds=True
        )
        unpack_vcs_link(ireq.link, ireq.source_dir)

    # Get the revision from the package.
    vcs_backend = vcs.get_backend_for_scheme(ireq.link.scheme)
    assert vcs_backend is not None
    revision = vcs_backend.get_revision(ireq.source_dir)

    return VcsInfo(url=ireq.link.url, revision=revision)


def _ignore_same_revision_vcs_packages(
    to_install: Set[InstallRequirement],
    to_uninstall: Set[str],
    installed_dists: Iterable[Distribution],
) -> None:
    """Filter out VCS packages that are reinstalled at the same revision.

    This finds VCS packages that are in both `to_install` and `to_uninstall` and have
    matching VCS info and removes them from both sets, so that we can have faster no-op
    syncs by avoiding the unnecessary reinstall.

    Processes packages in parallel.
    """
    installed_dists_by_key = {key_from_req(d): d for d in installed_dists}

    def get_pairs_to_ignore(
        ireq: InstallRequirement,
    ) -> Optional[Tuple[InstallRequirement, str]]:
        # Find uninstall+reinstall pairs where they share a name...
        key = key_from_ireq(ireq)
        if key not in to_uninstall:
            return None
        # ...and uninstall has VCS info...
        installed_dist = installed_dists_by_key.get(key)
        existing_vcs_info = _read_vcs_info_from_env(installed_dist)
        if existing_vcs_info is None:
            return None
        # ...and install has matching VCS info.
        new_vcs_info = _fetch_vcs_info_for_ireq(ireq)
        if new_vcs_info != existing_vcs_info:
            return None

        return ireq, key

    with global_tempdir_manager():
        to_ignore = [
            pair
            for pair in map_multithread(
                func=get_pairs_to_ignore, iterable=to_install, chunksize=1
            )
            if pair is not None
        ]

    for ignore_install, ignore_uninstall in to_ignore:
        to_install.remove(ignore_install)
        to_uninstall.remove(ignore_uninstall)


def diff(
    compiled_requirements: Iterable[InstallRequirement],
    installed_dists: Iterable[Distribution],
) -> Tuple[Set[InstallRequirement], Set[str]]:
    """
    Calculate which packages should be installed or uninstalled, given a set
    of compiled requirements and a list of currently installed modules.
    """
    requirements_lut = {diff_key_from_ireq(r): r for r in compiled_requirements}

    satisfied = set()  # holds keys
    to_install = set()  # holds InstallRequirement objects
    to_uninstall = set()  # holds keys

    pkgs_to_ignore = get_dists_to_ignore(installed_dists)
    for dist in installed_dists:
        key = key_from_req(dist)
        if key not in requirements_lut or not requirements_lut[key].match_markers():
            to_uninstall.add(key)
        elif requirements_lut[key].specifier.contains(dist.version):
            satisfied.add(key)

    for key, requirement in requirements_lut.items():
        if key not in satisfied and requirement.match_markers():
            to_install.add(requirement)

    # Make sure to not uninstall any packages that should be ignored
    to_uninstall -= set(pkgs_to_ignore)

    _ignore_same_revision_vcs_packages(to_install, to_uninstall, installed_dists)

    return (to_install, to_uninstall)


def sync(
    to_install: Iterable[InstallRequirement],
    to_uninstall: Iterable[InstallRequirement],
    dry_run: bool = False,
    install_flags: Optional[List[str]] = None,
    ask: bool = False,
    python_executable: Optional[str] = None,
) -> int:
    """
    Install and uninstalls the given sets of modules.
    """
    exit_code = 0

    python_executable = python_executable or sys.executable

    if not to_uninstall and not to_install:
        log.info("Everything up-to-date", err=False)
        return exit_code

    pip_flags = []
    if log.verbosity < 0:
        pip_flags += ["-q"]

    if ask:
        dry_run = True

    if dry_run:
        if to_uninstall:
            click.echo("Would uninstall:")
            for pkg in sorted(to_uninstall):
                click.echo(f"  {pkg}")

        if to_install:
            click.echo("Would install:")
            for ireq in sorted(to_install, key=key_from_ireq):
                click.echo(f"  {format_requirement(ireq)}")

        exit_code = 1

    if ask and click.confirm("Would you like to proceed with these changes?"):
        dry_run = False
        exit_code = 0

    if not dry_run:
        if to_uninstall:
            run(  # nosec
                [
                    python_executable,
                    "-m",
                    "pip",
                    "uninstall",
                    "-y",
                    *pip_flags,
                    *sorted(to_uninstall),
                ],
                check=True,
            )

        if to_install:
            if install_flags is None:
                install_flags = []
            # prepare requirement lines
            req_lines = []
            for ireq in sorted(to_install, key=key_from_ireq):
                ireq_hashes = get_hashes_from_ireq(ireq)
                req_lines.append(format_requirement(ireq, hashes=ireq_hashes))

            # save requirement lines to a temporary file
            tmp_req_file = tempfile.NamedTemporaryFile(mode="wt", delete=False)
            tmp_req_file.write("\n".join(req_lines))
            tmp_req_file.close()

            try:
                run(  # nosec
                    [
                        python_executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        tmp_req_file.name,
                        *pip_flags,
                        *install_flags,
                    ],
                    check=True,
                )
            finally:
                os.unlink(tmp_req_file.name)

            _write_vcs_infos_to_env_where_relevant(to_install)

    return exit_code
