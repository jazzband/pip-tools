#!/usr/bin/env python
from __future__ import absolute_import
import os
import argparse
from functools import partial
import logging
import urllib2
import json
from urllib2 import HTTPError
try:
    from subprocess import check_ouput as _check_ouput
except ImportError:
    import subprocess

    def _check_output(*args, **kwargs):
        process = subprocess.Popen(stdout=subprocess.PIPE, *args, **kwargs)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            error = subprocess.CalledProcessError(retcode, args[0])
            error.output = output
            raise error
        return output

check_output = partial(_check_output, shell=True)


def parse_args():
    parser = argparse.ArgumentParser(
            description='Keeps your Python package dependencies pinned, but '
            'fresh.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    parser.add_argument('--raw', '-r', action='store_true', default=False,
            help='Print raw lines (suitable for passing to pip install)')
    parser.add_argument('--interactive', '-i', action='store_true', default=False,
            help='Ask interactively to install updates')
    parser.add_argument('--auto', '-a', action='store_true', default=False,
            help='Automatically install every update found')
    parser.add_argument('--editables', '-e', action='store_true', default=False,
            help='Also include editable packages in PyPI lookup')
    return parser.parse_args()


def get_pkg_info(pkg_name):
    logging.debug('Checking for updates of %r' % (pkg_name,))
    req = urllib2.Request('http://pypi.python.org/pypi/%s/json' % (pkg_name,))
    handler = urllib2.urlopen(req)
    status = handler.getcode()
    if status == 200:
        content = handler.read()
        return json.loads(content)
    else:
        raise ValueError('Package %r not found on PyPI.' % (pkg_name,))


def latest_version(pkg_name, silent=False):
    try:
        info = get_pkg_info(pkg_name)
    except (ValueError, HTTPError):
        if silent:
            return None
        else:
            raise
    return info['info']['version']


def get_latest_versions(pkg_names):
    get_latest = partial(latest_version, silent=True)
    versions = map(get_latest, pkg_names)
    return zip(pkg_names, versions)


def get_installed_pkgs():
    output = check_output('pip freeze')

    for line in output.split('\n'):
        if not line or line.startswith('##'):
            continue

        if line.startswith('-e'):
            name = line.split('#egg=', 1)[1]
            if name.endswith('-dev'):
                name = name[:-4]
            yield name, 'dev', True
        else:
            name, version = line.split('==')
            yield name, version, False


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format='%(message)s')



class InteractiveAsker(object):
    def __init__(self):
        self.cached_answer = None

    def ask(self, prompt):
        if self.cached_answer is not None:
            return self.cached_answer

        answer = ''
        while answer not in ['y', 'n', 'a', 'q']:
            answer = raw_input('%s [Y]es, [N]o, [A]ll, [Q]uit ' % prompt)
            answer = answer.strip().lower()

        if answer in ['q', 'a']:
            self.cached_answer = answer

        return answer

ask_to_install = partial(InteractiveAsker().ask, prompt='Upgrade now?')


def update_pkg(pkg, version):
    os.system('pip install %s==%s' % (pkg, version))


def confirm(question):
    answer = ''
    while not answer in ['y', 'n']:
        answer = raw_input(question)
        answer = answer.strip().lower()
    return answer == 'y'


def main():
    args = parse_args()
    setup_logging(args.verbose)

    if args.raw and args.interactive:
        raise SystemExit('--raw and --interactive cannot be used together')

    if args.auto and args.editables:
        if not confirm('WARNING: Using --auto and --editables at the same time might lead to unintended upgrades.\n'
                'Are you sure? [yn] '):
            raise SystemExit('Quitting')

    installed = list(get_installed_pkgs())
    lookup_on_pypi = [name for name, _, editable in installed
            if not editable or args.editables]
    latest_versions = dict(get_latest_versions(lookup_on_pypi))

    all_ok = True
    for pkg, installed_version, editable in installed:
        if editable and not args.editables:
            logging.debug('Skipping -e %s==%s' % (pkg, installed_version))
            all_ok = False
            continue

        latest_version = latest_versions[pkg]
        if latest_version is None:
            logging.warning('No update information found for %s' % (pkg,))
            all_ok = False
        elif latest_version != installed_version:
            if args.raw:
                logging.info('%s==%s' % (pkg, latest_version))
            else:
                if args.auto:
                    update_pkg(pkg, latest_version)
                else:
                    logging.info('%s==%s is available (you have %s)' % (pkg,
                        latest_version, installed_version))
                    if args.interactive:
                        answer = ask_to_install()
                        if answer in ['y', 'a']:
                            update_pkg(pkg, latest_version)
            all_ok = False
        elif not args.raw:
            logging.debug('%s==%s is up-to-date' % (pkg, installed_version))

    if all_ok and not args.raw:
        logging.info('Everything up-to-date')


if __name__ == '__main__':
    main()
