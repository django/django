# Copyright 2016-present Facebook, Inc.
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

'''Module to deal with filename encoding on the local system, as returned by
Watchman.'''

import sys

from . import (
    compat,
)

if compat.PYTHON3:
    default_local_errors = 'surrogateescape'

    def get_local_encoding():
        if sys.platform == 'win32':
            # Watchman always returns UTF-8 encoded strings on Windows.
            return 'utf-8'
        # On the Python 3 versions we support, sys.getfilesystemencoding never
        # returns None.
        return sys.getfilesystemencoding()
else:
    # Python 2 doesn't support surrogateescape, so use 'strict' by
    # default. Users can register a custom surrogateescape error handler and use
    # that if they so desire.
    default_local_errors = 'strict'

    def get_local_encoding():
        if sys.platform == 'win32':
            # Watchman always returns UTF-8 encoded strings on Windows.
            return 'utf-8'
        fsencoding = sys.getfilesystemencoding()
        if fsencoding is None:
            # This is very unlikely to happen, but if it does, just use UTF-8
            fsencoding = 'utf-8'
        return fsencoding

def encode_local(s):
    return s.encode(get_local_encoding(), default_local_errors)

def decode_local(bs):
    return bs.decode(get_local_encoding(), default_local_errors)
