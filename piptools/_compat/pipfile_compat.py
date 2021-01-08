import logging
import os
import sys
from optparse import Values
from urllib.parse import urlparse

from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._internal.req.req_file import (
    ParsedLine,
    build_parser,
    handle_line,
    handle_option_line,
)

# noinspection PyUnresolvedReferences,PyPep8Naming
from pipfile import __version__ as PIPFILE_VERSION  # noqa: F401
from pipfile.api import PipfileParser

from ..exceptions import IncompatibleRequirements

logger = logging.getLogger(__name__)


class ValuesFactory:
    """
    Builds a Values object by creating default values and updating from a dictionary
    """

    option_parser = build_parser()

    @classmethod
    def build_values(cls, values_dict, defaults=None):
        values = (
            cls.option_parser.get_default_values()
            if defaults is None
            else Values(defaults)
        )
        for attr, value in values_dict.items():
            setattr(values, attr, value)

        return values


def _handle_options(
    line, filename=None, lineno=None, finder=None, options=None, session=None
):
    key, value = line

    if key == "sources":
        if len(value) == 0:
            opts = dict(no_index=True)

        else:
            index_url = value[0]["url"]
            extra_urls = [source["url"] for source in value[1:]]
            trusted_hosts = [
                urlparse(source["url"]).netloc
                for source in value
                if not source.get("verify_ssl", True)
            ]
            opts = dict(
                index_url=index_url,
                extra_index_urls=extra_urls,
                trusted_hosts=trusted_hosts,
            )

        opts_values = ValuesFactory.build_values(opts)
        handle_option_line(opts_values, filename, lineno, finder, options, session)

    elif key == "requires":
        if "python_version" in value:
            requested_version = tuple(map(int, value["python_version"].split(".")))
            if requested_version != sys.version_info[: len(requested_version)]:
                raise IncompatibleRequirements(value, sys.version_info)

    else:
        logger.debug("Unused options: %r", line)


def _parse_requirement(line, filename=None, lineno=None):
    # A line is actually an item in a dictionary
    name, values = line

    # set args/opts for the ParsedLine constructor below
    args, opts = None, None
    if isinstance(values, str):
        args = name + values
    elif values.get("editable", False):
        opts = dict(editables=["file://{}".format(os.path.abspath(values["path"]))])

    return ParsedLine(filename, lineno, args, Values(opts), False)


def _parse_pipfile(
    filename, session, finder=None, options=None, constraint=False, pipfile_options=None
):
    """
    :type filename: String
    :type session: PipSession
    :type finder: Optional[PackageFinder]
    :type options: Optional[optparse.Values]
    :type constraint: bool
    """
    pipfile_dev = pipfile_options and pipfile_options.get("pipfile_dev", False)

    parser = PipfileParser(filename)
    pipfile_contents = parser.parse()

    for line in pipfile_contents["_meta"].items():
        _handle_options(line, filename, None, finder, options, session)

    groups = ("default", "develop") if pipfile_dev else ("default",)
    for group in groups:
        for line in pipfile_contents[group].items():
            parsed_line = _parse_requirement(line, filename=filename)
            yield handle_line(
                parsed_line, options=options, finder=finder, session=session
            )


def parse_pipfile(
    filename,
    session,
    finder=None,
    options=None,
    constraint=False,
    isolated=False,
    **pipfile_options,
):
    for parsed_req in _parse_pipfile(
        filename, session, finder, options, constraint, pipfile_options
    ):
        yield install_req_from_parsed_requirement(parsed_req, isolated=isolated)
