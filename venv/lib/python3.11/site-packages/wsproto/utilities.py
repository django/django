"""
wsproto/utilities
~~~~~~~~~~~~~~~~~

Utility functions that do not belong in a separate module.
"""
import base64
import hashlib
import os
from typing import Dict, List, Optional, Union

from h11._headers import Headers as H11Headers

from .events import Event
from .typing import Headers

# RFC6455, Section 1.3 - Opening Handshake
ACCEPT_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ProtocolError(Exception):
    pass


class LocalProtocolError(ProtocolError):
    """Indicates an error due to local/programming errors.

    This is raised when the connection is asked to do something that
    is either incompatible with the state or the websocket standard.

    """

    pass  # noqa


class RemoteProtocolError(ProtocolError):
    """Indicates an error due to the remote's actions.

    This is raised when processing the bytes from the remote if the
    remote has sent data that is incompatible with the websocket
    standard.

    .. attribute:: event_hint

       This is a suggested wsproto Event to send to the client based
       on the error. It could be None if no hint is available.

    """

    def __init__(self, message: str, event_hint: Optional[Event] = None) -> None:
        self.event_hint = event_hint
        super().__init__(message)


# Some convenience utilities for working with HTTP headers
def normed_header_dict(h11_headers: Union[Headers, H11Headers]) -> Dict[bytes, bytes]:
    # This mangles Set-Cookie headers. But it happens that we don't care about
    # any of those, so it's OK. For every other HTTP header, if there are
    # multiple instances then you're allowed to join them together with
    # commas.
    name_to_values: Dict[bytes, List[bytes]] = {}
    for name, value in h11_headers:
        name_to_values.setdefault(name, []).append(value)
    name_to_normed_value = {}
    for name, values in name_to_values.items():
        name_to_normed_value[name] = b", ".join(values)
    return name_to_normed_value


# We use this for parsing the proposed protocol list, and for parsing the
# proposed and accepted extension lists. For the proposed protocol list it's
# fine, because the ABNF is just 1#token. But for the extension lists, it's
# wrong, because those can contain quoted strings, which can in turn contain
# commas. XX FIXME
def split_comma_header(value: bytes) -> List[str]:
    return [piece.decode("ascii").strip() for piece in value.split(b",")]


def generate_nonce() -> bytes:
    # os.urandom may be overkill for this use case, but I don't think this
    # is a bottleneck, and better safe than sorry...
    return base64.b64encode(os.urandom(16))


def generate_accept_token(token: bytes) -> bytes:
    accept_token = token + ACCEPT_GUID
    accept_token = hashlib.sha1(accept_token).digest()
    return base64.b64encode(accept_token)
