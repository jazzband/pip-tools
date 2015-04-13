from __future__ import absolute_import

import glob
import logging
import sys
from collections import defaultdict

import click
import pip
from pip.download import PipSession
from pip.index import PackageFinder
from pip.req import parse_requirements

from piptools.logging import logger

# from piptools.datastructures import ConflictError
# from collections import defaultdict
# from six import text_type
# from piptools.package_manager import PackageManager
# from piptools.resolver import Resolver

# Make sure we're using a reasonably modern version of pip
if not tuple(int(digit) for digit in pip.__version__.split('.')[:2]) >= (6, 1):
    print('pip-compile requires at least version 6.1 of pip ({} found), '
          'perhaps run `pip install --upgrade pip`?'.format(pip.__version__))
    sys.exit(4)


DEFAULT_REQUIREMENTS_FILE = 'requirements.in'
GLOB_PATTERN = '*requirements.in'


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


def collect_source_specs(filenames):
    """This function collects all of the (primary) source specs into
    a flattened list of specs.
    """
    for filename in filenames:
        for ireq in parse_requirements(filename):
            yield ireq


# def compile_specs(source_files, include_sources=False, dry_run=False):
#     logger.debug('===> Collecting source requirements')
#     top_level_ireqs = list(collect_source_specs(source_files))

#     spec_set = SpecSet()
#     spec_set.add_specs(top_level_ireqs)
#     logger.debug('%s' % (spec_set,))

#     logger.debug('')
#     logger.debug('===> Normalizing source requirements')
#     spec_set = spec_set.normalize()
#     logger.debug('%s' % (spec_set,))

#     package_manager = PackageManager(extra_index_urls, extra_find_links)

#     logger.debug('')
#     logger.debug('===> Resolving full tree')

#     resolver = Resolver(spec_set, package_manager=package_manager)
#     try:
#         pinned_spec_set = resolver.resolve()
#     except ConflictError as e:
#         logger.error('error: {0}'.format(e))
#         sys.exit(1)

#     logger.debug('')
#     logger.debug('===> Pinned spec set resolved')
#     for spec in pinned_spec_set:
#         logger.debug('- %s' % (spec,))

#     if dry_run:
#         return

#     logger.debug('')
#     logger.debug('===> Writing compiled files')

#     # The spec set is global for all files passed to pip-compile. Here we go
#     # through the resolver again (which will use its cache from the initial
#     # run) to determine where to write each dependency.
#     split = defaultdict(SpecSet)
#     for spec in top_level_ireqs:
#         split[spec.source.split(':')[0]].add_spec(spec)

#     for source_file, spec_set in split.items():
#         resolver = Resolver(spec_set, package_manager=package_manager)
#         with logger.silent():
#             local_pinned = resolver.resolve()
#         name, ext = os.path.splitext(source_file)
#         compiled_file = '{0}.txt'.format(name)
#         assert source_file != compiled_file, "Can't overwrite %s" % source_file
#         logger.debug('{0} -> {1}'.format(source_file, compiled_file))
#         with open(compiled_file, 'wb') as f:
#             for spec in sorted(local_pinned, key=text_type):
#                 f.write(text_type(spec).encode('utf-8'))
#                 if include_sources:
#                     f.write(b'  # {}'.format(spec.source))
#                 f.write(b'\n')

#             # Include external PyPi sources
#             if len(extra_index_urls):
#                 for extra_index_url in extra_index_urls:
#                     f.write(b'--extra-index-url {0}\n'.format(extra_index_url))


@click.command()
@click.option('--verbose', '-v', is_flag=True, help="Show more output")
@click.option('--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
# @click.option('--comments', '-c', is_flag=True,
#               help="Write comments to the output file, indicating how the compiled dependencies where calculated")
# @click.option('--prereleases', '-p', is_flag=True,
#               help="Allow prereleases (default is not)")
@click.option('--find-links', '-f', multiple=True, help="Look for archives in this directory or on this HTML page")
@click.option('--extra-index-url', multiple=True, help="Add additional PyPI repo to search")
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def cli(verbose, dry_run, find_links, extra_index_url, files):
    """Compiles requirements.txt from requirements.in specs."""
    src_files = files or glob.glob(GLOB_PATTERN)
    if not src_files:
        click.echo('No input files to process.')
        sys.exit(2)

    session = PipSession()
    finder = PackageFinder(find_links=find_links, index_urls=[], session=session)

    raw_requirements = []
    for src_file in src_files:
        for line in parse_requirements(src_file, finder=finder, session=session):
            raw_requirements.append(line)

    # Finder now contains these settings, populated by parse_requirements()
    finder.index_urls.extend(extra_index_url)

    # Output
    for link in finder.find_links:
        click.echo(' '.join(('-f', link)))
    for url in finder.index_urls:
        click.echo(' '.join(('-i', url)))

    reqlut = defaultdict(list)
    for req in raw_requirements:
        key = req.req.key
        reqlut[key].append(req)

    for req_name, reqs in reqlut.items():
        print(req_name)
        for req in reqs:
            if req.editable:
                click.echo('    -e {0}  # {1}'.format(req.link, req.req.key))
            else:
                click.echo('    {}'.format(req.specifier))
        click.echo()

    # compile_specs(src_files, include_sources=include_sources, dry_run=dry_run)

    # if dry_run:
    #     logger.info('Dry-run, so nothing updated.')
    # else:
    #     logger.info('Dependencies updated.')
