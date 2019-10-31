import locale

from .__version__ import __version__
from .click import secho

__all__ = ("__version__",)

# Needed for locale.getpreferredencoding(False) to work
# in pip._internal.utils.encoding.auto_decode
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error as e:  # pragma: no cover
    # setlocale can apparently crash if locale are uninitialized
    secho("Ignoring error when setting locale: {}".format(e), fg="red")
