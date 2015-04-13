import re
from itertools import chain


class ConflictError(Exception):
    pass


def first(iterable, default=None):
    for item in iterable:
        return item
    return default


def flatten(list_of_lists):
    """Flatten an iterable of iterables."""
    return chain.from_iterable(list_of_lists)


def _parse_vcs_url(line):
    """Parses a requirement line and if it is a VCS url, then
    returns a dict with following keys:

    * name - name of the package, either from url or from #egg part.
    * url - url without @branch-or-commit and #egg parts.
    * branch - branch name or commit id (optional).
    * editable - if the package should be installed as "editable" (optional).

    If given line is not VCS url, this function returns None.
    """

    regex_text = r"""
        ^
        ((?P<editable>-e)[ ]+)?        # checking if editable
        (?P<url>[a-z]+\+[a-z]+://.+?)  # extracting main URL
        (?:@(?P<branch>[^#]+))?        # extracting branch if any
        (?:\#egg=(?P<name>.+))?        # extracting egg name
        $
    """
    match = re.match(regex_text, line, re.X)
    if match is not None:
        result = {key: value for key, value in match.groupdict().items() if value}
        if 'name' not in result:
            name = result['url'].rsplit('/', 1)[1]
            name = name.rsplit('.', 1)[0]
            result['name'] = name
        if 'editable' in result:
            result['editable'] = True
        return result
