#!/usr/bin/env python
from __future__ import absolute_import
import os
import re
import argparse
from functools import partial
import logging
import sys
import json
try:
    import urllib2 as urllib_request  # Python2
except ImportError:
    import urllib.request as urllib_request
from pkg_resources import parse_version

try:
    from subprocess import check_output as _check_output
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

try:
    import __builtin__
    input = getattr(__builtin__, 'raw_input')  # Python2
except (ImportError, AttributeError):
    pass

from packaging import version as packaging_version


def parse_args():
    parser = argparse.ArgumentParser(
        description='Keeps your Python package dependencies pinned, '
                    'but fresh.')
    parser.add_argument(
        '--verbose', '-v', action='store_true', default=False,
        help='Show more output')
    parser.add_argument(
        '--raw', '-r', action='store_true', default=False,
        help='Print raw lines (suitable for passing to pip install)')
    parser.add_argument(
        '--interactive', '-i', action='store_true', default=False,
        help='Ask interactively to install updates')
    parser.add_argument(
        '--auto', '-a', action='store_true', default=False,
        help='Automatically install every update found')
    parser.add_argument(
        '--editables', '-e', action='store_true', default=False,
        help='Also include editable packages in PyPI lookup')
    parser.add_argument(
        '--local', '-l', action='store_true', default=False,
        help='If in a virtualenv that has global access, do not output '
             'globally-installed packages')
    parser.add_argument(
        '--pre', '-p', action='store_true', default=False,
        help='Include pre-release and development versions')
    return parser.parse_args()


def load_pkg_info(pkg_name):
    if pkg_name is None:
        return

    logger = logging.getLogger(u'pip-review')
    logger.debug('Checking for updates of {0}'.format(pkg_name))

    req = urllib_request.Request(
        'https://pypi.python.org/pypi/{0}/json'.format(pkg_name))
    try:
        handler = urllib_request.urlopen(req)
    except urllib_request.HTTPError:
        return

    if handler.getcode() == 200:
        content = handler.read()
        return json.loads(content.decode('utf-8'))


def guess_pkg_name(pkg_name):
    logger = logging.getLogger(u'pip-review')
    logger.debug('Try to guess package {0} name on PyPI.'.format(pkg_name))
    req = urllib_request.Request(
        'https://pypi.python.org/simple/{0}/'.format(pkg_name))
    try:
        handler = urllib_request.urlopen(req)
    except urllib_request.HTTPError:
        return None

    if handler.getcode() == 200:
        url_match = re.search(r'/pypi\.python\.org/simple/([^/]+)/',
                              handler.geturl())
        if url_match:
            return url_match.group(1)
    return None


def get_pkg_info(pkg_name, silent=False):
    info = load_pkg_info(pkg_name)
    if info is None:
        guessed_name = guess_pkg_name(pkg_name)
        if guessed_name is not None:
            info = load_pkg_info(guessed_name)
    if info is None and not silent:
        raise ValueError('Package {0} not found on PyPI.'.format(pkg_name))
    return info


def latest_version(pkg_name, prerelease=False, silent=False):
    try:
        info = get_pkg_info(pkg_name, silent=silent)
    except ValueError:
        if silent:
            return None, None
        else:
            raise
    if not info:
        return None, None

    try:
        versions = [
            v for v in sorted(
                list(info['releases']),
                key=packaging_version.parse
            )
        ]
        if not prerelease:
            versions = [v for v in versions
                        if not packaging_version.parse(v).is_prerelease]
        version = versions[-1]
    except IndexError:
        return None, None

    return parse_version(version), version


def get_latest_versions(pkg_names, prerelease=False):
    get_latest = partial(latest_version, prerelease=prerelease, silent=True)
    versions = map(get_latest, pkg_names)
    return zip(pkg_names, versions)


def get_installed_pkgs(local=False):
    logger = logging.getLogger(u'pip-review')
    command = 'pip freeze'
    if local:
        command += ' --local'

    output = check_output(command).decode('utf-8')

    for line in output.split('\n'):
        if not line or line.startswith('##'):
            continue

        if line.startswith('-e'):
            name = line.split('#egg=', 1)[1]
            if name.endswith('-dev'):
                name = name[:-4]
            yield name, 'dev', 'dev', True
        else:
            name, version = line.split('==')
            yield name, parse_version(version), version, False


class StdOutFilter(logging.Filter):
    def filter(self, record):
        return record.levelno in [logging.DEBUG, logging.INFO]


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    format = u'%(message)s'

    logger = logging.getLogger(u'pip-review')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.addFilter(StdOutFilter())
    stdout_handler.setFormatter(logging.Formatter(format))
    stdout_handler.setLevel(logging.DEBUG)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(format))
    stderr_handler.setLevel(logging.WARNING)

    logger.setLevel(level)
    logger.addHandler(stderr_handler)
    logger.addHandler(stdout_handler)
    return logger


class InteractiveAsker(object):
    def __init__(self):
        self.cached_answer = None

    def ask(self, prompt):
        if self.cached_answer is not None:
            return self.cached_answer

        answer = ''
        while answer not in ['y', 'n', 'a', 'q']:
            answer = input(
                '{0} [Y]es, [N]o, [A]ll, [Q]uit '.format(prompt))
            answer = answer.strip().lower()

        if answer in ['q', 'a']:
            self.cached_answer = answer

        return answer


ask_to_install = partial(InteractiveAsker().ask, prompt='Upgrade now?')


def update_pkg(pkg, version):
    os.system('pip install {0}=={1}'.format(pkg, version))


def confirm(question):
    answer = ''
    while not answer in ['y', 'n']:
        answer = input(question)
        answer = answer.strip().lower()
    return answer == 'y'


def main():
    args = parse_args()
    logger = setup_logging(args.verbose)

    if args.raw and args.interactive:
        raise SystemExit('--raw and --interactive cannot be used together')

    if args.auto and args.editables:
        if not confirm('WARNING: Using --auto and --editables at the same '
                       'time might lead to unintended upgrades.\n'
                       'Are you sure? [y/n] '):
            raise SystemExit('Quitting')

    installed = list(get_installed_pkgs(local=args.local))
    lookup_on_pypi = [name for name, _, _, editable in installed
                      if not editable or args.editables]
    latest_versions = dict(get_latest_versions(lookup_on_pypi, args.pre))

    all_ok = True
    for pkg, installed_raw_version, installed_version, editable in installed:
        if editable and not args.editables:
            logger.debug('Skipping -e {0}=={1}'.format(pkg, installed_version))
            all_ok = False
            continue

        raw_version, latest_version = latest_versions[pkg]
        if raw_version is None:
            logger.warning('No update information found for {0}'.format(pkg))
            all_ok = False
        elif raw_version != installed_raw_version:
            if args.raw:
                logger.info('{0}=={1}'.format(pkg, latest_version))
            else:
                if args.auto:
                    update_pkg(pkg, latest_version)
                else:
                    logger.info('{0}=={1} is available (you have {2})'.format(
                        pkg, latest_version, installed_version
                    ))
                    if args.interactive:
                        answer = ask_to_install()
                        if answer in ['y', 'a']:
                            update_pkg(pkg, latest_version)
            all_ok = False
        elif not args.raw:
            logger.debug(
                '{0}=={1} is up-to-date'.format(pkg, installed_version))

    if all_ok and not args.raw:
        logger.info('Everything up-to-date')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write('\nAborted\n')
        sys.exit(0)
