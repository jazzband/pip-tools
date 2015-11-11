# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from itertools import groupby, chain

from pip.download import is_vcs_url, _get_used_vcs_backend

from .click import style
from first import first


def comment(text):
    return style(text, fg='green')


def format_requirement(ireq):
    """
    Generic formatter for pretty printing InstallRequirements to the terminal
    in a less verbose way than using its `__str__` method.
    """
    if is_link_requirement(ireq):
        line = ''
        if ireq.editable:
            line = '-e '
        line += ireq.link.url
        if False and is_vcs_url(ireq.link):
            vcs_backend = _get_used_vcs_backend(ireq.link)
            rev = vcs_backend.get_revision(ireq.source_dir)
            line += '@{}'.format(rev)
    else:
        line = str(ireq.req)
    return line


def format_specifier(ireq):
    """
    Generic formatter for pretty printing the specifier part of
    InstallRequirements to the terminal.
    """
    # TODO: Ideally, this is carried over to the pip library itself
    specs = ireq.specifier._specs if ireq.req is not None else []
    specs = sorted(specs, key=lambda x: x._spec[1])
    return ','.join(str(s) for s in specs) or '<any>'


def is_link_requirement(ireq):
    return ireq.link and ireq.link.comes_from is None


def is_pinned_requirement(ireq):
    """
    Returns whether an InstallRequirement is a "pinned" requirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "=="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned
    """
    if is_link_requirement(ireq):
        return False

    if len(ireq.specifier._specs) != 1:
        return False

    op, version = first(ireq.specifier._specs)._spec
    return (op == '==' or op == '===') and not version.endswith('.*')


def as_name_version_tuple(ireq):
    """
    Pulls out the (name: str, version:str) tuple from the pinned
    InstallRequirement.
    """
    if not is_pinned_requirement(ireq):
        raise TypeError('Expected a pinned InstallRequirement, got {}'.format(ireq))

    name = ireq.req.key
    version = first(ireq.specifier._specs)._spec[1]
    return name, version


def full_groupby(iterable, key=None):
    """Like groupby(), but sorts the input on the group key first."""
    return groupby(sorted(iterable, key=key), key=key)


def flat_map(fn, collection):
    """Map a function over a collection and flatten the result by one-level"""
    return chain.from_iterable(map(fn, collection))


def lookup_table(values, key=None, keyval=None, unique=False, use_lists=False):
    """
    Builds a dict-based lookup table (index) elegantly.

    Supports building normal and unique lookup tables.  For example:

    >>> lookup_table(['foo', 'bar', 'baz', 'qux', 'quux'],
    ...              lambda s: s[0])
    {
        'b': {'bar', 'baz'},
        'f': {'foo'},
        'q': {'quux', 'qux'}
    }

    For key functions that uniquely identify values, set unique=True:

    >>> lookup_table(['foo', 'bar', 'baz', 'qux', 'quux'],
    ...              lambda s: s[0],
    ...              unique=True)
    {
        'b': 'baz',
        'f': 'foo',
        'q': 'quux'
    }

    The values of the resulting lookup table will be values, not sets.

    For extra power, you can even change the values while building up the LUT.
    To do so, use the `keyval` function instead of the `key` arg:

    >>> lookup_table(['foo', 'bar', 'baz', 'qux', 'quux'],
    ...              keyval=lambda s: (s[0], s[1:]))
    {
        'b': {'ar', 'az'},
        'f': {'oo'},
        'q': {'uux', 'ux'}
    }

    """
    if keyval is None:
        if key is None:
            keyval = (lambda v: v)
        else:
            keyval = (lambda v: (key(v), v))

    if unique:
        return dict(keyval(v) for v in values)

    lut = {}
    for value in values:
        k, v = keyval(value)
        try:
            s = lut[k]
        except KeyError:
            if use_lists:
                s = lut[k] = list()
            else:
                s = lut[k] = set()
        if use_lists:
            s.append(v)
        else:
            s.add(v)
    return dict(lut)
