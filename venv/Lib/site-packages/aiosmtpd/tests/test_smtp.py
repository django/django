# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Test the SMTP protocol."""

import asyncio
import itertools
import logging
import socket
import sys
import time
import warnings
from asyncio.transports import Transport
from base64 import b64encode
from contextlib import suppress
from smtplib import (
    SMTP as SMTPClient,
    SMTPAuthenticationError,
    SMTPDataError,
    SMTPResponseException,
    SMTPServerDisconnected,
)
from textwrap import dedent
from typing import cast, Any, Callable, Generator, List, Tuple, Union

import pytest
from pytest_mock import MockFixture

from .conftest import Global, controller_data, handler_data
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import (
    BOGUS_LIMIT,
    CALL_LIMIT_DEFAULT,
    MISSING,
    SMTP as Server,
    AuthResult,
    Envelope as SMTPEnvelope,
    LoginPassword,
    Session as SMTPSession,
    __ident__ as GREETING,
    auth_mechanism,
)
from aiosmtpd.testing.helpers import (
    ReceivingHandler,
    catchup_delay,
    reset_connection,
    send_recv,
)
from aiosmtpd.testing.statuscodes import SMTP_STATUS_CODES as S

CRLF = "\r\n"
BCRLF = b"\r\n"
MAIL_LOG = logging.getLogger("mail.log")
MAIL_LOG.setLevel(logging.DEBUG)
B64EQUALS = b64encode(b"=").decode()

# fh = logging.FileHandler("~smtp.log")
# fh.setFormatter(logging.Formatter("{asctime} - {levelname} - {message}", style="{"))
# fh.setLevel(logging.DEBUG)
# MAIL_LOG.addHandler(fh)


# region #### Test Helpers ############################################################


def auth_callback(mechanism, login, password) -> bool:
    return login and login.decode() == "goodlogin"


def assert_nopassleak(passwd: str, record_tuples: List[Tuple[str, int, str]]):
    """
    :param passwd: The password we're looking for in the logs
    :param record_tuples: Usually caplog.record_tuples
    """
    passwd_b64 = b64encode(passwd.encode("ascii")).decode("ascii")
    for _logname, _loglevel, logmsg in record_tuples:
        assert passwd not in logmsg
        assert passwd_b64 not in logmsg


class UndescribableError(Exception):
    def __str__(self):
        raise Exception()


class ErrorSMTP(Server):
    exception_type = ValueError

    async def smtp_HELO(self, hostname: str):
        raise self.exception_type("test")


# endregion


# region #### Special-Purpose Handlers ################################################


# noinspection TimingAttack
class PeekerHandler:
    sess: SMTPSession = None
    login: Union[str, bytes, None] = None
    login_data: Any = None
    mechanism: Union[str, bytes, None] = None
    password: Union[str, bytes, None] = None

    # Please do not insert "_" after auth; that will 'fool' SMTP into thinking this is
    # an AUTH Mechanism, and we totally do NOT want that.
    def authcallback(self, mechanism: str, login: bytes, password: bytes) -> bool:
        self.login = login
        self.password = password
        return login == b"goodlogin" and password == b"goodpasswd"

    def authenticator(
        self,
        server: Server,
        session: SMTPSession,
        envelope: SMTPEnvelope,
        mechanism: str,
        login_data: Tuple[bytes, bytes],
    ) -> AuthResult:
        self.sess = session
        self.mechanism = mechanism
        self.login_data = login_data
        userb, passb = login_data
        if userb == b"failme_with454":
            return AuthResult(
                success=False,
                handled=False,
                message="454 4.7.0 Temporary authentication failure",
            )
        else:
            self.login = userb
            self.password = passb
            return AuthResult(success=True, auth_data=login_data)

    async def handle_MAIL(
        self,
        server: Server,
        session: SMTPSession,
        envelope: SMTPEnvelope,
        address: str,
        mail_options: dict,
    ) -> str:
        self.sess = session
        return S.S250_OK.to_str()

    async def auth_DENYMISSING(self, server, args):
        return MISSING

    async def auth_DENYFALSE(self, server, args):
        return False

    async def auth_NONE(self, server: Server, args):
        await server.push(S.S235_AUTH_SUCCESS.to_str())
        return None

    async def auth_NULL(self, server, args):
        return "NULL_login"

    async def auth_DONT(self, server, args):
        return MISSING

    async def auth_WITH_UNDERSCORE(self, server: Server, args) -> str:
        """
        Be careful when using this AUTH mechanism; log_client_response is set to
        True, and this will raise some severe warnings.
        """
        await server.challenge_auth(
            "challenge", encode_to_b64=False, log_client_response=True
        )
        return "250 OK"

    @auth_mechanism("with-dash")
    async def auth_WITH_DASH(self, server, args):
        return "250 OK"

    async def auth_WITH__MULTI__DASH(self, server, args):
        return "250 OK"


class StoreEnvelopeOnVRFYHandler:
    """Saves envelope for later inspection when handling VRFY."""

    envelope = None

    async def handle_VRFY(
        self, server: Server, session: SMTPSession, envelope: SMTPEnvelope, addr: str
    ) -> str:
        self.envelope = envelope
        return S.S250_OK.to_str()


class ErroringHandler:
    error = None
    custom_response = False

    async def handle_DATA(self, server, session, envelope) -> str:
        return "499 Could not accept the message"

    async def handle_exception(self, error) -> str:
        self.error = error
        if not self.custom_response:
            return "500 ErroringHandler handling error"
        else:
            return "451 Temporary error: ({}) {}".format(
                error.__class__.__name__, str(error)
            )


class ErroringHandlerConnectionLost:
    error = None

    async def handle_DATA(self, server, session, envelope):
        raise ConnectionResetError("ErroringHandlerConnectionLost test")

    async def handle_exception(self, error):
        self.error = error


class ErroringErrorHandler:
    error = None

    async def handle_exception(self, error: Exception):
        self.error = error
        raise ValueError("ErroringErrorHandler test")


class UndescribableErrorHandler:
    error = None

    async def handle_exception(self, error: Exception):
        self.error = error
        raise UndescribableError()


class SleepingHeloHandler:
    async def handle_HELO(
        self,
        server: Server,
        session: SMTPSession,
        envelope: SMTPEnvelope,
        hostname: str,
    ) -> str:
        await asyncio.sleep(0.01)
        session.host_name = hostname
        return "250 {}".format(server.hostname)


# endregion


# region #### Special-Purpose Controllers #############################################


# These are either impractical or impossible to implement using Controller


class TimeoutController(Controller):
    Delay: float = 1.0

    def factory(self):
        return Server(self.handler, timeout=self.Delay)


class ErrorController(Controller):
    def factory(self):
        return ErrorSMTP(self.handler)


class CustomHostnameController(Controller):
    custom_name = "custom.localhost"

    def factory(self):
        return Server(self.handler, hostname=self.custom_name)


class CustomIdentController(Controller):
    ident: bytes = b"Identifying SMTP v2112"

    def factory(self):
        return Server(self.handler, ident=self.ident.decode())


# endregion


# region ##### Fixtures ###############################################################


@pytest.fixture
def transport_resp(mocker: MockFixture) -> Tuple[Transport, list]:
    responses = []
    mocked = mocker.Mock()
    mocked.write = responses.append
    #
    return cast(Transport, mocked), responses


@pytest.fixture
def get_protocol(
    temp_event_loop: asyncio.AbstractEventLoop,
    transport_resp: Any,
) -> Callable[..., Server]:
    transport, _ = transport_resp

    def getter(*args, **kwargs) -> Server:
        proto = Server(*args, loop=temp_event_loop, **kwargs)
        proto.connection_made(transport)
        return proto

    return getter


# region #### Fixtures: Controllers ##################################################


@pytest.fixture
def auth_peeker_controller(
    get_controller: Callable[..., Controller]
) -> Generator[Controller, None, None]:
    handler = PeekerHandler()
    controller = get_controller(
        handler,
        decode_data=True,
        enable_SMTPUTF8=True,
        auth_require_tls=False,
        auth_callback=handler.authcallback,
        auth_exclude_mechanism=["DONT"],
    )
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    controller.stop()


@pytest.fixture
def authenticator_peeker_controller(
    get_controller: Callable[..., Controller]
) -> Generator[Controller, None, None]:
    handler = PeekerHandler()
    controller = get_controller(
        handler,
        decode_data=True,
        enable_SMTPUTF8=True,
        auth_require_tls=False,
        authenticator=handler.authenticator,
        auth_exclude_mechanism=["DONT"],
    )
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    controller.stop()


@pytest.fixture
def decoding_authnotls_controller(
    get_handler: Callable,
    get_controller: Callable[..., Controller]
) -> Generator[Controller, None, None]:
    handler = get_handler()
    controller = get_controller(
        handler,
        decode_data=True,
        enable_SMTPUTF8=True,
        auth_require_tls=False,
        auth_callback=auth_callback,
    )
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    # Some test cases need to .stop() the controller inside themselves
    # in such cases, we must suppress Controller's raise of AssertionError
    # because Controller doesn't like .stop() to be invoked more than once
    with suppress(AssertionError):
        controller.stop()


@pytest.fixture
def error_controller(get_handler: Callable) -> Generator[ErrorController, None, None]:
    handler = get_handler()
    controller = ErrorController(handler)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    controller.stop()


# endregion

# endregion


class _CommonMethods:
    """Contain snippets that keep being performed again and again and again..."""

    def _helo(self, client: SMTPClient, domain: str = "example.org") -> bytes:
        code, mesg = client.helo(domain)
        assert code == 250
        return mesg

    def _ehlo(self, client: SMTPClient, domain: str = "example.com") -> bytes:
        code, mesg = client.ehlo(domain)
        assert code == 250
        return mesg


class TestProtocol:
    def test_honors_mail_delimiters(
        self, temp_event_loop, transport_resp, get_protocol
    ):
        handler = ReceivingHandler()
        protocol = get_protocol(handler)
        data = b"test\r\nmail\rdelimiters\nsaved\r\n"
        protocol.data_received(
            BCRLF.join(
                [
                    b"HELO example.org",
                    b"MAIL FROM: <anne@example.com>",
                    b"RCPT TO: <anne@example.com>",
                    b"DATA",
                    data + b".",
                    b"QUIT\r\n",
                ]
            )
        )
        with suppress(asyncio.CancelledError):
            temp_event_loop.run_until_complete(protocol._handler_coroutine)
        _, responses = transport_resp
        assert responses[5] == S.S250_OK.to_bytes() + b"\r\n"
        assert len(handler.box) == 1
        assert handler.box[0].content == data

    def test_empty_email(self, temp_event_loop, transport_resp, get_protocol):
        handler = ReceivingHandler()
        protocol = get_protocol(handler)
        protocol.data_received(
            BCRLF.join(
                [
                    b"HELO example.org",
                    b"MAIL FROM: <anne@example.com>",
                    b"RCPT TO: <anne@example.com>",
                    b"DATA",
                    b".",
                    b"QUIT\r\n",
                ]
            )
        )
        with suppress(asyncio.CancelledError):
            temp_event_loop.run_until_complete(protocol._handler_coroutine)
        _, responses = transport_resp
        assert responses[5] == S.S250_OK.to_bytes() + b"\r\n"
        assert len(handler.box) == 1
        assert handler.box[0].content == b""


@pytest.mark.usefixtures("plain_controller")
@controller_data(
    decode_data=True,
    enable_SMTPUTF8=True,
)
class TestSMTP(_CommonMethods):
    valid_mailfrom_addresses = [
        # no space between colon and address
        "anne@example.com",
        "<anne@example.com>",
        # one space between colon and address
        " anne@example.com",
        " <anne@example.com>",
        # multiple spaces between colon and address
        "  anne@example.com",
        "  <anne@example.com>",
        # non alphanums in local part
        "anne.arthur@example.com",
        "anne+promo@example.com",
        "anne-arthur@example.com",
        "anne_arthur@example.com",
        "_@example.com",
        # IP address in domain part
        "anne@127.0.0.1",
        "anne@[127.0.0.1]",
        "anne@[IPv6:2001:db8::1]",
        "anne@[IPv6::1]",
        # email with comments -- obsolete, but still valid
        "anne(comment)@example.com",
        "(comment)anne@example.com",
        "anne@example.com(comment)",
        "anne@machine(comment).  example",  # RFC5322 § A.6.3
        # source route -- RFC5321 § 4.1.2 "MUST BE accepted"
        "<@example.org:anne@example.com>",
        "<@example.net,@example.org:anne@example.com>",
        # strange -- but valid -- addresses
        "anne@mail",
        '""@example.com',
        '<""@example.com>',
        '" "@example.com',
        '"anne..arthur"@example.com',
        "mailhost!anne@example.com",
        "anne%example.org@example.com",
        'much."more\\ unusual"@example.com',
        'very."(),:;<>[]".VERY."very@\\ "very.unusual@strange.example.com',
        # more from RFC3696 § 3
        # 'Abc\\@def@example.com', -- get_addr_spec does not support this
        "Fred\\ Bloggs@example.com",
        "Joe.\\\\Blow@example.com",
        '"Abc@def"@example.com',
        '"Fred Bloggs"@example.com',
        "customer/department=shipping@example.com",
        "$A12345@example.com",
        "!def!xyz%abc@example.com",
        "a" * 65 + "@example.com",  # local-part > 64 chars -- see Issue#257
        "b" * 488 + "@example.com",  # practical longest for MAIL FROM
        "c" * 500,  # practical longest domainless for MAIL FROM
    ]

    valid_rcptto_addresses = valid_mailfrom_addresses + [
        # Postmaster -- RFC5321 § 4.1.1.3
        "<Postmaster>",
        "b" * 490 + "@example.com",  # practical longest for RCPT TO
        "c" * 502,  # practical longest domainless for RCPT TO
    ]

    invalid_email_addresses = [
        "<@example.com>",  # null local part
        "<johnathon@>",  # null domain part
    ]

    @pytest.mark.parametrize("data", [b"\x80FAIL\r\n", b"\x80 FAIL\r\n"])
    def test_binary(self, client, data):
        client.sock.send(data)
        assert client.getreply() == S.S500_BAD_SYNTAX

    def test_helo(self, client):
        resp = client.helo("example.com")
        assert resp == S.S250_FQDN

    def test_close_then_continue(self, client):
        self._helo(client)
        client.close()
        client.connect(*Global.SrvAddr)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S503_HELO_FIRST

    def test_helo_no_hostname(self, client):
        client.local_hostname = ""
        resp = client.helo("")
        assert resp == S.S501_SYNTAX_HELO

    def test_helo_duplicate(self, client):
        self._helo(client, "example.org")
        self._helo(client, "example.com")

    def test_ehlo(self, client):
        code, mesg = client.ehlo("example.com")
        lines = mesg.splitlines()
        assert lines == [
            bytes(socket.getfqdn(), "utf-8"),
            b"SIZE 33554432",
            b"SMTPUTF8",
            b"HELP",
        ]

    def test_ehlo_duplicate(self, client):
        self._ehlo(client, "example.com")
        self._ehlo(client, "example.org")

    def test_ehlo_no_hostname(self, client):
        client.local_hostname = ""
        resp = client.ehlo("")
        assert resp == S.S501_SYNTAX_EHLO

    def test_helo_then_ehlo(self, client):
        self._helo(client, "example.com")
        self._ehlo(client, "example.org")

    def test_ehlo_then_helo(self, client):
        self._ehlo(client, "example.org")
        self._helo(client, "example.com")

    def test_noop(self, client):
        resp = client.noop()
        assert resp == S.S250_OK

    def test_noop_with_arg(self, plain_controller, client):
        # smtplib.SMTP.noop() doesn't accept args
        resp = client.docmd("NOOP ok")
        assert resp == S.S250_OK

    def test_quit(self, client):
        resp = client.quit()
        assert resp == S.S221_BYE

    def test_quit_with_args(self, client):
        resp = client.docmd("QUIT oops")
        assert resp == S.S501_SYNTAX_QUIT

    def test_help(self, client):
        resp = client.docmd("HELP")
        assert resp == S.S250_SUPPCMD_NOTLS

    @pytest.mark.parametrize(
        "command",
        [
            "HELO",
            "EHLO",
            "MAIL",
            "RCPT",
            "DATA",
            "RSET",
            "NOOP",
            "QUIT",
            "VRFY",
            "AUTH",
        ],
    )
    def test_help_(self, client, command):
        resp = client.docmd(f"HELP {command}")
        syntax = getattr(S, f"S250_SYNTAX_{command}")
        assert resp == syntax

    @pytest.mark.parametrize(
        "command",
        [
            "MAIL",
            "RCPT",
        ],
    )
    def test_help_esmtp(self, client, command):
        self._ehlo(client)
        resp = client.docmd(f"HELP {command}")
        syntax = getattr(S, f"S250_SYNTAX_{command}_E")
        assert resp == syntax

    def test_help_bad_arg(self, client):
        resp = client.docmd("HELP me!")
        assert resp == S.S501_SUPPCMD_NOTLS

    def test_expn(self, client):
        resp = client.expn("anne@example.com")
        assert resp == S.S502_EXPN_NOTIMPL

    @pytest.mark.parametrize(
        "command",
        ["MAIL FROM: <anne@example.com>", "RCPT TO: <anne@example.com>", "DATA"],
        ids=lambda x: x.split()[0],
    )
    def test_no_helo(self, client, command):
        resp = client.docmd(command)
        assert resp == S.S503_HELO_FIRST

    @pytest.mark.parametrize(
        "address",
        valid_mailfrom_addresses,
        ids=itertools.count(),
    )
    def test_mail_valid_address(self, client, address):
        self._ehlo(client)
        resp = client.docmd(f"MAIL FROM:{address}")
        assert resp == S.S250_OK

    @pytest.mark.parametrize(
        "command",
        [
            "MAIL",
            "MAIL <anne@example.com>",
            "MAIL FROM:",
            "MAIL FROM: <anne@example.com> SIZE=10000",
            "MAIL FROM: Anne <anne@example.com>",
        ],
        ids=["noarg", "nofrom", "noaddr", "params_noesmtp", "malformed"],
    )
    def test_mail_smtp_errsyntax(self, client, command):
        self._helo(client)
        resp = client.docmd(command)
        assert resp == S.S501_SYNTAX_MAIL

    @pytest.mark.parametrize(
        "param",
        [
            "SIZE=10000",
            " SIZE=10000",
            "SIZE=10000 ",
        ],
        ids=["norm", "extralead", "extratail"],
    )
    def test_mail_params_esmtp(self, client, param):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> " + param)
        assert resp == S.S250_OK

    def test_mail_from_twice(self, client):
        self._helo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S503_MAIL_NESTED

    @pytest.mark.parametrize(
        "command",
        [
            "MAIL FROM: <anne@example.com> SIZE 10000",
            "MAIL FROM: <anne@example.com> SIZE",
            "MAIL FROM: <anne@example.com> #$%=!@#",
            "MAIL FROM: <anne@example.com> SIZE = 10000",
        ],
        ids=["malformed", "missing", "badsyntax", "space"],
    )
    def test_mail_esmtp_errsyntax(self, client, command):
        self._ehlo(client)
        resp = client.docmd(command)
        assert resp == S.S501_SYNTAX_MAIL_E

    def test_mail_esmtp_params_unrecognized(self, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> FOO=BAR")
        assert resp == S.S555_MAIL_PARAMS_UNRECOG

    def test_bpo27931fix_smtp(self, client):
        self._helo(client)
        resp = client.docmd('MAIL FROM: <""@example.com>')
        assert resp == S.S250_OK
        resp = client.docmd('RCPT TO: <""@example.org>')
        assert resp == S.S250_OK

    @pytest.mark.parametrize(
        "address",
        invalid_email_addresses,
        ids=itertools.count(),
    )
    def test_mail_invalid_address(self, client, address):
        self._helo(client)
        resp = client.docmd(f"MAIL FROM: {address}")
        assert resp == S.S553_MALFORMED

    @pytest.mark.parametrize("address", invalid_email_addresses, ids=itertools.count())
    def test_mail_esmtp_invalid_address(self, client, address):
        self._ehlo(client)
        resp = client.docmd(f"MAIL FROM: {address} SIZE=28113")
        assert resp == S.S553_MALFORMED

    def test_rcpt_no_mail(self, client):
        self._helo(client)
        resp = client.docmd("RCPT TO: <anne@example.com>")
        assert resp == S.S503_MAIL_NEEDED

    @pytest.mark.parametrize(
        "command",
        [
            "RCPT",
            "RCPT <anne@example.com>",
            "RCPT TO:",
            "RCPT TO: <bart@example.com> SIZE=1000",
            "RCPT TO: bart <bart@example.com>",
        ],
        ids=["noarg", "noto", "noaddr", "params", "malformed"],
    )
    def test_rcpt_smtp_errsyntax(self, client, command):
        self._helo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd(command)
        assert resp == S.S501_SYNTAX_RCPT

    @pytest.mark.parametrize(
        "command",
        [
            "RCPT",
            "RCPT <anne@example.com>",
            "RCPT TO:",
            "RCPT TO: <bart@example.com> #$%=!@#",
            "RCPT TO: bart <bart@example.com>",
        ],
        ids=["noarg", "noto", "noaddr", "badparams", "malformed"],
    )
    def test_rcpt_esmtp_errsyntax(self, client, command):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd(command)
        assert resp == S.S501_SYNTAX_RCPT_E

    def test_rcpt_unknown_params(self, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd("RCPT TO: <bart@example.com> FOOBAR")
        assert resp == S.S555_RCPT_PARAMS_UNRECOG

    @pytest.mark.parametrize("address", valid_rcptto_addresses, ids=itertools.count())
    def test_rcpt_valid_address(self, client, address):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd(f"RCPT TO: {address}")
        assert resp == S.S250_OK

    @pytest.mark.parametrize("address", invalid_email_addresses, ids=itertools.count())
    def test_rcpt_invalid_address(self, client, address):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd(f"RCPT TO: {address}")
        assert resp == S.S553_MALFORMED

    def test_bpo27931fix_esmtp(self, client):
        self._ehlo(client)
        resp = client.docmd('MAIL FROM: <""@example.com> SIZE=28113')
        assert resp == S.S250_OK
        resp = client.docmd('RCPT TO: <""@example.org>')
        assert resp == S.S250_OK

    def test_rset(self, client):
        resp = client.rset()
        assert resp == S.S250_OK

    def test_rset_with_arg(self, client):
        resp = client.docmd("RSET FOO")
        assert resp == S.S501_SYNTAX_RSET

    def test_vrfy(self, client):
        resp = client.docmd("VRFY <anne@example.com>")
        assert resp == S.S252_CANNOT_VRFY

    def test_vrfy_no_arg(self, client):
        resp = client.docmd("VRFY")
        assert resp == S.S501_SYNTAX_VRFY

    def test_vrfy_not_address(self, client):
        resp = client.docmd("VRFY @@")
        assert resp == S.S502_VRFY_COULDNT(b"@@")

    def test_data_no_rcpt(self, client):
        self._helo(client)
        resp = client.docmd("DATA")
        assert resp == S.S503_RCPT_NEEDED

    def test_data_354(self, plain_controller, client):
        self._helo(client)
        resp = client.docmd("MAIL FROM: <alice@example.org>")
        assert resp == S.S250_OK
        resp = client.docmd("RCPT TO: <bob@example.org>")
        assert resp == S.S250_OK
        # Note: We NEED to manually stop the controller if we must abort while
        # in DATA phase. For reasons unclear, if we don't do that we'll hang
        # the test case should the assertion fail
        try:
            resp = client.docmd("DATA")
            assert resp == S.S354_DATA_ENDWITH
        finally:
            plain_controller.stop()

    def test_data_invalid_params(self, client):
        self._helo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd("RCPT TO: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd("DATA FOOBAR")
        assert resp == S.S501_SYNTAX_DATA

    def test_empty_command(self, client):
        resp = client.docmd("")
        assert resp == S.S500_BAD_SYNTAX

    def test_too_long_command(self, client):
        resp = client.docmd("a" * 513)
        assert resp == S.S500_CMD_TOO_LONG

    def test_way_too_long_command(self, client):
        # Send a very large string to ensure it is broken
        # into several packets, which hits the inner
        # LimitOverrunError code path in _handle_client.
        client.send("a" * 1_000_000)
        response = client.docmd("a" * 1001)
        assert response == S.S500_CMD_TOO_LONG
        response = client.docmd("NOOP")
        assert response == S.S250_OK

    def test_unknown_command(self, client):
        resp = client.docmd("FOOBAR")
        assert resp == S.S500_CMD_UNRECOG(b"FOOBAR")


class TestSMTPNonDecoding(_CommonMethods):
    @controller_data(decode_data=False)
    def test_mail_invalid_body_param(self, plain_controller, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> BODY=FOOBAR")
        assert resp == S.S501_MAIL_BODY


@pytest.mark.usefixtures("decoding_authnotls_controller")
class TestSMTPAuth(_CommonMethods):
    def test_no_ehlo(self, client):
        resp = client.docmd("AUTH")
        assert resp == S.S503_EHLO_FIRST

    def test_helo(self, client):
        self._helo(client)
        resp = client.docmd("AUTH")
        assert resp == S.S500_AUTH_UNRECOG

    def test_not_enough_values(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH")
        assert resp == S.S501_TOO_FEW

    def test_already_authenticated(self, caplog, client):
        PW = "goodpasswd"
        self._ehlo(client)
        resp = client.docmd(
            "AUTH PLAIN " + b64encode(b"\0goodlogin\0" + PW.encode("ascii")).decode()
        )
        assert resp == S.S235_AUTH_SUCCESS
        resp = client.docmd("AUTH")
        assert resp == S.S503_ALREADY_AUTH
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        assert_nopassleak(PW, caplog.record_tuples)

    def test_auth_individually(self, caplog, client):
        """AUTH state of different clients must be independent"""
        PW = "goodpasswd"
        client1 = client
        with SMTPClient(*Global.SrvAddr) as client2:
            for c in client1, client2:
                c.ehlo("example.com")
                resp = c.login("goodlogin", PW)
                assert resp == S.S235_AUTH_SUCCESS
        assert_nopassleak(PW, caplog.record_tuples)

    def test_rset_maintain_authenticated(self, caplog, client):
        """RSET resets only Envelope not Session"""
        PW = "goodpasswd"
        self._ehlo(client, "example.com")
        resp = client.login("goodlogin", PW)
        assert resp == S.S235_AUTH_SUCCESS
        resp = client.mail("alice@example.com")
        assert resp == S.S250_OK
        resp = client.rset()
        assert resp == S.S250_OK
        resp = client.docmd("AUTH PLAIN")
        assert resp == S.S503_ALREADY_AUTH
        assert_nopassleak(PW, caplog.record_tuples)

    @handler_data(class_=PeekerHandler)
    def test_auth_loginteract_warning(self, client):
        client.ehlo("example.com")
        resp = client.docmd("AUTH WITH_UNDERSCORE")
        assert resp == (334, b"challenge")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter(action="default", category=UserWarning)
            assert client.docmd(B64EQUALS) == S.S235_AUTH_SUCCESS
        assert len(w) > 0
        assert str(w[0].message) == "AUTH interaction logging is enabled!"
        assert str(w[1].message) == "Sensitive information might be leaked!"


# noinspection TimingAttack,HardcodedPassword
@pytest.mark.usefixtures("auth_peeker_controller")
class TestAuthMechanisms(_CommonMethods):
    @pytest.fixture
    def do_auth_plain1(
        self, client
    ) -> Callable[[str], Tuple[int, bytes]]:
        self._ehlo(client)

        def do(param: str) -> Tuple[int, bytes]:
            return client.docmd("AUTH PLAIN " + param)

        do.client = client
        return do

    @pytest.fixture
    def do_auth_login3(
        self, client
    ) -> Callable[[str], Tuple[int, bytes]]:
        self._ehlo(client)
        resp = client.docmd("AUTH LOGIN")
        assert resp == S.S334_AUTH_USERNAME

        def do(param: str) -> Tuple[int, bytes]:
            return client.docmd(param)

        do.client = client
        return do

    def test_ehlo(self, client):
        code, mesg = client.ehlo("example.com")
        assert code == 250
        lines = mesg.splitlines()
        assert lines == [
            bytes(socket.getfqdn(), "utf-8"),
            b"SIZE 33554432",
            b"SMTPUTF8",
            (
                b"AUTH DENYFALSE DENYMISSING LOGIN NONE NULL PLAIN "
                b"WITH-DASH WITH-MULTI-DASH WITH_UNDERSCORE"
            ),
            b"HELP",
        ]

    @pytest.mark.parametrize("mechanism", ["GSSAPI", "DIGEST-MD5", "MD5", "CRAM-MD5"])
    def test_not_supported_mechanism(self, client, mechanism):
        self._ehlo(client)
        resp = client.docmd("AUTH " + mechanism)
        assert resp == S.S504_AUTH_UNRECOG

    def test_custom_mechanism(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH NULL")
        assert resp == S.S235_AUTH_SUCCESS

    def test_disabled_mechanism(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH DONT")
        assert resp == S.S504_AUTH_UNRECOG

    @pytest.mark.parametrize("init_resp", [True, False])
    @pytest.mark.parametrize("mechanism", ["login", "plain"])
    def test_byclient(
        self, caplog, auth_peeker_controller, client, mechanism, init_resp
    ):
        self._ehlo(client)
        PW = "goodpasswd"
        client.user = "goodlogin"
        client.password = PW
        auth_meth = getattr(client, "auth_" + mechanism)
        if (mechanism, init_resp) == ("login", False) and (
                sys.version_info < (3, 8, 9)
                or (3, 9, 0) < sys.version_info < (3, 9, 4)):
            # The bug with SMTP.auth_login was fixed in Python 3.10 and backported
            # to 3.9.4 and and 3.8.9.
            # See https://github.com/python/cpython/pull/24118 for the fixes.:
            with pytest.raises(SMTPAuthenticationError):
                client.auth(mechanism, auth_meth, initial_response_ok=init_resp)
            client.docmd("*")
            pytest.xfail(reason="smtplib.SMTP.auth_login is buggy (bpo-27820)")
        client.auth(mechanism, auth_meth, initial_response_ok=init_resp)
        peeker = auth_peeker_controller.handler
        assert isinstance(peeker, PeekerHandler)
        assert peeker.login == b"goodlogin"
        assert peeker.password == PW.encode("ascii")
        assert_nopassleak(PW, caplog.record_tuples)

    def test_plain1_bad_base64_encoding(self, do_auth_plain1):
        resp = do_auth_plain1("not-b64")
        assert resp == S.S501_AUTH_NOTB64

    def test_plain1_bad_base64_length(self, do_auth_plain1):
        resp = do_auth_plain1(b64encode(b"\0onlylogin").decode())
        assert resp == S.S501_AUTH_CANTSPLIT

    def test_plain1_too_many_values(self, do_auth_plain1):
        resp = do_auth_plain1("NONE NONE")
        assert resp == S.S501_TOO_MANY

    def test_plain1_bad_username(self, do_auth_plain1):
        resp = do_auth_plain1(b64encode(b"\0badlogin\0goodpasswd").decode())
        assert resp == S.S535_AUTH_INVALID

    def test_plain1_bad_password(self, do_auth_plain1):
        resp = do_auth_plain1(b64encode(b"\0goodlogin\0badpasswd").decode())
        assert resp == S.S535_AUTH_INVALID

    def test_plain1_empty(self, do_auth_plain1):
        resp = do_auth_plain1(B64EQUALS)
        assert resp == S.S501_AUTH_CANTSPLIT

    def test_plain1_good_credentials(
        self, caplog, auth_peeker_controller, do_auth_plain1
    ):
        PW = "goodpasswd"
        PWb = PW.encode("ascii")
        resp = do_auth_plain1(b64encode(b"\0goodlogin\0" + PWb).decode())
        assert resp == S.S235_AUTH_SUCCESS
        peeker = auth_peeker_controller.handler
        assert isinstance(peeker, PeekerHandler)
        assert peeker.login == b"goodlogin"
        assert peeker.password == PWb
        # noinspection PyUnresolvedReferences
        resp = do_auth_plain1.client.mail("alice@example.com")
        assert resp == S.S250_OK
        assert_nopassleak(PW, caplog.record_tuples)

    def test_plain1_goodcreds_sanitized_log(self, caplog, client):
        caplog.set_level("DEBUG")
        client.ehlo("example.com")
        PW = "goodpasswd"
        PWb = PW.encode("ascii")
        code, response = client.docmd(
            "AUTH PLAIN " + b64encode(b"\0goodlogin\0" + PWb).decode()
        )
        interestings = [tup for tup in caplog.record_tuples if "AUTH PLAIN" in tup[-1]]
        assert len(interestings) == 2
        assert interestings[0][1] == logging.DEBUG
        assert interestings[0][2].endswith("b'AUTH PLAIN ********\\r\\n'")
        assert interestings[1][1] == logging.INFO
        assert interestings[1][2].endswith("b'AUTH PLAIN ********'")
        assert_nopassleak(PW, caplog.record_tuples)

    @pytest.fixture
    def client_auth_plain2(self, client) -> SMTPClient:
        self._ehlo(client)
        resp = client.docmd("AUTH PLAIN")
        assert resp == S.S334_AUTH_EMPTYPROMPT
        return client

    def test_plain2_good_credentials(
        self, caplog, auth_peeker_controller, client_auth_plain2
    ):
        PW = "goodpasswd"
        PWb = PW.encode("ascii")
        resp = client_auth_plain2.docmd(b64encode(b"\0goodlogin\0" + PWb).decode())
        assert resp == S.S235_AUTH_SUCCESS
        peeker = auth_peeker_controller.handler
        assert isinstance(peeker, PeekerHandler)
        assert peeker.login == b"goodlogin"
        assert peeker.password == b"goodpasswd"
        resp = client_auth_plain2.mail("alice@example.com")
        assert resp == S.S250_OK
        assert_nopassleak(PW, caplog.record_tuples)

    def test_plain2_bad_credentials(self, client_auth_plain2):
        resp = client_auth_plain2.docmd(b64encode(b"\0badlogin\0badpasswd").decode())
        assert resp == S.S535_AUTH_INVALID

    def test_plain2_no_credentials(self, client_auth_plain2):
        resp = client_auth_plain2.docmd(B64EQUALS)
        assert resp == S.S501_AUTH_CANTSPLIT

    def test_plain2_abort(self, client_auth_plain2):
        resp = client_auth_plain2.docmd("*")
        assert resp == S.S501_AUTH_ABORTED

    def test_plain2_bad_base64_encoding(self, client_auth_plain2):
        resp = client_auth_plain2.docmd("ab@%")
        assert resp == S.S501_AUTH_NOTB64

    def test_login2_bad_base64(self, auth_peeker_controller, client):
        self._ehlo(client)
        resp = client.docmd("AUTH LOGIN ab@%")
        assert resp == S.S501_AUTH_NOTB64

    def test_login2_good_credentials(self, caplog, auth_peeker_controller, client):
        self._ehlo(client)
        PW = "goodpasswd"
        PWb = PW.encode("ascii")
        line = "AUTH LOGIN " + b64encode(b"goodlogin").decode()
        resp = client.docmd(line)
        assert resp == S.S334_AUTH_PASSWORD
        assert resp == S.S334_AUTH_PASSWORD
        resp = client.docmd(b64encode(PWb).decode())
        assert resp == S.S235_AUTH_SUCCESS
        peeker = auth_peeker_controller.handler
        assert isinstance(peeker, PeekerHandler)
        assert peeker.login == b"goodlogin"
        assert peeker.password == PWb
        resp = client.mail("alice@example.com")
        assert resp == S.S250_OK
        assert_nopassleak(PW, caplog.record_tuples)

    def test_login3_good_credentials(
        self, caplog, auth_peeker_controller, do_auth_login3
    ):
        PW = "goodpasswd"
        PWb = PW.encode("ascii")
        resp = do_auth_login3(b64encode(b"goodlogin").decode())
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login3(b64encode(PWb).decode())
        assert resp == S.S235_AUTH_SUCCESS
        peeker = auth_peeker_controller.handler
        assert isinstance(peeker, PeekerHandler)
        assert peeker.login == b"goodlogin"
        assert peeker.password == PWb
        # noinspection PyUnresolvedReferences
        resp = do_auth_login3.client.mail("alice@example.com")
        assert resp == S.S250_OK
        assert_nopassleak(PW, caplog.record_tuples)

    def test_login3_bad_base64(self, do_auth_login3):
        resp = do_auth_login3("not-b64")
        assert resp == S.S501_AUTH_NOTB64

    def test_login3_bad_username(self, do_auth_login3):
        resp = do_auth_login3(b64encode(b"badlogin").decode())
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login3(b64encode(b"goodpasswd").decode())
        assert resp == S.S535_AUTH_INVALID

    def test_login3_bad_password(self, do_auth_login3):
        resp = do_auth_login3(b64encode(b"goodlogin").decode())
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login3(b64encode(b"badpasswd").decode())
        assert resp == S.S535_AUTH_INVALID

    def test_login3_empty_credentials(self, do_auth_login3):
        resp = do_auth_login3(B64EQUALS)
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login3(B64EQUALS)
        assert resp == S.S535_AUTH_INVALID

    def test_login3_abort_username(self, do_auth_login3):
        resp = do_auth_login3("*")
        assert resp == S.S501_AUTH_ABORTED

    def test_login3_abort_password(self, do_auth_login3):
        resp = do_auth_login3(B64EQUALS)
        assert resp == S.S334_AUTH_PASSWORD
        resp = do_auth_login3("*")
        assert resp == S.S501_AUTH_ABORTED

    def test_DENYFALSE(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH DENYFALSE")
        assert resp == S.S535_AUTH_INVALID

    def test_DENYMISSING(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH DENYMISSING")
        assert resp == S.S535_AUTH_INVALID

    def test_NONE(self, client):
        self._ehlo(client)
        resp = client.docmd("AUTH NONE")
        assert resp == S.S235_AUTH_SUCCESS


# noinspection HardcodedPassword
class TestAuthenticator(_CommonMethods):
    def test_success(self, caplog, authenticator_peeker_controller, client):
        PW = "goodpasswd"
        client.user = "gooduser"
        client.password = PW
        self._ehlo(client)
        client.auth("plain", client.auth_plain)
        auth_peeker = authenticator_peeker_controller.handler
        assert isinstance(auth_peeker, PeekerHandler)
        assert auth_peeker.sess.peer[0] in {"::1", "127.0.0.1", "localhost"}
        assert auth_peeker.sess.peer[1] > 0
        assert auth_peeker.sess.authenticated
        assert auth_peeker.sess.auth_data == (b"gooduser", PW.encode("ascii"))
        assert auth_peeker.login_data == (b"gooduser", PW.encode("ascii"))
        assert_nopassleak(PW, caplog.record_tuples)

    def test_fail_withmesg(self, caplog, authenticator_peeker_controller, client):
        PW = "anypass"
        client.user = "failme_with454"
        client.password = PW
        self._ehlo(client)
        with pytest.raises(SMTPAuthenticationError) as cm:
            client.auth("plain", client.auth_plain)
        assert cm.value.args == (454, b"4.7.0 Temporary authentication failure")
        auth_peeker = authenticator_peeker_controller.handler
        assert isinstance(auth_peeker, PeekerHandler)
        assert auth_peeker.sess.peer[0] in {"::1", "127.0.0.1", "localhost"}
        assert auth_peeker.sess.peer[1] > 0
        assert auth_peeker.sess.login_data is None
        assert auth_peeker.login_data == (b"failme_with454", PW.encode("ascii"))
        assert_nopassleak(PW, caplog.record_tuples)


@pytest.mark.filterwarnings("ignore:Requiring AUTH while not requiring TLS:UserWarning")
@pytest.mark.usefixtures("plain_controller")
@controller_data(
    decode_data=True,
    enable_SMTPUTF8=True,
    auth_require_tls=False,
    auth_callback=auth_callback,
    auth_required=True,
)
class TestRequiredAuthentication(_CommonMethods):
    def _login(self, client: SMTPClient):
        self._ehlo(client)
        resp = client.login("goodlogin", "goodpasswd")
        assert resp == S.S235_AUTH_SUCCESS

    def test_help_unauthenticated(self, client):
        resp = client.docmd("HELP")
        assert resp == S.S530_AUTH_REQUIRED

    def test_help_authenticated(self, client):
        self._login(client)
        resp = client.docmd("HELP")
        assert resp == S.S250_SUPPCMD_NOTLS

    def test_vrfy_unauthenticated(self, client):
        resp = client.docmd("VRFY <anne@example.com>")
        assert resp == S.S530_AUTH_REQUIRED

    def test_mail_unauthenticated(self, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S530_AUTH_REQUIRED

    def test_rcpt_unauthenticated(self, client):
        self._ehlo(client)
        resp = client.docmd("RCPT TO: <anne@example.com>")
        assert resp == S.S530_AUTH_REQUIRED

    def test_rcpt_nomail_authenticated(self, client):
        self._login(client)
        resp = client.docmd("RCPT TO: <anne@example.com>")
        assert resp == S.S503_MAIL_NEEDED

    def test_data_unauthenticated(self, client):
        self._ehlo(client)
        resp = client.docmd("DATA")
        assert resp == S.S530_AUTH_REQUIRED

    def test_data_authenticated(self, client):
        self._ehlo(client, "example.com")
        client.login("goodlogin", "goodpassword")
        resp = client.docmd("DATA")
        assert resp != S.S530_AUTH_REQUIRED

    def test_vrfy_authenticated(self, client):
        self._login(client)
        resp = client.docmd("VRFY <anne@example.com>")
        assert resp == S.S252_CANNOT_VRFY

    def test_mail_authenticated(self, client):
        self._login(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp, S.S250_OK

    def test_data_norcpt_authenticated(self, client):
        self._login(client)
        resp = client.docmd("DATA")
        assert resp == S.S503_RCPT_NEEDED


class TestResetCommands:
    """Test that sender and recipients are reset on RSET, HELO, and EHLO.

    The tests below issue each command twice with different addresses and
    verify that mail_from and rcpt_tos have been replacecd.
    """

    expected_envelope_data = [
        # Pre-RSET/HELO/EHLO envelope data.
        dict(
            mail_from="anne@example.com",
            rcpt_tos=["bart@example.com", "cate@example.com"],
        ),
        dict(
            mail_from="dave@example.com",
            rcpt_tos=["elle@example.com", "fred@example.com"],
        ),
    ]

    def _send_envelope_data(
        self,
        client: SMTPClient,
        mail_from: str,
        rcpt_tos: List[str],
    ):
        client.mail(mail_from)
        for rcpt in rcpt_tos:
            client.rcpt(rcpt)

    @handler_data(class_=StoreEnvelopeOnVRFYHandler)
    def test_helo(self, decoding_authnotls_controller, client):
        handler = decoding_authnotls_controller.handler
        assert isinstance(handler, StoreEnvelopeOnVRFYHandler)
        # Each time through the loop, the HELO will reset the envelope.
        for data in self.expected_envelope_data:
            client.helo("example.com")
            # Save the envelope in the handler.
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from is None
            assert len(handler.envelope.rcpt_tos) == 0
            self._send_envelope_data(client, **data)
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from == data["mail_from"]
            assert handler.envelope.rcpt_tos == data["rcpt_tos"]

    @handler_data(class_=StoreEnvelopeOnVRFYHandler)
    def test_ehlo(self, decoding_authnotls_controller, client):
        handler = decoding_authnotls_controller.handler
        assert isinstance(handler, StoreEnvelopeOnVRFYHandler)
        # Each time through the loop, the EHLO will reset the envelope.
        for data in self.expected_envelope_data:
            client.ehlo("example.com")
            # Save the envelope in the handler.
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from is None
            assert len(handler.envelope.rcpt_tos) == 0
            self._send_envelope_data(client, **data)
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from == data["mail_from"]
            assert handler.envelope.rcpt_tos == data["rcpt_tos"]

    @handler_data(class_=StoreEnvelopeOnVRFYHandler)
    def test_rset(self, decoding_authnotls_controller, client):
        handler = decoding_authnotls_controller.handler
        assert isinstance(handler, StoreEnvelopeOnVRFYHandler)
        client.helo("example.com")
        # Each time through the loop, the RSET will reset the envelope.
        for data in self.expected_envelope_data:
            self._send_envelope_data(client, **data)
            # Save the envelope in the handler.
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from == data["mail_from"]
            assert handler.envelope.rcpt_tos == data["rcpt_tos"]
            # Reset the envelope explicitly.
            client.rset()
            client.vrfy("zuzu@example.com")
            assert handler.envelope.mail_from is None
            assert len(handler.envelope.rcpt_tos) == 0


class TestSMTPWithController(_CommonMethods):
    @controller_data(data_size_limit=9999)
    def test_mail_with_size_too_large(self, plain_controller, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> SIZE=10000")
        assert resp == S.S552_EXCEED_SIZE

    @handler_data(class_=ReceivingHandler)
    def test_mail_with_compatible_smtputf8(self, plain_controller, client):
        receiving_handler = plain_controller.handler
        assert isinstance(receiving_handler, ReceivingHandler)
        sender = "anne\xCB@example.com"
        recipient = "bart\xCB@example.com"
        self._ehlo(client)
        client.send(f"MAIL FROM: <{sender}> SMTPUTF8\r\n".encode("utf-8"))
        assert client.getreply() == S.S250_OK
        client.send(f"RCPT TO: <{recipient}>\r\n".encode("utf-8"))
        assert client.getreply() == S.S250_OK
        resp = client.data("")
        assert resp == S.S250_OK
        assert receiving_handler.box[0].mail_from == sender
        assert receiving_handler.box[0].rcpt_tos == [recipient]

    def test_mail_with_unrequited_smtputf8(self, plain_controller, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK

    def test_mail_with_incompatible_smtputf8(self, plain_controller, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> SMTPUTF8=YES")
        assert resp == S.S501_SMTPUTF8_NOARG

    def test_mail_invalid_body(self, plain_controller, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> BODY 9BIT")
        assert resp == S.S501_MAIL_BODY

    @controller_data(data_size_limit=None)
    def test_esmtp_no_size_limit(self, plain_controller, client):
        code, mesg = client.ehlo("example.com")
        for ln in mesg.splitlines():
            assert not ln.startswith(b"SIZE")

    @handler_data(class_=ErroringHandler)
    def test_process_message_error(self, error_controller, client):
        self._ehlo(client)
        with pytest.raises(SMTPDataError) as excinfo:
            client.sendmail(
                "anne@example.com",
                ["bart@example.com"],
                dedent(
                    """\
                    From: anne@example.com
                    To: bart@example.com
                    Subjebgct: A test

                    Testing
                """
                ),
            )
        assert excinfo.value.args == (499, b"Could not accept the message")

    @controller_data(data_size_limit=100)
    def test_too_long_message_body(self, plain_controller, client):
        self._helo(client)
        mail = "\r\n".join(["z" * 20] * 10)
        with pytest.raises(SMTPResponseException) as excinfo:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert excinfo.value.args == S.S552_DATA_TOO_MUCH

    @handler_data(class_=ReceivingHandler)
    def test_dots_escaped(self, decoding_authnotls_controller, client):
        receiving_handler = decoding_authnotls_controller.handler
        assert isinstance(receiving_handler, ReceivingHandler)
        self._helo(client)
        mail = CRLF.join(["Test", ".", "mail"])
        client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert len(receiving_handler.box) == 1
        assert receiving_handler.box[0].content == mail + CRLF

    @handler_data(class_=ErroringHandler)
    def test_unexpected_errors(self, error_controller, client):
        handler = error_controller.handler
        resp = client.helo("example.com")
        assert resp == (500, b"ErroringHandler handling error")
        exception_type = ErrorSMTP.exception_type
        assert isinstance(handler.error, exception_type)

    def test_unexpected_errors_unhandled(self, error_controller, client):
        resp = client.helo("example.com")
        exception_type = ErrorSMTP.exception_type
        exception_nameb = exception_type.__name__.encode("ascii")
        assert resp == (500, b"Error: (" + exception_nameb + b") test")

    @handler_data(class_=ErroringHandler)
    def test_unexpected_errors_custom_response(self, error_controller, client):
        erroring_handler = error_controller.handler
        erroring_handler.custom_response = True
        resp = client.helo("example.com")
        exception_type = ErrorSMTP.exception_type
        assert isinstance(erroring_handler.error, exception_type)
        exception_nameb = exception_type.__name__.encode("ascii")
        assert resp == (451, b"Temporary error: (" + exception_nameb + b") test")

    @handler_data(class_=ErroringErrorHandler)
    def test_exception_handler_exception(self, error_controller, client):
        handler = error_controller.handler
        resp = client.helo("example.com")
        assert resp == (500, b"Error: (ValueError) ErroringErrorHandler test")
        exception_type = ErrorSMTP.exception_type
        assert isinstance(handler.error, exception_type)

    @handler_data(class_=UndescribableErrorHandler)
    def test_exception_handler_undescribable(self, error_controller, client):
        handler = error_controller.handler
        resp = client.helo("example.com")
        assert resp == (500, b"Error: Cannot describe error")
        exception_type = ErrorSMTP.exception_type
        assert isinstance(handler.error, exception_type)

    @handler_data(class_=ErroringHandlerConnectionLost)
    def test_exception_handler_multiple_connections_lost(
        self, error_controller, client
    ):
        client1 = client
        code, mesg = client1.ehlo("example.com")
        assert code == 250
        with SMTPClient(*Global.SrvAddr) as client2:
            code, mesg = client2.ehlo("example.com")
            assert code == 250
            with pytest.raises(SMTPServerDisconnected) as exc:
                mail = CRLF.join(["Test", ".", "mail"])
                client2.sendmail("anne@example.com", ["bart@example.com"], mail)
            assert isinstance(exc.value, SMTPServerDisconnected)
            assert error_controller.handler.error is None
            # At this point connection should be down
            with pytest.raises(SMTPServerDisconnected) as exc:
                client2.mail("alice@example.com")
            assert str(exc.value) == "please run connect() first"
        # client1 shouldn't be affected.
        resp = client1.mail("alice@example.com")
        assert resp == S.S250_OK

    @handler_data(class_=ReceivingHandler)
    def test_bad_encodings(self, decoding_authnotls_controller, client):
        handler: ReceivingHandler = decoding_authnotls_controller.handler
        self._helo(client)
        mail_from = b"anne\xFF@example.com"
        mail_to = b"bart\xFF@example.com"
        self._ehlo(client, "test")
        client.send(b"MAIL FROM:" + mail_from + b"\r\n")
        assert client.getreply() == S.S250_OK
        client.send(b"RCPT TO:" + mail_to + b"\r\n")
        assert client.getreply() == S.S250_OK
        client.data("Test mail")
        assert len(handler.box) == 1
        envelope = handler.box[0]
        mail_from2 = envelope.mail_from.encode("utf-8", errors="surrogateescape")
        assert mail_from2 == mail_from
        mail_to2 = envelope.rcpt_tos[0].encode("utf-8", errors="surrogateescape")
        assert mail_to2 == mail_to

    @controller_data(decode_data=False)
    def test_data_line_too_long(self, plain_controller, client):
        self._helo(client)
        client.helo("example.com")
        mail = b"\r\n".join([b"a" * 5555] * 3)
        with pytest.raises(SMTPDataError) as exc:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert exc.value.args == S.S500_DATALINE_TOO_LONG

    @controller_data(data_size_limit=10000)
    def test_long_line_double_count(self, plain_controller, client):
        # With a read limit of 1001 bytes in aiosmtp.SMTP, asyncio.StreamReader
        # returns too-long lines of length up to 2002 bytes.
        # This test ensures that bytes in partial lines are only counted once.
        # If the implementation has a double-counting bug, then a message of
        # 9998 bytes + CRLF will raise SMTPResponseException.
        client.helo("example.com")
        mail = "z" * 9998
        with pytest.raises(SMTPDataError) as exc:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert exc.value.args == S.S500_DATALINE_TOO_LONG

    def test_long_line_leak(self, mocker: MockFixture, plain_controller, client):
        # Simulates situation where readuntil() does not raise LimitOverrunError,
        # but somehow the line_fragments when join()ed resulted in a too-long line

        # Hijack EMPTY_BARR.join() to return a bytes object that's definitely too long
        mock_ebarr = mocker.patch("aiosmtpd.smtp.EMPTY_BARR")
        mock_ebarr.join.return_value = b"a" * 1010

        client.helo("example.com")
        mail = "z" * 72  # Make sure this is small and definitely within limits
        with pytest.raises(SMTPDataError) as exc:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert exc.value.args == S.S500_DATALINE_TOO_LONG
        # self.assertEqual(cm.exception.smtp_code, 500)
        # self.assertEqual(cm.exception.smtp_error,
        #                  b'Line too long (see RFC5321 4.5.3.1.6)')

    @controller_data(data_size_limit=20)
    def test_too_long_body_delay_error(self, plain_controller):
        with socket.socket() as sock:
            sock.connect((plain_controller.hostname, plain_controller.port))
            rslt = send_recv(sock, b"EHLO example.com")
            assert rslt.startswith(b"220")
            rslt = send_recv(sock, b"MAIL FROM: <anne@example.com>")
            assert rslt.startswith(b"250")
            rslt = send_recv(sock, b"RCPT TO: <bruce@example.com>")
            assert rslt.startswith(b"250")
            rslt = send_recv(sock, b"DATA")
            assert rslt.startswith(b"354")
            rslt = send_recv(sock, b"a" * (20 + 3))
            # Must NOT receive status code here even if data is too much
            assert rslt == b""
            rslt = send_recv(sock, b"\r\n.")
            # *NOW* we must receive status code
            assert rslt == b"552 Error: Too much mail data\r\n"

    @controller_data(data_size_limit=700)
    def test_too_long_body_then_too_long_lines(self, plain_controller, client):
        # If "too much mail" state was reached before "too long line" gets received,
        # SMTP should respond with '552' instead of '500'
        client.helo("example.com")
        mail = "\r\n".join(["z" * 76] * 10 + ["a" * 1100] * 2)
        with pytest.raises(SMTPResponseException) as exc:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert exc.value.args == S.S552_DATA_TOO_MUCH

    def test_too_long_line_delay_error(self, plain_controller):
        with socket.socket() as sock:
            sock.connect((plain_controller.hostname, plain_controller.port))
            rslt = send_recv(sock, b"EHLO example.com")
            assert rslt.startswith(b"220")
            rslt = send_recv(sock, b"MAIL FROM: <anne@example.com>")
            assert rslt.startswith(b"250")
            rslt = send_recv(sock, b"RCPT TO: <bruce@example.com>")
            assert rslt.startswith(b"250")
            rslt = send_recv(sock, b"DATA")
            assert rslt.startswith(b"354")
            rslt = send_recv(sock, b"a" * (Server.line_length_limit + 3))
            # Must NOT receive status code here even if data is too much
            assert rslt == b""
            rslt = send_recv(sock, b"\r\n.")
            # *NOW* we must receive status code
            assert rslt == S.S500_DATALINE_TOO_LONG.to_bytes(crlf=True)

    @controller_data(data_size_limit=2000)
    def test_too_long_lines_then_too_long_body(self, plain_controller, client):
        # If "too long line" state was reached before "too much data" happens,
        # SMTP should respond with '500' instead of '552'
        client.helo("example.com")
        mail = "\r\n".join(["z" * (2000 - 1)] * 2)
        with pytest.raises(SMTPResponseException) as exc:
            client.sendmail("anne@example.com", ["bart@example.com"], mail)
        assert exc.value.args == S.S500_DATALINE_TOO_LONG


class TestCustomization(_CommonMethods):
    @controller_data(class_=CustomHostnameController)
    def test_custom_hostname(self, plain_controller, client):
        code, mesg = client.helo("example.com")
        assert code == 250
        assert mesg == CustomHostnameController.custom_name.encode("ascii")

    def test_default_greeting(self, plain_controller, client):
        controller = plain_controller
        code, mesg = client.connect(controller.hostname, controller.port)
        assert code == 220
        # The hostname prefix is unpredictable
        assert mesg.endswith(bytes(GREETING, "utf-8"))

    @controller_data(class_=CustomIdentController)
    def test_custom_greeting(self, plain_controller, client):
        controller = plain_controller
        code, mesg = client.connect(controller.hostname, controller.port)
        assert code == 220
        # The hostname prefix is unpredictable.
        assert mesg.endswith(CustomIdentController.ident)

    @controller_data(decode_data=False)
    def test_mail_invalid_body_param(self, plain_controller, client):
        client.ehlo("example.com")
        resp = client.docmd("MAIL FROM: <anne@example.com> BODY=FOOBAR")
        assert resp == S.S501_MAIL_BODY

    def test_limitlocalpart(self, plain_controller, client):
        plain_controller.smtpd.local_part_limit = 64
        client.ehlo("example.com")
        locpart = "a" * 64
        resp = client.docmd(f"MAIL FROM: {locpart}@example.com")
        assert resp == S.S250_OK
        locpart = "b" * 65
        resp = client.docmd(f"RCPT TO: {locpart}@example.com")
        assert resp == S.S553_MALFORMED


class TestClientCrash(_CommonMethods):
    def test_connection_reset_during_DATA(
        self, mocker: MockFixture, plain_controller, client
    ):
        # Trigger factory() to produce the smtpd server
        self._helo(client)
        smtpd: Server = plain_controller.smtpd
        spy = mocker.spy(smtpd._writer, "close")
        # Do some stuff
        client.docmd("MAIL FROM: <anne@example.com>")
        client.docmd("RCPT TO: <bart@example.com>")
        # Entering portion of code where hang is possible (upon assertion fail), so
        # we must wrap with "try..finally". See pytest-dev/pytest#7989
        try:
            resp = client.docmd("DATA")
            assert resp == S.S354_DATA_ENDWITH
            # Start sending the DATA but reset the connection before that
            # completes, i.e. before the .\r\n
            client.send(b"From: <anne@example.com>")
            reset_connection(client)
            with pytest.raises(SMTPServerDisconnected):
                client.noop()
            catchup_delay()
            # Apparently within that delay, ._writer.close() invoked several times
            # That is okay; we just want to ensure that it's invoked at least once.
            assert spy.call_count > 0
        finally:
            plain_controller.stop()

    def test_connection_reset_during_command(
        self, mocker: MockFixture, plain_controller, client
    ):
        # Trigger factory() to produce the smtpd server
        self._helo(client)
        smtpd: Server = plain_controller.smtpd
        spy = mocker.spy(smtpd._writer, "close")
        # Start sending a command but reset the connection before that
        # completes, i.e. before the \r\n
        client.send("MAIL FROM: <anne")
        reset_connection(client)
        with pytest.raises(SMTPServerDisconnected):
            client.noop()
        catchup_delay()
        # Should be called at least once. (In practice, almost certainly just once.)
        assert spy.call_count > 0

    def test_connection_reset_in_long_command(self, plain_controller, client):
        client.send("F" + 5555 * "O")  # without CRLF
        reset_connection(client)
        catchup_delay()
        # At this point, smtpd's StreamWriter hasn't been initialized. Prolly since
        # the call is self._reader.readline() and we abort before CRLF is sent.
        # That is why we don't need to 'spy' on writer.close()
        writer = plain_controller.smtpd._writer
        # transport.is_closing() == True if transport is in the process of closing,
        # and still == True if transport is closed.
        assert writer.transport.is_closing()

    def test_close_in_command(self, plain_controller, client):
        # Don't include the CRLF.
        client.send("FOO")
        client.close()
        catchup_delay()
        # At this point, smtpd's StreamWriter hasn't been initialized. Prolly since
        # the call is self._reader.readline() and we abort before CRLF is sent.
        # That is why we don't need to 'spy' on writer.close()
        writer = plain_controller.smtpd._writer
        # transport.is_closing() == True if transport is in the process of closing,
        # and still == True if transport is closed.
        assert writer.transport.is_closing()

    def test_close_in_command_2(self, mocker: MockFixture, plain_controller, client):
        self._helo(client)
        catchup_delay()
        smtpd: Server = plain_controller.smtpd
        writer = smtpd._writer
        spy = mocker.spy(writer, "close")
        # Don't include the CRLF.
        client.send("FOO")
        client.close()
        catchup_delay()
        # Check that smtpd._writer.close() invoked at least once
        assert spy.call_count > 0
        # transport.is_closing() == True if transport is in the process of closing,
        # and still == True if transport is closed.
        assert writer.transport.is_closing()

    def test_close_in_long_command(self, plain_controller, client):
        client.send("F" + 5555 * "O")  # without CRLF
        client.close()
        catchup_delay()
        # At this point, smtpd's StreamWriter hasn't been initialized. Prolly since
        # the call is self._reader.readline() and we abort before CRLF is sent.
        # That is why we don't need to 'spy' on writer.close()
        writer = plain_controller.smtpd._writer
        # transport.is_closing() == True if transport is in the process of closing,
        # and still == True if transport is closed.
        assert writer.transport.is_closing()

    def test_close_in_data(self, mocker: MockFixture, plain_controller, client):
        self._helo(client)
        smtpd: Server = plain_controller.smtpd
        writer = smtpd._writer
        spy = mocker.spy(writer, "close")
        resp = client.docmd("MAIL FROM: <anne@example.com>")
        assert resp == S.S250_OK
        resp = client.docmd("RCPT TO: <bart@example.com>")
        assert resp == S.S250_OK
        # Entering portion of code where hang is possible (upon assertion fail), so
        # we must wrap with "try..finally". See pytest-dev/pytest#7989
        try:
            resp = client.docmd("DATA")
            assert resp == S.S354_DATA_ENDWITH
            # Don't include the CRLF.
            client.send("FOO")
            client.close()
            catchup_delay()
            # Check that smtpd._writer.close() invoked at least once
            assert spy.call_count > 0
            # transport.is_closing() == True if transport is in the process of closing,
            # and still == True if transport is closed.
            assert writer.transport.is_closing()
        finally:
            plain_controller.stop()

    def test_sockclose_after_helo(self, mocker: MockFixture, plain_controller, client):
        client.send("HELO example.com\r\n")
        catchup_delay()
        smtpd: Server = plain_controller.smtpd
        writer = smtpd._writer
        spy = mocker.spy(writer, "close")

        client.sock.shutdown(socket.SHUT_WR)
        catchup_delay()
        # Check that smtpd._writer.close() invoked at least once
        assert spy.call_count > 0
        # transport.is_closing() == True if transport is in the process of closing,
        # and still == True if transport is closed.
        assert writer.transport.is_closing()


@pytest.mark.usefixtures("plain_controller")
@controller_data(enable_SMTPUTF8=False, decode_data=True)
class TestStrictASCII(_CommonMethods):
    def test_ehlo(self, client):
        blines = self._ehlo(client)
        assert b"SMTPUTF8" not in blines

    def test_bad_encoded_param(self, client):
        self._ehlo(client)
        client.send(b"MAIL FROM: <anne\xFF@example.com>\r\n")
        assert client.getreply() == S.S500_STRICT_ASCII

    def test_mail_param(self, client):
        self._ehlo(client)
        resp = client.docmd("MAIL FROM: <anne@example.com> SMTPUTF8")
        assert resp == S.S501_SMTPUTF8_DISABLED

    def test_data(self, client):
        self._ehlo(client)
        with pytest.raises(SMTPDataError) as excinfo:
            client.sendmail(
                "anne@example.com",
                ["bart@example.com"],
                b"From: anne@example.com\n"
                b"To: bart@example.com\n"
                b"Subject: A test\n"
                b"\n"
                b"Testing\xFF\n",
            )
        assert excinfo.value.args == S.S500_STRICT_ASCII


class TestSleepingHandler(_CommonMethods):
    # What is the point here?

    @controller_data(decode_data=False)
    @handler_data(class_=SleepingHeloHandler)
    def test_close_after_helo(self, plain_controller, client):
        #
        # What are we actually testing?
        #
        client.send("HELO example.com\r\n")
        client.sock.shutdown(socket.SHUT_WR)
        with pytest.raises(SMTPServerDisconnected):
            client.getreply()


class TestTimeout(_CommonMethods):
    @controller_data(class_=TimeoutController)
    def test_timeout(self, plain_controller, client):
        # This one is rapid, it must succeed
        self._ehlo(client)
        time.sleep(0.1 + TimeoutController.Delay)
        with pytest.raises(SMTPServerDisconnected):
            client.mail("anne@example.com")


class TestAuthArgs:
    def test_warn_authreqnotls(self, caplog):
        with pytest.warns(UserWarning) as record:
            _ = Server(Sink(), auth_required=True, auth_require_tls=False)
        for warning in record:
            if warning.message.args and (
                warning.message.args[0]
                == "Requiring AUTH while not requiring TLS can lead to "
                "security vulnerabilities!"
            ):
                break
            else:
                pytest.xfail("Did not raise expected warning")

        assert caplog.record_tuples[0] == (
            "mail.log",
            logging.WARNING,
            "auth_required == True but auth_require_tls == False",
        )

    def test_log_authmechanisms(self, caplog):
        caplog.set_level(logging.INFO)
        server = Server(Sink())
        auth_mechs = sorted(
            m.replace("auth_", "") + "(builtin)"
            for m in dir(server)
            if m.startswith("auth_")
        )
        assert (
            caplog.record_tuples[0][-1]
            == f"Available AUTH mechanisms: {' '.join(auth_mechs)}"
        )

    @pytest.mark.parametrize(
        "name",
        [
            "has space",
            "has.dot",
            "has/slash",
            "has\\backslash",
        ],
    )
    def test_authmechname_decorator_badname(self, name):
        expectre = r"Invalid AUTH mechanism name"
        with pytest.raises(ValueError, match=expectre):
            auth_mechanism(name)


class TestLimits(_CommonMethods):
    def _consume_budget(
        self, client: SMTPClient, nums: int, cmd: str, *args, ok_expected=None
    ):
        code, _ = client.ehlo("example.com")
        assert code == 250
        func = getattr(client, cmd)
        expected = ok_expected or S.S250_OK
        for _ in range(0, nums):
            assert func(*args) == expected
        assert func(*args) == S.S421_TOO_MANY(cmd.upper().encode())
        with pytest.raises(SMTPServerDisconnected):
            client.noop()

    def test_limit_wrong_type(self):
        with pytest.raises(TypeError) as exc:
            # noinspection PyTypeChecker
            _ = Server(Sink(), command_call_limit="invalid")
        assert exc.value.args[0] == "command_call_limit must be int or Dict[str, int]"

    def test_limit_wrong_value_type(self):
        with pytest.raises(TypeError) as exc:
            # noinspection PyTypeChecker
            _ = Server(Sink(), command_call_limit={"NOOP": "invalid"})
        assert exc.value.args[0] == "All command_call_limit values must be int"

    @controller_data(command_call_limit=15)
    def test_all_limit_15(self, plain_controller, client):
        self._consume_budget(client, 15, "noop")

    @controller_data(command_call_limit={"NOOP": 15, "EXPN": 5})
    def test_different_limits(self, plain_controller, client):
        srv_ip_port = plain_controller.hostname, plain_controller.port

        self._consume_budget(client, 15, "noop")

        client.connect(*srv_ip_port)
        self._consume_budget(
            client, 5, "expn", "alice@example.com", ok_expected=S.S502_EXPN_NOTIMPL
        )

        client.connect(*srv_ip_port)
        self._consume_budget(
            client,
            CALL_LIMIT_DEFAULT,
            "vrfy",
            "alice@example.com",
            ok_expected=S.S252_CANNOT_VRFY,
        )

    @controller_data(command_call_limit={"NOOP": 7, "EXPN": 5, "*": 25})
    def test_different_limits_custom_default(self, plain_controller, client):
        # Important: make sure default_max > CALL_LIMIT_DEFAULT
        # Others can be set small to cut down on testing time, but must be different
        assert plain_controller.smtpd._call_limit_default > CALL_LIMIT_DEFAULT
        srv_ip_port = plain_controller.hostname, plain_controller.port

        self._consume_budget(client, 7, "noop")

        client.connect(*srv_ip_port)
        self._consume_budget(
            client, 5, "expn", "alice@example.com", ok_expected=S.S502_EXPN_NOTIMPL
        )

        client.connect(*srv_ip_port)
        self._consume_budget(
            client,
            25,
            "vrfy",
            "alice@example.com",
            ok_expected=S.S252_CANNOT_VRFY,
        )

    @controller_data(command_call_limit=7)
    def test_limit_bogus(self, plain_controller, client):
        assert plain_controller.smtpd._call_limit_default > BOGUS_LIMIT
        code, mesg = client.ehlo("example.com")
        assert code == 250
        for i in range(0, BOGUS_LIMIT - 1):
            cmd = f"BOGUS{i}"
            assert client.docmd(cmd) == S.S500_CMD_UNRECOG(cmd.encode())
        assert client.docmd("LASTBOGUS") == S.S502_TOO_MANY_UNRECOG
        with pytest.raises(SMTPServerDisconnected):
            client.noop()


class TestSanitize:
    def test_loginpassword(self):
        lp = LoginPassword(b"user", b"pass")
        expect = "LoginPassword(login='user', password=...)"
        assert repr(lp) == expect
        assert str(lp) == expect

    def test_authresult(self):
        ar = AuthResult(success=True, auth_data="user:pass")
        expect = "AuthResult(success=True, handled=True, message=None, auth_data=...)"
        assert repr(ar) == expect
        assert str(ar) == expect
