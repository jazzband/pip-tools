#!/usr/bin/env python
from __future__ import absolute_import

import argparse
import glob
import logging
from piptools.logging import logger

from piptools.datastructures import Spec, SpecSet
from piptools.package_manager import PackageManager
from piptools.resolver import Resolver


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


def parse_args():
    parser = argparse.ArgumentParser(
            description='Compiles requirements.txt from requirements.in specs.')
    parser.add_argument('--dry-run', action='store_true', default=False,
            help="Only show what would happen, don't change anything")
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    parser.add_argument('files', nargs='*')
    return parser.parse_args()


def walk_specfile(filename):
    """Walks over the given file, and returns (req, filename, lineno)
    tuples for each entry.
    """
    with open(filename, 'r') as f:
        reqs = f.read()

    for lineno, line in enumerate(reqs.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        spec = Spec.from_line(line, source='{0}:{1}'.format(filename, lineno))
        yield spec


def collect_source_specs(filenames):
    """This function collects all of the (primary) source specs into
    a flattened list of specs.
    """
    for filename in filenames:
        for spec in walk_specfile(filename):
            yield spec


def compile_specs(source_files, dry_run=False):
    logger.debug('===> Collecting source requirements')
    top_level_specs = list(collect_source_specs(source_files))

    spec_set = SpecSet()
    spec_set.add_specs(top_level_specs)
    logger.debug('%s' % (spec_set,))

    logger.debug('')
    logger.debug('===> Normalizing source requirements')
    spec_set = spec_set.normalize()
    logger.debug('%s' % (spec_set,))

    package_manager = PackageManager()

    #for spec in spec_set:
    #    logger.debug('')
    #    logger.debug('Finding package match for {0}'.format(spec))
    #    version = package_manager.find_best_match(spec)
    #    deps = package_manager.get_dependencies(spec.name, version)
    #    spec_set.add_specs(deps)
    #new_spec = spec_set.normalize()

    logger.debug('')
    logger.debug('===> Resolving full tree')

    resolver = Resolver(spec_set, package_manager=package_manager)
    pinned_spec_set = resolver.resolve()

    logger.debug('')
    logger.debug('===> Pinned spec set resolved')
    for spec in pinned_spec_set:
        logger.info('- %s' % (spec,))

    # TODO: new_spec has everything pinned but for all spec files. If there
    # is only one that's not an issue but for multiple specs we need to dump
    # the appropriate dependency tree in each compiled file.


def main():
    args = parse_args()
    setup_logging(args.verbose)

    src_files = args.files or glob.glob(GLOB_PATTERN)
    compile_specs(src_files, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("Dry-run, so nothing updated.")
    else:
        logger.info("Dependencies updated.")


if __name__ == '__main__':
    main()
