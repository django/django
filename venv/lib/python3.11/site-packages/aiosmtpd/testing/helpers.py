# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Testing helpers."""

import os
import select
import socket
import struct
import sys
import time
from smtplib import SMTP as SMTP_Client
from typing import List

from aiosmtpd.smtp import Envelope, Session, SMTP

ASYNCIO_CATCHUP_DELAY = float(os.environ.get("ASYNCIO_CATCHUP_DELAY", 0.1))
"""
Delay (in seconds) to give asyncio event loop time to catch up and do things. May need
to be increased for slow and/or overburdened test systems.
"""


def reset_connection(client: SMTP_Client):
    # Close the connection with a TCP RST instead of a TCP FIN.  client must
    # be a smtplib.SMTP instance.
    #
    # https://stackoverflow.com/a/6440364/1570972
    #
    # socket(7) SO_LINGER option.
    #
    # struct linger {
    #   int l_onoff;    /* linger active */
    #   int l_linger;   /* how many seconds to linger for */
    # };
    #
    # Is this correct for Windows/Cygwin and macOS?
    struct_format = "hh" if sys.platform == "win32" else "ii"
    l_onoff = 1
    l_linger = 0
    client.sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_LINGER,
        struct.pack(struct_format, l_onoff, l_linger),
    )
    client.close()


class ReceivingHandler:
    box: List[Envelope] = None

    def __init__(self):
        self.box = []

    async def handle_DATA(
            self, server: SMTP, session: Session, envelope: Envelope
    ) -> str:
        self.box.append(envelope)
        return "250 OK"


def catchup_delay(delay: float = ASYNCIO_CATCHUP_DELAY):
    """
    Sleep for awhile to give asyncio's event loop time to catch up.
    """
    time.sleep(delay)


def send_recv(
    sock: socket.socket, data: bytes, end: bytes = b"\r\n", timeout: float = 0.1
) -> bytes:
    sock.send(data + end)
    slist = [sock]
    result: List[bytes] = []
    while True:
        read_s, _, _ = select.select(slist, [], [], timeout)
        if read_s:
            # We can use sock instead of read_s because slist only contains sock
            result.append(sock.recv(1024))
        else:
            break
    return b"".join(result)
