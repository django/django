# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import socket
from typing import Iterable, NamedTuple


class StatusCode(NamedTuple):
    code: int
    mesg: bytes

    def __call__(self, *args: bytes) -> "StatusCode":
        nmsg = self.mesg % args
        return StatusCode(self.code, nmsg)

    def to_bytes(self, crlf: bool = False) -> bytes:
        """
        Returns code + mesg as bytes.
        WARNING: This is NOT identical to __str()__.encode()!
        """
        _crlf = b"\r\n" if crlf else b""
        return str(self.code).encode() + b" " + self.mesg + _crlf

    def to_str(self, crlf: bool = False) -> str:
        """
        Returns code + mesg as a string.
        WARNING: This is NOT identical to __str__()!
        """
        _crlf = "\r\n" if crlf else ""
        return str(self.code) + " " + self.mesg.decode() + _crlf


_COMMON_COMMANDS = [
    b"AUTH",
    b"DATA",
    b"HELP",
    b"MAIL",
    b"NOOP",
    b"QUIT",
    b"RCPT",
    b"RSET",
    b"VRFY",
]

SUPPORTED_COMMANDS_NOTLS = _COMMON_COMMANDS + [b"EHLO", b"HELO"]
SUPPORTED_COMMANDS_NOTLS.sort()

SUPPORTED_COMMANDS_TLS = SUPPORTED_COMMANDS_NOTLS + [b"STARTTLS"]
SUPPORTED_COMMANDS_TLS.sort()

SUPPORTED_COMMANDS_LMTP = _COMMON_COMMANDS + [b"LHLO"]
SUPPORTED_COMMANDS_LMTP.sort()


def _suppcmd(commands: Iterable[bytes]) -> bytes:
    return b"Supported commands: " + b" ".join(commands)


class SMTP_STATUS_CODES:
    # Enforced conventions:
    #  1. Must start with uppercase "S"
    #  2. Must have the 3-digit status code following "S"
    #  3. Must be instances of StatusCode

    S220_READY_TLS = StatusCode(220, b"Ready to start TLS")
    S221_BYE = StatusCode(221, b"Bye")
    S235_AUTH_SUCCESS = StatusCode(235, b"2.7.0 Authentication successful")

    S250_OK = StatusCode(250, b"OK")
    S250_FQDN = StatusCode(250, bytes(socket.getfqdn(), "utf-8"))

    S250_SUPPCMD_LMTP = StatusCode(250, _suppcmd(SUPPORTED_COMMANDS_LMTP))
    S250_SUPPCMD_NOTLS = StatusCode(250, _suppcmd(SUPPORTED_COMMANDS_NOTLS))
    S250_SUPPCMD_TLS = StatusCode(250, _suppcmd(SUPPORTED_COMMANDS_TLS))

    S250_SYNTAX_AUTH = StatusCode(250, b"Syntax: AUTH <mechanism>")
    S250_SYNTAX_DATA = StatusCode(250, b"Syntax: DATA")
    S250_SYNTAX_EHLO = StatusCode(250, b"Syntax: EHLO hostname")
    S250_SYNTAX_HELO = StatusCode(250, b"Syntax: HELO hostname")
    S250_SYNTAX_MAIL = StatusCode(250, b"Syntax: MAIL FROM: <address>")
    S250_SYNTAX_NOOP = StatusCode(250, b"Syntax: NOOP [ignored]")
    S250_SYNTAX_QUIT = StatusCode(250, b"Syntax: QUIT")
    S250_SYNTAX_RCPT = StatusCode(250, b"Syntax: RCPT TO: <address>")
    S250_SYNTAX_RSET = StatusCode(250, b"Syntax: RSET")
    S250_SYNTAX_STARTTLS = StatusCode(250, b"Syntax: STARTTLS")
    S250_SYNTAX_VRFY = StatusCode(250, b"Syntax: VRFY <address>")

    S250_SYNTAX_MAIL_E = StatusCode(
        250, S250_SYNTAX_MAIL.mesg + b" [SP <mail-parameters>]"
    )
    S250_SYNTAX_RCPT_E = StatusCode(
        250, S250_SYNTAX_RCPT.mesg + b" [SP <mail-parameters>]"
    )

    S252_CANNOT_VRFY = StatusCode(
        252,
        b"Cannot VRFY user, but will accept message and attempt delivery",
    )

    S334_AUTH_EMPTYPROMPT = StatusCode(334, b"")
    S334_AUTH_USERNAME = StatusCode(334, b"VXNlciBOYW1lAA==")
    S334_AUTH_PASSWORD = StatusCode(334, b"UGFzc3dvcmQA")

    S354_DATA_ENDWITH = StatusCode(354, b"End data with <CR><LF>.<CR><LF>")

    S421_TOO_MANY = StatusCode(421, b"4.7.0 %b sent too many times")

    S450_DEST_GREYLIST = StatusCode(
        450, b"4.2.0 Recipient address rejected: Greylisted"
    )
    S450_SERVICE_UNAVAIL = StatusCode(450, b"4.3.2 Service currently unavailable")
    S452_TOO_MANY_CONN = StatusCode(452, b"4.7.0 Too many connections")
    S454_TLS_NA = StatusCode(454, b"TLS not available")

    S500_BAD_SYNTAX = StatusCode(500, b"Error: bad syntax")
    S500_CMD_TOO_LONG = StatusCode(500, b"Command line too long")
    S500_DATALINE_TOO_LONG = StatusCode(500, b"Line too long (see RFC5321 4.5.3.1.6)")
    S500_STRICT_ASCII = StatusCode(500, b"Error: strict ASCII mode")

    S500_CMD_UNRECOG = StatusCode(500, b'Error: command "%b" not recognized')
    S500_AUTH_UNRECOG = StatusCode(500, b"Error: command 'AUTH' not recognized")

    S501_AUTH_ABORTED = StatusCode(501, b"5.7.0 Auth aborted")
    S501_AUTH_NOTB64 = StatusCode(501, b"5.5.2 Can't decode base64")
    S501_AUTH_CANTSPLIT = StatusCode(501, b"5.5.2 Can't split auth value")

    S501_MAIL_BODY = StatusCode(501, b"Error: BODY can only be one of 7BIT, 8BITMIME")

    S501_SMTPUTF8_DISABLED = StatusCode(501, b"Error: SMTPUTF8 disabled")
    S501_SMTPUTF8_NOARG = StatusCode(501, b"Error: SMTPUTF8 takes no arguments")

    S501_SUPPCMD_NOTLS = StatusCode(501, S250_SUPPCMD_NOTLS.mesg)

    S501_SYNTAX_DATA = StatusCode(501, S250_SYNTAX_DATA.mesg)
    S501_SYNTAX_EHLO = StatusCode(501, S250_SYNTAX_EHLO.mesg)
    S501_SYNTAX_HELO = StatusCode(501, S250_SYNTAX_HELO.mesg)
    S501_SYNTAX_MAIL = StatusCode(501, S250_SYNTAX_MAIL.mesg)
    S501_SYNTAX_MAIL_E = StatusCode(501, S250_SYNTAX_MAIL_E.mesg)
    S501_SYNTAX_QUIT = StatusCode(501, S250_SYNTAX_QUIT.mesg)
    S501_SYNTAX_RCPT = StatusCode(501, S250_SYNTAX_RCPT.mesg)
    S501_SYNTAX_RCPT_E = StatusCode(501, S250_SYNTAX_RCPT_E.mesg)
    S501_SYNTAX_RSET = StatusCode(501, S250_SYNTAX_RSET.mesg)
    S501_SYNTAX_STARTTLS = StatusCode(501, S250_SYNTAX_STARTTLS.mesg)
    S501_SYNTAX_VRFY = StatusCode(501, S250_SYNTAX_VRFY.mesg)

    S501_TOO_FEW = StatusCode(501, b"Not enough value")
    S501_TOO_MANY = StatusCode(501, b"Too many values")

    S502_EXPN_NOTIMPL = StatusCode(502, b"EXPN not implemented")
    S502_VRFY_COULDNT = StatusCode(502, b"Could not VRFY %b")
    S502_TOO_MANY_UNRECOG = StatusCode(
        502, b"5.5.1 Too many unrecognized commands, goodbye."
    )

    S503_ALREADY_AUTH = StatusCode(503, b"Already authenticated")
    S503_EHLO_FIRST = StatusCode(503, b"Error: send EHLO first")
    S503_HELO_FIRST = StatusCode(503, b"Error: send HELO first")
    S503_MAIL_NEEDED = StatusCode(503, b"Error: need MAIL command")
    S503_MAIL_NESTED = StatusCode(503, b"Error: nested MAIL command")
    S503_RCPT_NEEDED = StatusCode(503, b"Error: need RCPT command")

    S504_AUTH_UNRECOG = StatusCode(504, b"5.5.4 Unrecognized authentication type")
    S530_STARTTLS_FIRST = StatusCode(530, b"Must issue a STARTTLS command first")
    S530_AUTH_REQUIRED = StatusCode(530, b"5.7.0 Authentication required")
    S535_AUTH_INVALID = StatusCode(535, b"5.7.8 Authentication credentials invalid")
    S538_AUTH_ENCRYPTREQ = StatusCode(
        538,
        b"5.7.11 Encryption required for requested authentication mechanism",
    )

    S550_DEST_UNKNOWN = StatusCode(
        550, b"5.1.1 Recipient address rejected: User unknown"
    )
    S550_NO_RELAY = StatusCode(550, b"5.7.1 Unable to relay")
    S552_EXCEED_SIZE = StatusCode(
        552, b"Error: message size exceeds fixed maximum message size"
    )
    S552_DATA_TOO_MUCH = StatusCode(552, b"Error: Too much mail data")
    S553_MALFORMED = StatusCode(553, b"5.1.3 Error: malformed address")
    S554_LACK_SECURITY = StatusCode(554, b"Command refused due to lack of security")

    S555_MAIL_PARAMS_UNRECOG = StatusCode(
        555,
        b"MAIL FROM parameters not recognized or not implemented",
    )
    S555_RCPT_PARAMS_UNRECOG = StatusCode(
        555, b"RCPT TO parameters not recognized or not implemented"
    )
