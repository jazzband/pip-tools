#!/usr/bin/env python
from __future__ import absolute_import
import argparse
import logging
#from pip_refresh import check_for_updates
from pip_refresh import get_latest_versions, get_installed_pkgs


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format='%(message)s')


def parse_args():
    parser = argparse.ArgumentParser(
            description='Keeps your Python package dependencies pinned, but '
            'fresh.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    #parser.add_argument('--requirement', '-r', metavar='FILENAME',
    #        help='Specify requirements file to check.')
    #parser.add_argument('pkgname', nargs='*',
    #        help='Specify package names to update.')
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    installed_pkgs = get_installed_pkgs()
    logging.info('Installed packages:')
    for pkg, version in installed_pkgs:
        logging.info('- %s %s' % (pkg, version))

    pkgs = get_latest_versions(args.pkgname)
    for pkg, version in pkgs:
        if version is None:
            logging.warning('%s not found on PyPI' % (pkg,))
        else:
            logging.info('%s==%s is available' % (pkg, version,))


if __name__ == '__main__':
    main()
