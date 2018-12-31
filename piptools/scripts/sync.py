# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import os
import sys


from .. import click, sync
from .._compat import parse_requirements, get_installed_distributions, PackageFinder
from ..exceptions import PipToolsError
from ..logging import log
from ..utils import flat_map

DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'


@click.command()
@click.version_option()
@click.option('-n', '--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--force', is_flag=True, help="Proceed even if conflicts are found")
@click.option('-f', '--find-links', multiple=True, help="Look for archives in this directory or on this HTML page", envvar='PIP_FIND_LINKS')  # noqa
@click.option('-i', '--index-url', help="Change index URL (defaults to PyPI)", envvar='PIP_INDEX_URL')
@click.option('--extra-index-url', multiple=True, help="Add additional index URL to search", envvar='PIP_EXTRA_INDEX_URL')  # noqa
@click.option('--no-index', is_flag=True, help="Ignore package index (only looking at --find-links URLs instead)")
@click.option('-q', '--quiet', default=False, is_flag=True, help="Give less output")
@click.option('--user', 'user_only', is_flag=True, help="Restrict attention to user directory")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, find_links, index_url, extra_index_url, no_index, quiet, user_only, src_files):
    """Synchronize virtual environment with requirements.txt."""
    if not src_files:
        if os.path.exists(DEFAULT_REQUIREMENTS_FILE):
            src_files = (DEFAULT_REQUIREMENTS_FILE,)
        else:
            msg = 'No requirement files given and no {} found in the current directory'
            log.error(msg.format(DEFAULT_REQUIREMENTS_FILE))
            sys.exit(2)

    if any(src_file.endswith('.in') for src_file in src_files):
        msg = ('Some input files have the .in extension, which is most likely an error and can '
               'cause weird behaviour.  You probably meant to use the corresponding *.txt file?')
        if force:
            log.warning('WARNING: ' + msg)
        else:
            log.error('ERROR: ' + msg)
            sys.exit(2)

    # Note: Passing in a deque instead of a list as index_urls is a hack to be able
    #       to detect if parse_requirements encountered a --no-index or --index-url
    #       (as opposed to just --extra-index-url flags), in which case it will have
    #       set it to a list during parsing.
    finder = PackageFinder(find_links=[], index_urls=collections.deque(), session=True)

    requirements = flat_map(lambda src: parse_requirements(src, finder=finder, session=True),
                            src_files)

    try:
        requirements = sync.merge(requirements, ignore_conflicts=force)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    installed_dists = get_installed_distributions(skip=[], user_only=user_only)
    to_install, to_uninstall = sync.diff(requirements, installed_dists)

    install_flags = []

    # Install flags from requirements files.
    for link in finder.find_links:
        install_flags.extend(['-f', link])
    if not finder.index_urls and isinstance(finder.index_urls, list):
        install_flags.append('--no-index')
    if finder.index_urls and isinstance(finder.index_urls, list):
        install_flags.extend(['-i', finder.index_urls.pop(0)])
    for extra_index in finder.index_urls:
        install_flags.extend(['--extra-index-url', extra_index])
    if finder.format_control.no_binary:
        install_flags.extend(['--no-binary',
                              ','.join(finder.format_control.no_binary)])
    if finder.format_control.only_binary:
        install_flags.extend(['--only-binary',
                              ','.join(finder.format_control.only_binary)])
    if finder.allow_all_prereleases:
        install_flags.append('--pre')
    if finder.process_dependency_links:
        install_flags.append('--process-dependency-links')
    for host_pattern in finder.secure_origins:
        install_flags.extend(['--trusted-host', host_pattern[1]])

    # Install flags passed on command line.
    for link in find_links or []:
        install_flags.extend(['-f', link])
    if no_index:
        install_flags.append('--no-index')
    if index_url:
        install_flags.extend(['-i', index_url])
    if extra_index_url:
        for extra_index in extra_index_url:
            install_flags.extend(['--extra-index-url', extra_index])
    if user_only:
        install_flags.append('--user')

    sys.exit(sync.sync(to_install, to_uninstall, verbose=(not quiet), dry_run=dry_run,
                       install_flags=install_flags))
