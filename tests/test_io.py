import os
import tempfile

from piptools import io as ppt_io


def test__atomic_rename_can_overwrite():
    try:
        fd, path = tempfile.mkstemp()
        new_fd, new_path = tempfile.mkstemp()

        # close for to remove tmp files
        for _fd in [fd, new_fd]:
            os.fdopen(_fd).close()

        ppt_io._atomic_rename(path, new_path, overwrite=True)
    finally:
        try:
            os.remove(path)
        except:
            # If move file0 to file1,
            # there is no file on file0's path.
            pass
        os.remove(new_path)
