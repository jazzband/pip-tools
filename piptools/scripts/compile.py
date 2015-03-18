from __future__ import absolute_import
from collections import defaultdict

import click
import glob
import logging
import os
import sys
import re

from piptools.datastructures import Spec, SpecSet, ConflictError
from piptools.logging import logger
from piptools.package_manager import PackageManager
from piptools.resolver import Resolver

from six import text_type


DEFAULT_REQUIREMENTS_FILE = 'requirements.in'
GLOB_PATTERN = '*requirements.in'


# Track external PyPi repos referenced
extra_index_urls = []
extra_find_links = []


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s', None)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    from pip import logger as pip_logger
    if hasattr(pip_logger, 'addHandler'):
        # New method from pip 6 onwards.
        pip_formatter = logging.Formatter('PIP said: %(message)s', None)
        pip_handler = logging.StreamHandler()
        pip_handler.setFormatter(pip_formatter)
        pip_handler.setLevel(level)
        pip_logger.addHandler(pip_handler)
    else:
        # Old method, removed in 767d11e (tags/6.0~104^2).
        pip_logger.consumers.append(
            (pip_logger.VERBOSE_DEBUG,
             lambda msg: logger.debug('PIP said: ' + msg)))


def walk_specfile(filename):
    """Walks over the given file, and returns (req, filename, lineno)
    tuples for each entry.
    """
    with open(filename, 'rb') as f:
        reqs = f.read()

    for lineno, line in enumerate(reqs.splitlines(), 1):
        line = line.strip().decode('utf-8')
        if not line or line.startswith('#'):
            continue

        if line.startswith('-r'):
            requirement = line.split(None, 1)[1]
            # requirement file is relative to processed one
            requirement = os.path.join(os.path.dirname(filename), requirement)

            for spec in walk_specfile(requirement):
                yield spec.add_source('{0}:{1} -> {2}'.format(filename, lineno, spec.source))
        elif line.startswith('-f'):
            extra_find_links.append(line.split(None, 1)[1])
        elif line.startswith('--extra-index-url'):
            repo = re.split('=| ', line)
            if len(repo) > 1:
                repo = repo[1]
                logger.debug('Found a link to additional PyPi repo -> {0}'.format(repo))
                if repo not in extra_index_urls:
                    extra_index_urls.append(repo)
        else:
            spec = Spec.from_line(line, source='{0}:{1}'.format(filename, lineno))
            yield spec


def collect_source_specs(filenames):
    """This function collects all of the (primary) source specs into
    a flattened list of specs.
    """
    for filename in filenames:
        for spec in walk_specfile(filename):
            yield spec


def compile_specs(source_files, include_sources=False, dry_run=False):
    logger.debug('===> Collecting source requirements')
    top_level_specs = list(collect_source_specs(source_files))

    spec_set = SpecSet()
    spec_set.add_specs(top_level_specs)
    logger.debug('%s' % (spec_set,))

    logger.debug('')
    logger.debug('===> Normalizing source requirements')
    spec_set = spec_set.normalize()
    logger.debug('%s' % (spec_set,))

    package_manager = PackageManager(extra_index_urls, extra_find_links)

    logger.debug('')
    logger.debug('===> Resolving full tree')

    resolver = Resolver(spec_set, package_manager=package_manager)
    try:
        pinned_spec_set = resolver.resolve()
    except ConflictError as e:
        logger.error('error: {0}'.format(e))
        sys.exit(1)

    logger.debug('')
    logger.debug('===> Pinned spec set resolved')
    for spec in pinned_spec_set:
        logger.debug('- %s' % (spec,))

    if dry_run:
        return

    logger.debug('')
    logger.debug('===> Writing compiled files')

    # The spec set is global for all files passed to pip-compile. Here we go
    # through the resolver again (which will use its cache from the initial
    # run) to determine where to write each dependency.
    split = defaultdict(SpecSet)
    for spec in top_level_specs:
        split[spec.source.split(':')[0]].add_spec(spec)

    for source_file, spec_set in split.items():
        resolver = Resolver(spec_set, package_manager=package_manager)
        with logger.silent():
            local_pinned = resolver.resolve()
        name, ext = os.path.splitext(source_file)
        compiled_file = '{0}.txt'.format(name)
        assert source_file != compiled_file, "Can't overwrite %s" % source_file
        logger.debug('{0} -> {1}'.format(source_file, compiled_file))
        with open(compiled_file, 'wb') as f:
            for spec in sorted(local_pinned, key=text_type):
                f.write(text_type(spec).encode('utf-8'))
                if include_sources:
                    f.write(b'  # {}'.format(spec.source))
                f.write(b'\n')

            # Include external PyPi sources
            if len(extra_index_urls):
                for extra_index_url in extra_index_urls:
                    f.write(b'--extra-index-url {0}\n'.format(extra_index_url))


@click.command()
@click.option('--verbose', '-v', is_flag=True, help="Show more output")
@click.option('--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--include-sources', '-i', is_flag=True,
              help="Write comments to the output file, indicating how the compiled dependencies where calculated")
@click.option('--find-links', '-f', help="Look for archives in this directory or on this HTML page", multiple=True)
@click.option('--extra-index-url', default=None, help="Add additional PyPi repo to search")
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def cli(verbose, dry_run, include_sources, find_links, extra_index_url, files):
    """Compiles requirements.txt from requirements.in specs."""
    setup_logging(verbose)

    if find_links:
        extra_find_links.extend(find_links)

    if extra_index_url:
        urls = extra_index_url.split(',')
        extra_index_urls.extend(urls)

    src_files = files or glob.glob(GLOB_PATTERN)
    if not src_files:
        click.echo('No input files to process.')
        sys.exit(2)

    compile_specs(src_files, include_sources=include_sources, dry_run=dry_run)

    if dry_run:
        logger.info('Dry-run, so nothing updated.')
    else:
        logger.info('Dependencies updated.')
