#!/usr/bin/env python
from __future__ import absolute_import
import argparse
import logging
from pip_tools.review import get_latest_versions, get_installed_pkgs


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format='%(message)s')
    logging.getLogger('requests').setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser(
            description='Keeps your Python package dependencies pinned, but '
            'fresh.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    installed = list(get_installed_pkgs(editables=False))
    non_editables = [name for name, _, editable in installed if not editable]
    latest_versions = dict(get_latest_versions(non_editables))

    all_ok = True
    for pkg, installed_version, editable in installed:
        if editable:
            logging.debug('Skipping -e %s' % (pkg,))
            all_ok = False
            continue

        latest_version = latest_versions[pkg]
        if latest_version is None:
            logging.warning('No update information found for %s' % (pkg,))
            all_ok = False
        elif latest_version != installed_version:
            logging.info('%s==%s is available (you have %s)' % (pkg,
                latest_version, installed_version))
            all_ok = False
        else:
            logging.debug('%s==%s is up-to-date' % (pkg, installed_version))

    if all_ok:
        logging.info('Everything up-to-date')


if __name__ == '__main__':
    main()
