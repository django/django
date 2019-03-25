# -*- coding: utf-8 -*-
"""
    sphinx.util.png
    ~~~~~~~~~~~~~~~

    PNG image manipulation helpers.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import binascii
import struct


LEN_IEND = 12
LEN_DEPTH = 22

DEPTH_CHUNK_LEN = struct.pack('!i', 10)
DEPTH_CHUNK_START = b'tEXtDepth\x00'
IEND_CHUNK = b'\x00\x00\x00\x00IEND\xAE\x42\x60\x82'


def read_png_depth(filename):
    # type: (unicode) -> int
    """Read the special tEXt chunk indicating the depth from a PNG file."""
    with open(filename, 'rb') as f:
        f.seek(- (LEN_IEND + LEN_DEPTH), 2)
        depthchunk = f.read(LEN_DEPTH)
        if not depthchunk.startswith(DEPTH_CHUNK_LEN + DEPTH_CHUNK_START):
            # either not a PNG file or not containing the depth chunk
            return None
        else:
            return struct.unpack('!i', depthchunk[14:18])[0]


def write_png_depth(filename, depth):
    # type: (unicode, int) -> None
    """Write the special tEXt chunk indicating the depth to a PNG file.

    The chunk is placed immediately before the special IEND chunk.
    """
    data = struct.pack('!i', depth)
    with open(filename, 'r+b') as f:
        # seek to the beginning of the IEND chunk
        f.seek(-LEN_IEND, 2)
        # overwrite it with the depth chunk
        f.write(DEPTH_CHUNK_LEN + DEPTH_CHUNK_START + data)
        # calculate the checksum over chunk name and data
        crc = binascii.crc32(DEPTH_CHUNK_START + data) & 0xffffffff
        f.write(struct.pack('!I', crc))
        # replace the IEND chunk
        f.write(IEND_CHUNK)
