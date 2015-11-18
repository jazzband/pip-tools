# coding: utf-8
# isort:skip_file
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import optparse
import sys
import pip

# Make sure we're using a reasonably modern version of pip
if not tuple(int(digit) for digit in pip.__version__.split('.')[:2]) >= (6, 1):
    print('pip-compile requires at least version 6.1 of pip ({} found), '
          'perhaps run `pip install --upgrade pip`?'.format(pip.__version__))
    sys.exit(4)

from .. import click  # noqa
from pip.req import parse_requirements  # noqa

from ..exceptions import PipToolsError  # noqa
from ..logging import log  # noqa
from ..repositories import PyPIRepository  # noqa
from ..resolver import Resolver  # noqa
from ..writer import OutputWriter  # noqa

DEFAULT_REQUIREMENTS_FILE = 'requirements.in'


# emulate pip's option parsing with a stub command
class PipCommand(pip.basecommand.Command):
    name = 'PipCommand'


@click.command()
@click.option('-v', '--verbose', is_flag=True, help="Show more output")
@click.option('--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('-p', '--pre', is_flag=True, default=None, help="Allow resolving to prereleases (default is not)")
@click.option('-r', '--rebuild', is_flag=True, help="Clear any caches upfront, rebuild from scratch")
@click.option('-f', '--find-links', multiple=True, help="Look for archives in this directory or on this HTML page", envvar='PIP_FIND_LINKS')  # noqa
@click.option('-i', '--index-url', help="Change index URL (defaults to PyPI)", envvar='PIP_INDEX_URL')
@click.option('--extra-index-url', multiple=True, help="Add additional index URL to search", envvar='PIP_EXTRA_INDEX_URL')  # noqa
@click.option('--client-cert', help="Path to SSL client certificate, a single file containing the private key and the certificate in PEM format.")  # noqa
@click.option('--trusted-host', multiple=True, envvar='PIP_TRUSTED_HOST',
              help="Mark this host as trusted, even though it does not have "
                   "valid or any HTTPS.")
@click.option('--header/--no-header', is_flag=True, default=True, help="Add header to generated file")
@click.option('--annotate/--no-annotate', is_flag=True, default=True,
              help="Annotate results, indicating where dependencies come from")
@click.argument('src_file', required=False, type=click.Path(exists=True), default=DEFAULT_REQUIREMENTS_FILE)
def cli(verbose, dry_run, pre, rebuild, find_links, index_url, extra_index_url,
        client_cert, trusted_host, header, annotate, src_file):
    """Compiles requirements.txt from requirements.in specs."""
    log.verbose = verbose

    if not src_file:
        log.warning('No input files to process')
        sys.exit(2)

    ###
    # Setup
    ###

    # Use pip's parser for pip.conf management and defaults.
    # General options (find_links, index_url, extra_index_url, trusted_host,
    # and pre) are defered to pip.
    pip_options = PipCommand()
    index_opts = pip.cmdoptions.make_option_group(
        pip.cmdoptions.index_group,
        pip_options.parser,
    )
    pip_options.parser.insert_option_group(0, index_opts)
    pip_options.parser.add_option(optparse.Option('--pre', action='store_true', default=False))

    pip_args = []
    if find_links:
        pip_args.extend(['-f', find_links])
    if index_url:
        pip_args.extend(['-i', index_url])
    if extra_index_url:
        for extra in extra_index_url:
            pip_args.extend(['--extra-index-url', extra])
    if client_cert:
        pip_args.extend(['--client-cert', client_cert])
    if pre:
        pip_args.extend(['--pre'])
    if trusted_host:
        for host in trusted_host:
            pip_args.extend(['--trusted-host', host])

    pip_options, _ = pip_options.parse_args(pip_args)

    repository = PyPIRepository(pip_options)

    log.debug('Using indexes:')
    for index_url in repository.finder.index_urls:
        log.debug('  {}'.format(index_url))

    if repository.finder.find_links:
        log.debug('')
        log.debug('Configuration:')
        for find_link in repository.finder.find_links:
            log.debug('  -f {}'.format(find_link))

    ###
    # Parsing/collecting initial requirements
    ###
    constraints = []
    for line in parse_requirements(src_file, finder=repository.finder, session=repository.session, options=pip_options):
        constraints.append(line)

    try:
        resolver = Resolver(constraints, repository, prereleases=pre, clear_caches=rebuild)
        results = resolver.resolve()
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    log.debug('')

    ##
    # Output
    ##

    # Compute reverse dependency annotations statically, from the
    # dependency cache that the resolver has populated by now.
    #
    # TODO (1a): reverse deps for any editable package are lost
    #            what SHOULD happen is that they are cached in memory, just
    #            not persisted to disk!
    #
    # TODO (1b): perhaps it's easiest if the dependency cache has an API
    #            that could take InstallRequirements directly, like:
    #
    #                cache.set(ireq, ...)
    #
    #            then, when ireq is editable, it would store in
    #
    #              editables[egg_name][link_without_fragment] = deps
    #              editables['pip-tools']['git+...ols.git@future'] = {'click>=3.0', 'six'}
    #
    #            otherwise:
    #
    #              self[as_name_version_tuple(ireq)] = {'click>=3.0', 'six'}
    #
    reverse_dependencies = None
    if annotate:
        reverse_dependencies = resolver.reverse_dependencies(results)

    writer = OutputWriter(src_file, dry_run=dry_run, header=header,
                          annotate=annotate,
                          default_index_url=repository.DEFAULT_INDEX_URL,
                          index_urls=repository.finder.index_urls)
    writer.write(results=results,
                 reverse_dependencies=reverse_dependencies,
                 primary_packages={ireq.req.key for ireq in constraints})

    if dry_run:
        log.warning('Dry-run, so nothing updated.')
