#
# NOTE:
# The classes in this module are vendored from boltons:
#     http://pypi.python.org/pypi/boltons
#

import errno
import os
import stat

RW_PERMS = 438

_TEXT_OPENFLAGS = os.O_RDWR | os.O_CREAT | os.O_EXCL
if hasattr(os, 'O_NOINHERIT'):
    _TEXT_OPENFLAGS |= os.O_NOINHERIT
if hasattr(os, 'O_NOFOLLOW'):
    _TEXT_OPENFLAGS |= os.O_NOFOLLOW
_BIN_OPENFLAGS = _TEXT_OPENFLAGS
if hasattr(os, 'O_BINARY'):
    _BIN_OPENFLAGS |= os.O_BINARY


try:
    import fcntl as fcntl
except ImportError:
    def set_cloexec(fd):
        "Dummy set_cloexec for platforms without fcntl support"
        pass
else:
    def set_cloexec(fd):
        """Does a best-effort :func:`fcntl.fcntl` call to set a fd to be
        automatically closed by any future child processes.

        Implementation from the :mod:`tempfile` module.
        """
        try:
            flags = fcntl.fcntl(fd, fcntl.F_GETFD, 0)
        except IOError:
            pass
        else:
            # flags read successfully, modify
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(fd, fcntl.F_SETFD, flags)
        return


def _atomic_rename(path, new_path, overwrite=False):
    if overwrite:
        os.rename(path, new_path)
    else:
        os.link(path, new_path)
        os.unlink(path)


class AtomicSaver(object):
    """``AtomicSaver`` is a configurable `context manager`_ that provides
    a writable :class:`file` which will be moved into place as long as
    no exceptions are raised within the context manager's block. These
    "part files" are created in the same directory as the destination
    path to ensure atomic move operations (i.e., no cross-filesystem
    moves occur).

    Args:
        dest_path (str): The path where the completed file will be
            written.
        overwrite (bool): Whether to overwrite the destination file if
            it exists at completion time. Defaults to ``True``.
        file_perms (int): Integer representation of file permissions
            for the newly-created file. Defaults are, when the
            destination path already exists, to copy the permissions
            from the previous file, or if the file did not exist, to
            respect the user's configured `umask`_, usually resulting
            in octal 0644 or 0664.
        part_file (str): Name of the temporary *part_file*. Defaults
            to *dest_path* + ``.part``. Note that this argument is
            just the filename, and not the full path of the part
            file. To guarantee atomic saves, part files are always
            created in the same directory as the destination path.
        overwrite_part (bool): Whether to overwrite the *part_file*,
            should it exist at setup time. Defaults to ``False``,
            which results in an :exc:`OSError` being raised on
            pre-existing part files. Be careful of setting this to
            ``True`` in situations when multiple threads or processes
            could be writing to the same part file.
        rm_part_on_exc (bool): Remove *part_file* on exception cases.
            Defaults to ``True``, but ``False`` can be useful for
            recovery in some cases. Note that resumption is not
            automatic and by default an :exc:`OSError` is raised if
            the *part_file* exists.

    Practically, the AtomicSaver serves a few purposes:

      * Avoiding overwriting an existing, valid file with a partially
        written one.
      * Providing a reasonable guarantee that a part file only has one
        writer at a time.
      * Optional recovery of partial data in failure cases.

    .. _context manager: https://docs.python.org/2/reference/compound_stmts.html#with
    .. _umask: https://en.wikipedia.org/wiki/Umask

    """
    _default_file_perms = RW_PERMS

    # TODO: option to abort if target file modify date has changed since start?
    def __init__(self, dest_path, **kwargs):
        self.dest_path = dest_path
        self.overwrite = kwargs.pop('overwrite', True)
        self.file_perms = kwargs.pop('file_perms', None)
        self.overwrite_part = kwargs.pop('overwrite_part', False)
        self.part_filename = kwargs.pop('part_file', None)
        self.rm_part_on_exc = kwargs.pop('rm_part_on_exc', True)
        self.text_mode = kwargs.pop('text_mode', False)  # for windows
        self.buffering = kwargs.pop('buffering', -1)
        if kwargs:
            raise TypeError('unexpected kwargs: %r' % (kwargs.keys(),))

        self.dest_path = os.path.abspath(self.dest_path)
        self.dest_dir = os.path.dirname(self.dest_path)
        if not self.part_filename:
            self.part_path = dest_path + '.part'
        else:
            self.part_path = os.path.join(self.dest_dir, self.part_filename)
        self.mode = 'w+' if self.text_mode else 'w+b'
        self.open_flags = _TEXT_OPENFLAGS if self.text_mode else _BIN_OPENFLAGS

        self.part_file = None

    def _open_part_file(self):
        do_chmod = True
        file_perms = self.file_perms
        if file_perms is None:
            try:
                # try to copy from file being replaced
                stat_res = os.stat(self.dest_path)
                file_perms = stat.S_IMODE(stat_res.st_mode)
            except (OSError, IOError):
                # default if no destination file exists
                file_perms = self._default_file_perms
                do_chmod = False  # respect the umask

        fd = os.open(self.part_path, self.open_flags, file_perms)
        set_cloexec(fd)
        self.part_file = os.fdopen(fd, self.mode, self.buffering)

        # if default perms are overridden by the user or previous dest_path
        # chmod away the effects of the umask
        if do_chmod:
            try:
                os.chmod(self.part_path, file_perms)
            except (OSError, IOError):
                self.part_file.close()
                raise
        return

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
        if self.overwrite_part and os.path.lexists(self.part_path):
            os.unlink(self.part_path)
        self._open_part_file()
        return

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
            raise  # could not save destination file
        return
