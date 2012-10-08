from __future__ import absolute_import
from logging import Logger


class IndentationContext(object):
    def __init__(self, logger):
        self._logger = logger

    def __enter__(self):
        self._logger.do_indent()

    def __exit__(self, type, value, traceback):
        self._logger.do_unindent()


class IndentingLogger(Logger):
    def __init__(self, *args, **kwargs):
        Logger.__init__(self, *args, **kwargs)
        self._indent_level = 0

    def _log(self, level, msg, *args, **kwargs):
        indentation = '    ' * self._indent_level
        msg = '%s%s' % (indentation, msg)
        Logger._log(self, level, msg, *args, **kwargs)

    def do_indent(self):
        self._indent_level += 1

    def do_unindent(self):
        self._indent_level -= 1

    def indent(self):
        return IndentationContext(self)


logger = IndentingLogger('piptools')
