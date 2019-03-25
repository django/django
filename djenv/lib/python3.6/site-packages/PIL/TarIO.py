#
# The Python Imaging Library.
# $Id$
#
# read files from within a tar file
#
# History:
# 95-06-18 fl   Created
# 96-05-28 fl   Open files in binary mode
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1995-96.
#
# See the README file for information on usage and redistribution.
#

import sys
from . import ContainerIO


##
# A file object that provides read access to a given member of a TAR
# file.

class TarIO(ContainerIO.ContainerIO):

    def __init__(self, tarfile, file):
        """
        Create file object.

        :param tarfile: Name of TAR file.
        :param file: Name of member file.
        """
        self.fh = open(tarfile, "rb")

        while True:

            s = self.fh.read(512)
            if len(s) != 512:
                raise IOError("unexpected end of tar file")

            name = s[:100].decode('utf-8')
            i = name.find('\0')
            if i == 0:
                raise IOError("cannot find subfile")
            if i > 0:
                name = name[:i]

            size = int(s[124:135], 8)

            if file == name:
                break

            self.fh.seek((size + 511) & (~511), 1)

        # Open region
        ContainerIO.ContainerIO.__init__(self, self.fh, self.fh.tell(), size)

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    if sys.version_info.major >= 3:
        def __del__(self):
            self.close()

    def close(self):
        self.fh.close()
