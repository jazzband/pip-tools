import logging
import os
import sys
from optparse import Values
from urllib.parse import urlparse

from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._internal.req.req_file import (
    ParsedLine,
    build_parser,
    handle_option_line,
    handle_requirement_line,
)
from pipfile import __version__ as PIPFILE_VERSION  # noqa: F401
from pipfile.api import PipfileParser

from ..exceptions import IncompatibleRequirements
from . import PIP_VERSION

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


def _handle_requirement(line, options=None, filename=None, lineno=None):
    # A line is actually an item in a dictionary
    name, values = line

    # set args/opts for the ParsedLine constructor below
    args, opts = None, None

    if isinstance(values, str):
        args = name if values.strip() == "*" else name + values

    elif values.get("editable", False):
        opts = dict(editables=["{}".format(os.path.abspath(values["path"]))])

    elif "version" in values:
        extras = (
            "[{}]".format(",".join(values["extras"])) if values.get("extras") else ""
        )
        version = values["version"] if values.get("version", "*") != "*" else ""
        env_markers = (
            ";{}".format(",".join(values["markers"])) if values.get("markers") else ""
        )
        args = "{name}{extras}{version}{environment}".format(
            name=name,
            extras=extras,
            version=version,
            environment=env_markers,
        )

    elif "file" in values:
        args = values["file"]

    elif "git" in values:
        url = values["git"]
        ref = "@{}".format(values["ref"]) if values.get("ref") else ""
        args = f"git+{url}{ref}#egg={name}"

    parsed_line = _build_parsed_line(filename, lineno, args, opts)
    return handle_requirement_line(parsed_line, options)


def _build_parsed_line(filename, lineno, args, opts):
    if PIP_VERSION < (20, 3):
        parsed_line = ParsedLine(
            filename=filename,
            lineno=lineno,
            comes_from=None,
            args=args,
            opts=Values(opts),
            constraint=False,
        )
    else:
        parsed_line = ParsedLine(
            filename=filename,
            lineno=lineno,
            args=args,
            opts=Values(opts),
            constraint=False,
        )

    return parsed_line


def _parse_pipfile(filename, session, finder=None, options=None, pipfile_options=None):
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
            yield _handle_requirement(line, filename=filename)


def parse_pipfile(
    filename,
    session,
    finder=None,
    options=None,
    isolated=False,
    **pipfile_options,
):
    for parsed_req in _parse_pipfile(
        filename, session, finder, options, pipfile_options
    ):
        yield install_req_from_parsed_requirement(parsed_req, isolated=isolated)
