from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
import os

from pip.download import PipSession
from pip.index import PackageFinder
from pip.req import parse_requirements

from .. import click
from ..repositories import pypi
from ..logging import log
from .._compat import ExitStack
from ..io import AtomicSaver


DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'


@click.command()
@click.option('-v', '--verbose', is_flag=True, help='Show more output')
@click.option('--dry-run', is_flag=True,
              help="Only show what would happen, don't change anything")
@click.option('-f', '--find-links', multiple=True, envvar='PIP_FIND_LINKS',
              help='Look for archives in this directory or on this HTML page')
@click.option('-i', '--index-url', envvar='PIP_INDEX_URL',
              help='Change index URL (defaults to PyPI)')
@click.option('--extra-index-url', multiple=True, envvar='PIP_EXTRA_INDEX_URL',
              help='Add additional index URL to search')
@click.argument('src_file', required=False, type=click.Path(exists=True),
                default=DEFAULT_REQUIREMENTS_FILE)
def cli(verbose, dry_run, find_links, index_url, extra_index_url, src_file):
    """
    Compiles a list of URLs for each entry in requirements.txt.
    """
    log.verbose = verbose
    if not src_file:
        log.warning('No input files to process')
        sys.exit(2)

    # Configure the finder
    session = PipSession()
    finder = PackageFinder(
        find_links=[],
        index_urls=[pypi.PyPIRepository.DEFAULT_INDEX_URL],
        session=session,
    )

    if index_url:
        finder.index_urls = [index_url]
    finder.index_urls.extend(extra_index_url)
    finder.find_links.extend(find_links)

    log.debug('Using indexes:')
    for index_url in finder.index_urls:
        log.debug('  {}'.format(index_url))

    if finder.find_links:
        log.debug('')
        log.debug('Configuration:')
        for find_link in finder.find_links:
            log.debug('  -f {}'.format(find_link))

    # Parsing/collecting requirements
    ireqs = parse_requirements(src_file, finder=finder, session=session)

    # Output
    base_name, _, _ = src_file.rpartition('.')
    dst_file = base_name + '.urls'

    with ExitStack() as stack:
        f = None
        if not dry_run:
            f = stack.enter_context(AtomicSaver(dst_file))

        for ireq in ireqs:
            if ireq.link:
                link = ireq.link
            else:
                link = finder.find_requirement(ireq, False)
            line = link.url
            log.info(line)
            if f:
                f.write(line.encode('utf-8'))
                f.write(os.linesep.encode('utf-8'))

    if dry_run:
        log.warning('Dry-run, so nothing updated.')
