"""Types for aiohappyeyeballs."""

import socket

# PY3.9: Import Callable from typing until we drop Python 3.9 support
# https://github.com/python/cpython/issues/87131
from typing import Callable, Tuple, Union

AddrInfoType = Tuple[
    Union[int, socket.AddressFamily],
    Union[int, socket.SocketKind],
    int,
    str,
    Tuple,  # type: ignore[type-arg]
]

SocketFactoryType = Callable[[AddrInfoType], socket.socket]
