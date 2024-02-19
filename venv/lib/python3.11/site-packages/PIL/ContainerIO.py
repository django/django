#
# The Python Imaging Library.
# $Id$
#
# a class to read from a container file
#
# History:
# 1995-06-18 fl     Created
# 1995-09-07 fl     Added readline(), readlines()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1995 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
from typing import IO, AnyStr, Generic, Literal


class ContainerIO(Generic[AnyStr]):
    """
    A file object that provides read access to a part of an existing
    file (for example a TAR file).
    """

    def __init__(self, file: IO[AnyStr], offset: int, length: int) -> None:
        """
        Create file object.

        :param file: Existing file.
        :param offset: Start of region, in bytes.
        :param length: Size of region, in bytes.
        """
        self.fh: IO[AnyStr] = file
        self.pos = 0
        self.offset = offset
        self.length = length
        self.fh.seek(offset)

    ##
    # Always false.

    def isatty(self) -> bool:
        return False

    def seek(self, offset: int, mode: Literal[0, 1, 2] = io.SEEK_SET) -> None:
        """
        Move file pointer.

        :param offset: Offset in bytes.
        :param mode: Starting position. Use 0 for beginning of region, 1
           for current offset, and 2 for end of region.  You cannot move
           the pointer outside the defined region.
        """
        if mode == 1:
            self.pos = self.pos + offset
        elif mode == 2:
            self.pos = self.length + offset
        else:
            self.pos = offset
        # clamp
        self.pos = max(0, min(self.pos, self.length))
        self.fh.seek(self.offset + self.pos)

    def tell(self) -> int:
        """
        Get current file pointer.

        :returns: Offset from start of region, in bytes.
        """
        return self.pos

    def read(self, n: int = 0) -> AnyStr:
        """
        Read data.

        :param n: Number of bytes to read. If omitted or zero,
            read until end of region.
        :returns: An 8-bit string.
        """
        if n:
            n = min(n, self.length - self.pos)
        else:
            n = self.length - self.pos
        if not n:  # EOF
            return b"" if "b" in self.fh.mode else ""  # type: ignore[return-value]
        self.pos = self.pos + n
        return self.fh.read(n)

    def readline(self) -> AnyStr:
        """
        Read a line of text.

        :returns: An 8-bit string.
        """
        s: AnyStr = b"" if "b" in self.fh.mode else ""  # type: ignore[assignment]
        newline_character = b"\n" if "b" in self.fh.mode else "\n"
        while True:
            c = self.read(1)
            if not c:
                break
            s = s + c
            if c == newline_character:
                break
        return s

    def readlines(self) -> list[AnyStr]:
        """
        Read multiple lines of text.

        :returns: A list of 8-bit strings.
        """
        lines = []
        while True:
            s = self.readline()
            if not s:
                break
            lines.append(s)
        return lines
