# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from collections import deque


# Inspired by discussions on http://bugs.python.org/issue13585
class ExitStack(object):
    """Context manager for dynamic management of a stack of exit callbacks

    For example:

        with ExitStack() as stack:
            files = [stack.enter_context(open(fname)) for fname in filenames]
            # All opened files will automatically be closed at the end of
            # the with statement, even if attempts to open files later
            # in the list throw an exception

    """
    def __init__(self):
        self._exit_callbacks = deque()

    def pop_all(self):
        """Preserve the context stack by transferring it to a new instance"""
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = deque()
        return new_stack

    def _push_cm_exit(self, cm, cm_exit):
        """Helper to correctly register callbacks to __exit__ methods"""
        def _exit_wrapper(*exc_details):
            return cm_exit(cm, *exc_details)
        _exit_wrapper.__self__ = cm
        self.push(_exit_wrapper)

    def push(self, exit):
        """Registers a callback with the standard __exit__ method signature

        Can suppress exceptions the same way __exit__ methods can.

        Also accepts any object with an __exit__ method (registering the
        method instead of the object itself)
        """
        # We use an unbound method rather than a bound method to follow
        # the standard lookup behaviour for special methods
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__exit__
        except AttributeError:
            # Not a context manager, so assume its a callable
            self._exit_callbacks.append(exit)
        else:
            self._push_cm_exit(exit, exit_method)
        return exit  # Allow use as a decorator

    def callback(self, callback, *args, **kwds):
        """Registers an arbitrary callback and arguments.

        Cannot suppress exceptions.
        """
        def _exit_wrapper(exc_type, exc, tb):
            callback(*args, **kwds)
        # We changed the signature, so using @wraps is not appropriate, but
        # setting __wrapped__ may still help with introspection
        _exit_wrapper.__wrapped__ = callback
        self.push(_exit_wrapper)
        return callback  # Allow use as a decorator

    def enter_context(self, cm):
        """Enters the supplied context manager

        If successful, also pushes its __exit__ method as a callback and
        returns the result of the __enter__ method.
        """
        # We look up the special methods on the type to match the with
        # statement
        _cm_type = type(cm)
        _exit = _cm_type.__exit__
        result = _cm_type.__enter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    def close(self):
        """Immediately unwind the context stack"""
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        if not self._exit_callbacks:
            return

        # This looks complicated, but it is really just
        # setting up a chain of try-expect statements to ensure
        # that outer callbacks still get invoked even if an
        # inner one throws an exception
        def _invoke_next_callback(exc_details):
            # Callbacks are removed from the list in FIFO order
            # but the recursion means they're invoked in LIFO order
            cb = self._exit_callbacks.popleft()
            if not self._exit_callbacks:
                # Innermost callback is invoked directly
                return cb(*exc_details)
            # More callbacks left, so descend another level in the stack
            try:
                suppress_exc = _invoke_next_callback(exc_details)
            except:
                suppress_exc = cb(*sys.exc_info())
                # Check if this cb suppressed the inner exception
                if not suppress_exc:
                    raise
            else:
                # Check if inner cb suppressed the original exception
                if suppress_exc:
                    exc_details = (None, None, None)
                suppress_exc = cb(*exc_details) or suppress_exc
            return suppress_exc
        # Kick off the recursive chain
        return _invoke_next_callback(exc_details)
