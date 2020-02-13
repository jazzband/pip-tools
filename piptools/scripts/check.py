# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
import tempfile

from .. import click
from ..lock import check, read_locks
from ..logging import log

DEFAULT_REQUIREMENTS_FILE = "requirements.txt"


@click.command()
@click.version_option()
@click.pass_context
@click.option("-v", "--verbose", count=True, help="Show more output")
@click.option("-q", "--quiet", count=True, help="Give less output")
@click.argument("req_files", nargs=-1, type=click.Path(exists=True, allow_dash=True))
def cli(ctx, verbose, quiet, req_files):
    """Checks whether requirements.txt aligns with requirements.in."""
    log.verbosity = verbose - quiet

    for req_file in req_files:
        if req_file.endswith(".in"):
            raise click.BadParameter(
                "req_file has the .in extensions, which is most likely an error "
                "and will most likely fail the checks. You probably meant to use "
                "the corresponding *.txt file?"
            )

    if len(req_files) == 0:
        if os.path.exists(DEFAULT_REQUIREMENTS_FILE):
            req_files = (DEFAULT_REQUIREMENTS_FILE,)
        else:
            raise click.BadParameter(
                ("If you do not specify an input file, " "the default is {}").format(
                    DEFAULT_REQUIREMENTS_FILE
                )
            )

    if req_files == ("-",):
        # pip requires filenames and not files. Since we want to support
        # piping from stdin, we need to briefly save the input from stdin
        # to a temporary file and have pip read that.
        tmpfile = tempfile.NamedTemporaryFile(mode="wt", delete=False)
        tmpfile.write(sys.stdin.read())
        tmpfile.flush()

        req_files = (tmpfile.name,)

    errors = 0

    for req_file in req_files:
        locks = read_locks(req_file)
        if not locks:
            log.info("{}: no locks found".format(req_file))
            errors += 1
        is_okay = check(locks)
        if not is_okay:
            log.info("{}: lock(s) are out-of-date".format(req_file))
            errors += 1

    if errors:
        log.info("{} errors found. Run pip-compile to fix".format(errors))
        sys.exit(1)
    else:
        log.debug("locks are up-to-date")
