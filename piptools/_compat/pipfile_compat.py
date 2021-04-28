import logging
import os
import re
import sys
from collections import defaultdict
from optparse import Values
from urllib.parse import urlparse

import jsonschema as jsonschema
import numpy as np
import pipfile
import toml
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._internal.req.req_file import (
    ParsedLine,
    build_parser,
    handle_option_line,
    handle_requirement_line,
)
from pip._vendor.packaging.version import parse as parse_version
from pipfile.api import PipfileParser

from ..exceptions import IncompatibleRequirements
from . import PIP_VERSION

PIPFILE_VERSION = tuple(
    map(int, parse_version(pipfile.__version__).base_version.split("."))
)

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
    line, filename=None, lineinfo=None, finder=None, options=None, session=None
):
    key, value = line

    if key == "sources":
        if len(value) == 0:
            opts = dict(no_index=True)
            opts_values = ValuesFactory.build_values(opts)
            handle_option_line(opts_values, filename, None, finder, options, session)

        else:
            # Handle trusted hosts first
            _handle_trusted_hosts(value, filename, lineinfo, finder, options, session)
            # Do index URLs second because they overwrite with default values otherwise
            _handle_sources(value, filename, lineinfo, finder, options, session)

    elif key == "requires":
        if "python_version" in value:
            requested_version = tuple(map(int, value["python_version"].split(".")))
            if requested_version != sys.version_info[: len(requested_version)]:
                raise IncompatibleRequirements(value, sys.version_info)

    else:
        logger.debug("Unused options: %r", line)


def _handle_sources(sources, filename, lineinfo, finder, options, session):
    opts = dict(
        index_url=sources[0]["url"], extra_index_urls=[s["url"] for s in sources[1:]]
    )
    opts_values = ValuesFactory.build_values(opts)
    handle_option_line(opts_values, filename, None, finder, options, session)


def _handle_trusted_hosts(sources, filename, lineinfo, finder, options, session):
    """
    Handles each trusted host individually as if it were one line (mostly for better user feedback)
    """
    for source in sources:
        if not source.get("verify_ssl", True):
            lineno = lineinfo["sources"].get(source["name"]) if lineinfo else None
            opts = dict(trusted_hosts=[urlparse(source["url"]).netloc])
            opts_values = ValuesFactory.build_values(opts)
            handle_option_line(opts_values, filename, lineno, finder, options, session)


def _handle_requirement(line, options=None, filename=None, lineno=None):
    # A line is actually an item in a dictionary
    name, values = line

    def _extract_from_values(values):
        extras = values.get("extras")
        extras_str = "[{}]".format(",".join(extras)) if extras else ""

        version = values.get("version", "*")
        version_str = version if version != "*" else ""

        markers = values.get("markers")
        env_markers = ";{}".format(",".join(markers)) if markers else ""

        return extras_str, version_str, env_markers

    # set args/opts for the ParsedLine constructor below
    args, opts = None, None

    if isinstance(values, str):
        args = name if values.strip() == "*" else name + values

    elif values.get("editable", False):
        path = os.path.abspath(values["path"])
        extras, _, env_markers = _extract_from_values(values)
        editable_path = "{path}{extras}{env}".format(
            path=path, extras=extras, env=env_markers
        )
        opts = dict(editables=[editable_path])

    elif "version" in values:
        extras, version, env_markers = _extract_from_values(values)
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


class PipfileParserExt:
    def __init__(self, pipfile_parser):
        self.parser = pipfile_parser

    def build_lineinfo(self, parsed_data=None):
        if parsed_data is None:
            parsed_data = self.parser.parse()

        try:
            return self._build_lineinfo(parsed_data)
        except jsonschema.exceptions.ValidationError:
            logger.warning(
                "Failed to build line info from Pipfile. This is probably a developer bug.",
                exc_info=True,
            )
            return dict(
                sources=defaultdict(list),
                default=defaultdict(list),
                develop=defaultdict(list),
            )

    def _build_lineinfo(self, data):
        self._validate_schema(data)

        with open(self.parser.filename, encoding="utf-8") as fh:
            pipfile_contents = list(map(str.strip, fh.readlines()))

        lineinfo = dict(requires={}, sources={}, default={}, develop={})

        for index, s in enumerate(data["_meta"]["sources"]):
            source_line = self.find_source(pipfile_contents, s)
            if source_line:  # Sources may come from pip defaults
                lineinfo["sources"][s["name"]] = source_line

        for index, r in enumerate(data["_meta"]["requires"].items()):
            source_line = self.find_requires(pipfile_contents, r)
            lineinfo["requires"][r] = source_line

        # For packages, we do a regex split on each line. Preprocess that as a slight optimization
        split_lines = [re.split(r"\s*=\s*", line) for line in pipfile_contents]

        for index, r in enumerate(data["default"].items()):
            name, source_line = self.find_package(split_lines, r)
            lineinfo["default"][name] = source_line

        for index, r in enumerate(data["develop"].items()):
            name, source_line = self.find_package(split_lines, r)
            lineinfo["develop"][name] = source_line

        return lineinfo

    @classmethod
    def find_source(cls, pipfile_contents, source):
        source_candidates = (
            cls._find_key_value(pipfile_contents, k, v) for k, v in source.items()
        )
        source_candidates = list(filter(None, source_candidates))
        return min(source_candidates) if source_candidates else None

    @classmethod
    def find_requires(cls, pipfile_contents, requires):
        return cls._find_key_value(pipfile_contents, *requires)

    @classmethod
    def _find_key_value(cls, pipfile_contents, key, value):
        encoder = toml.TomlEncoder()
        found = [
            (key in line and encoder.dump_value(value) in line)
            for line in pipfile_contents
        ]
        source_line = np.nonzero(found)[0]
        return source_line[0] if source_line.size == 1 else None

    @staticmethod
    def find_package(pipfile_contents, requirement):
        name, constraints = requirement
        source_line = np.nonzero([name == line[0] for line in pipfile_contents])[0]
        return name, source_line[0] if source_line.size == 1 else None

    @staticmethod
    def _validate_schema(data):
        """
        The PipfileParser class returns a data structure that this class consumes.
        Make sure I still understand the right type of data before consuming it
        """

        schema = {
            "type": "object",
            "properties": {
                "_meta": {
                    "type": "object",
                    "properties": {
                        "requires": dict(type="object"),
                        "sources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": dict(type="string"),
                                    "url": dict(type="string"),
                                    "verify_ssl": dict(type="boolean"),
                                },
                                "required": ["url"],
                            },
                        },
                    },
                    "required": ["sources", "requires"],
                },
                # In this implementation, I only read object keys, so I don't care about properties
                "default": dict(type="object"),
                "develop": dict(type="object"),
            },
            "required": ["_meta", "default", "develop"],
        }
        jsonschema.validate(data, schema)


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
    lineinfo_parser = PipfileParserExt(parser)
    pipfile_contents = parser.parse()
    pipfile_lineinfo = lineinfo_parser.build_lineinfo(pipfile_contents)

    for line in pipfile_contents["_meta"].items():
        _handle_options(line, filename, pipfile_lineinfo, finder, options, session)

    groups = ("default", "develop") if pipfile_dev else ("default",)
    for group in groups:
        for line in pipfile_contents[group].items():
            lineno = pipfile_lineinfo[group].get(line[0])
            yield _handle_requirement(line, filename=filename, lineno=lineno)


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
