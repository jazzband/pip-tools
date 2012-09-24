#!/usr/bin/env python
from __future__ import absolute_import
import os.path
import argparse
import logging
from itertools import dropwhile, takewhile
from functools import partial
from subprocess import check_call as _check_call, check_output as _check_output

check_call = partial(_check_call, shell=True)
check_output = partial(_check_output, shell=True)

# Constants
PIP_IGNORE_FILE = '.pipignore'
SPLIT_PATTERN = '## The following requirements were added by pip --freeze:'


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format='%(message)s')
    logging.getLogger('requests').setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser(
            description='Rewrites requirements.txt to match your virtualenv.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
            help='Show more output')
    parser.add_argument('files', nargs='*')
    return parser.parse_args()


def dump_requirements(files):
    def pip_partition(lines):
        no_split_match = lambda line: line != SPLIT_PATTERN
        split_match = lambda line: line == SPLIT_PATTERN
        first = takewhile(no_split_match, lines)
        second = dropwhile(split_match, dropwhile(no_split_match, lines))
        return (list(first), list(second))

    def pip_info(filename):
        raw = check_output('pip freeze -r {}'.format(filename))
        lines = raw.split('\n')
        p = pip_partition(lines)
        return p

    def append_lines(lines, filename):
        with open(filename, 'a') as f:
            for line in lines:
                f.write('%s\n' % line)

    def rewrite(filename, lines):
        with open(filename, 'w') as f:
            for line in sorted(lines, key=str.lower):
                line = line.strip()
                if line:
                    f.write('%s\n' % line)

    TMP_FILE = '/tmp/.foo.txt'
    check_call('cat {} | sort -u > {}'.format(' '.join(files), TMP_FILE))
    _, new = pip_info(TMP_FILE)
    check_call('rm {}'.format(TMP_FILE))
    append_lines(new, files[0])

    for filename in files:
        if os.path.basename(filename) == PIP_IGNORE_FILE:  # never rewrite the pip ignore file
            continue
        pkgs, _ = pip_info(filename)
        rewrite(filename, pkgs)


def main():
    args = parse_args()
    setup_logging(args.verbose)

    if not args.files:
        args.files = ['requirements.txt', PIP_IGNORE_FILE]
    dump_requirements(args.files)


if __name__ == '__main__':
    main()
