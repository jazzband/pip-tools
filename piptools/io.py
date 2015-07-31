#
# NOTE:
# The classes in this module are vendored from boltons:
#     http://pypi.python.org/pypi/boltons
#

import errno
import os
import tempfile


def _atomic_rename(path, new_path, overwrite=False):
    if overwrite:
        os.rename(path, new_path)
    else:
        os.link(path, new_path)
        os.unlink(path)


class AtomicSaver(object):
    """``AtomicSaver`` is a configurable context manager that provides a
    writable file which will be moved into place as long as no
    exceptions are raised before it is closed. It returns a standard
    Python :class:`file` object which can be closed explicitly or used
    as a context manager (i.e., via the :keyword:`with` statement).
    Args:
        dest_path (str): The path where the completed file will be
            written.
        overwrite (bool): Whether to overwrite the destination file if
            it exists at completion time. Defaults to ``True``.
        part_file (str): Name of the temporary *part_file*. Defaults
            to *dest_path* + ``.part``
        rm_part_on_exc (bool): Remove *part_file* on exception.
            Defaults to ``True``.
        overwrite_partfile (bool): Whether to overwrite the *part_file*,
            should it exist at setup time. Defaults to ``True``.
        open_func (callable): Function used to open the file. Override
            this if you want to use :func:`codecs.open` or some other
            alternative. Defaults to :func:`open()`.
        open_kwargs (dict): Additional keyword arguments to pass to
            *open_func*. Defaults to ``{}``.
    """
    # TODO: option to abort if target file modify date has changed
    # since start?
    def __init__(self, dest_path, **kwargs):
        self.dest_path = dest_path
        self.overwrite = kwargs.pop('overwrite', True)
        self.overwrite_part = kwargs.pop('overwrite_partfile', True)
        self.part_filename = kwargs.pop('part_file', None)
        self.text_mode = kwargs.pop('text_mode', False)  # for windows
        self.rm_part_on_exc = kwargs.pop('rm_part_on_exc', True)
        self._open = kwargs.pop('open_func', open)
        self._open_kwargs = kwargs.pop('open_kwargs', {})
        if kwargs:
            raise TypeError('unexpected kwargs: %r' % kwargs.keys)

        self.dest_path = os.path.abspath(self.dest_path)
        self.dest_dir = os.path.dirname(self.dest_path)
        if not self.part_filename:
            self.part_path = dest_path + '.part'
        else:
            self.part_path = os.path.join(self.dest_dir, self.part_filename)
        self.mode = 'w+' if self.text_mode else 'w+b'

        self.part_file = None

    def setup(self):
        """Called on context manager entry (the :keyword:`with` statement),
        the ``setup()`` method creates the temporary file in the same
        directory as the destination file.
        ``setup()`` tests for a writable directory with rename permissions
        early, as the part file may not be written to immediately (not
        using :func:`os.access` because of the potential issues of
        effective vs. real privileges).
        If the caller is not using the :class:`AtomicSaver` as a
        context manager, this method should be called explicitly
        before writing.
        """
        if os.path.lexists(self.dest_path):
            if not self.overwrite:
                raise OSError(errno.EEXIST,
                              'Overwrite disabled and file already exists',
                              self.dest_path)
        tmp_fd, tmp_part_path = tempfile.mkstemp(dir=self.dest_dir,
                                                 text=self.text_mode)
        os.close(tmp_fd)
        try:
            _atomic_rename(tmp_part_path, self.part_path,
                           overwrite=self.overwrite_part)
        except OSError:
            os.unlink(tmp_part_path)
            raise

        self.part_file = self._open(self.part_path, self.mode,
                                    **self._open_kwargs)

    def __enter__(self):
        self.setup()
        return self.part_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.part_file.close()
        if exc_type:
            if self.rm_part_on_exc:
                try:
                    os.unlink(self.part_path)
                except:
                    pass
            return
        try:
            _atomic_rename(self.part_path, self.dest_path,
                           overwrite=self.overwrite)
        except OSError:
            if self.rm_part_on_exc:
                os.unlink(self.part_path)
        return
