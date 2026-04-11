"""Helpers for WebSocket protocol versions 13 and 8."""

import functools
import re
from struct import Struct
from typing import TYPE_CHECKING, Final, List, Optional, Pattern, Tuple

from ..helpers import NO_EXTENSIONS
from .models import WSHandshakeError

UNPACK_LEN3 = Struct("!Q").unpack_from
UNPACK_CLOSE_CODE = Struct("!H").unpack
PACK_LEN1 = Struct("!BB").pack
PACK_LEN2 = Struct("!BBH").pack
PACK_LEN3 = Struct("!BBQ").pack
PACK_CLOSE_CODE = Struct("!H").pack
PACK_RANDBITS = Struct("!L").pack
MSG_SIZE: Final[int] = 2**14
MASK_LEN: Final[int] = 4

WS_KEY: Final[bytes] = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# Used by _websocket_mask_python
@functools.lru_cache
def _xor_table() -> List[bytes]:
    return [bytes(a ^ b for a in range(256)) for b in range(256)]


def _websocket_mask_python(mask: bytes, data: bytearray) -> None:
    """Websocket masking function.

    `mask` is a `bytes` object of length 4; `data` is a `bytearray`
    object of any length. The contents of `data` are masked with `mask`,
    as specified in section 5.3 of RFC 6455.

    Note that this function mutates the `data` argument.

    This pure-python implementation may be replaced by an optimized
    version when available.

    """
    assert isinstance(data, bytearray), data
    assert len(mask) == 4, mask

    if data:
        _XOR_TABLE = _xor_table()
        a, b, c, d = (_XOR_TABLE[n] for n in mask)
        data[::4] = data[::4].translate(a)
        data[1::4] = data[1::4].translate(b)
        data[2::4] = data[2::4].translate(c)
        data[3::4] = data[3::4].translate(d)


if TYPE_CHECKING or NO_EXTENSIONS:  # pragma: no cover
    websocket_mask = _websocket_mask_python
else:
    try:
        from .mask import _websocket_mask_cython  # type: ignore[import-not-found]

        websocket_mask = _websocket_mask_cython
    except ImportError:  # pragma: no cover
        websocket_mask = _websocket_mask_python


_WS_EXT_RE: Final[Pattern[str]] = re.compile(
    r"^(?:;\s*(?:"
    r"(server_no_context_takeover)|"
    r"(client_no_context_takeover)|"
    r"(server_max_window_bits(?:=(\d+))?)|"
    r"(client_max_window_bits(?:=(\d+))?)))*$"
)

_WS_EXT_RE_SPLIT: Final[Pattern[str]] = re.compile(r"permessage-deflate([^,]+)?")


def ws_ext_parse(extstr: Optional[str], isserver: bool = False) -> Tuple[int, bool]:
    if not extstr:
        return 0, False

    compress = 0
    notakeover = False
    for ext in _WS_EXT_RE_SPLIT.finditer(extstr):
        defext = ext.group(1)
        # Return compress = 15 when get `permessage-deflate`
        if not defext:
            compress = 15
            break
        match = _WS_EXT_RE.match(defext)
        if match:
            compress = 15
            if isserver:
                # Server never fail to detect compress handshake.
                # Server does not need to send max wbit to client
                if match.group(4):
                    compress = int(match.group(4))
                    # Group3 must match if group4 matches
                    # Compress wbit 8 does not support in zlib
                    # If compress level not support,
                    # CONTINUE to next extension
                    if compress > 15 or compress < 9:
                        compress = 0
                        continue
                if match.group(1):
                    notakeover = True
                # Ignore regex group 5 & 6 for client_max_window_bits
                break
            else:
                if match.group(6):
                    compress = int(match.group(6))
                    # Group5 must match if group6 matches
                    # Compress wbit 8 does not support in zlib
                    # If compress level not support,
                    # FAIL the parse progress
                    if compress > 15 or compress < 9:
                        raise WSHandshakeError("Invalid window size")
                if match.group(2):
                    notakeover = True
                # Ignore regex group 5 & 6 for client_max_window_bits
                break
        # Return Fail if client side and not match
        elif not isserver:
            raise WSHandshakeError("Extension for deflate not supported" + ext.group(1))

    return compress, notakeover


def ws_ext_gen(
    compress: int = 15, isserver: bool = False, server_notakeover: bool = False
) -> str:
    # client_notakeover=False not used for server
    # compress wbit 8 does not support in zlib
    if compress < 9 or compress > 15:
        raise ValueError(
            "Compress wbits must between 9 and 15, zlib does not support wbits=8"
        )
    enabledext = ["permessage-deflate"]
    if not isserver:
        enabledext.append("client_max_window_bits")

    if compress < 15:
        enabledext.append("server_max_window_bits=" + str(compress))
    if server_notakeover:
        enabledext.append("server_no_context_takeover")
    # if client_notakeover:
    #     enabledext.append('client_no_context_takeover')
    return "; ".join(enabledext)
