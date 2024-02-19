# Copyright 2016 Facebook, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name Facebook nor the names of its contributors may be used to
#    endorse or promote products derived from this software without specific
#    prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# no unicode literals

try:
    from . import bser
except ImportError:
    from . import pybser as bser

import ctypes

EMPTY_HEADER = b"\x00\x01\x05\x00\x00\x00\x00"


def _read_bytes(fp, buf):
    """Read bytes from a file-like object

    @param fp: File-like object that implements read(int)
    @type fp: file

    @param buf: Buffer to read into
    @type buf: bytes

    @return: buf
    """

    # Do the first read without resizing the input buffer
    offset = 0
    remaining = len(buf)
    while remaining > 0:
        l = fp.readinto((ctypes.c_char * remaining).from_buffer(buf, offset))
        if l is None or l == 0:
            return offset
        offset += l
        remaining -= l
    return offset


def load(fp, mutable=True, value_encoding=None, value_errors=None):
    """Deserialize a BSER-encoded blob.

    @param fp: The file-object to deserialize.
    @type file:

    @param mutable: Whether to return mutable results.
    @type mutable: bool

    @param value_encoding: Optional codec to use to decode values. If
                           unspecified or None, return values as bytestrings.
    @type value_encoding: str

    @param value_errors: Optional error handler for codec. 'strict' by default.
                         The other most common argument is 'surrogateescape' on
                         Python 3. If value_encoding is None, this is ignored.
    @type value_errors: str
    """
    buf = ctypes.create_string_buffer(8192)
    SNIFF_BUFFER_SIZE = len(EMPTY_HEADER)
    header = (ctypes.c_char * SNIFF_BUFFER_SIZE).from_buffer(buf)
    read_len = _read_bytes(fp, header)
    if read_len < len(header):
        return None

    total_len = bser.pdu_len(buf)
    if total_len > len(buf):
        ctypes.resize(buf, total_len)

    body = (ctypes.c_char * (total_len - len(header))).from_buffer(
        buf, len(header))
    read_len = _read_bytes(fp, body)
    if read_len < len(body):
        raise RuntimeError('bser data ended early')

    return bser.loads(
        (ctypes.c_char * total_len).from_buffer(buf, 0),
        mutable,
        value_encoding,
        value_errors)
