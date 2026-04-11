# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
from email.message import Message as Em_Message
from io import StringIO
from mailbox import Maildir
from operator import itemgetter
from pathlib import Path
from smtplib import SMTPDataError, SMTPRecipientsRefused
from textwrap import dedent
from types import SimpleNamespace
from typing import AnyStr, Callable, Generator, Type, TypeVar, Union

import pytest

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage, Debugging, Mailbox, Proxy, Sink
from aiosmtpd.handlers import Message as AbstractMessageHandler
from aiosmtpd.smtp import SMTP as Server
from aiosmtpd.smtp import Session as ServerSession
from aiosmtpd.smtp import Envelope
from aiosmtpd.testing.statuscodes import SMTP_STATUS_CODES as S
from aiosmtpd.testing.statuscodes import StatusCode

from .conftest import Global, controller_data, handler_data

try:
    from typing_extensions import Protocol
except ModuleNotFoundError:
    from typing import Protocol


class HasFakeParser(Protocol):
    fparser: "FakeParser"
    exception: Type[Exception]


class KnowsUpstream(Protocol):
    upstream: Controller


T = TypeVar("T")


CRLF = "\r\n"


# region ##### Support Classes ###############################################


class FakeParser:
    """
    Emulates ArgumentParser.error() to catch the message
    """

    message: Union[str, bytes, None] = None

    def error(self, message: AnyStr):
        self.message = message
        raise SystemExit


class DataHandler:
    content: Union[str, bytes, None] = None
    original_content: bytes = None

    async def handle_DATA(
        self, server: Server, session: ServerSession, envelope: Envelope
    ) -> str:
        self.content = envelope.content
        self.original_content = envelope.original_content
        return S.S250_OK.to_str()


class MessageHandler(AbstractMessageHandler):
    def handle_message(self, message: Em_Message) -> None:
        pass


class AsyncMessageHandler(AsyncMessage):
    handled_message: Em_Message = None

    async def handle_message(self, message: Em_Message) -> None:
        self.handled_message = message


class HELOHandler:
    ReturnCode = StatusCode(250, b"pepoluan.was.here")

    async def handle_HELO(self, server, session, envelope, hostname):
        return self.ReturnCode.to_str()


class EHLOHandlerDeprecated:
    Domain = "alex.example.code"
    ReturnCode = StatusCode(250, Domain.encode("ascii"))

    async def handle_EHLO(self, server, session, envelope, hostname):
        return self.ReturnCode.to_str()


# The suffix "New" is kept so we can catch all refs to the old "EHLOHandler" class
class EHLOHandlerNew:
    Domain = "bruce.example.code"
    hostname = None
    orig_responses = []

    def __init__(self, *features):
        self.features = features or tuple()

    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        self.hostname = hostname
        self.orig_responses.clear()
        self.orig_responses.extend(responses)
        my_resp = [responses[0]]
        my_resp.extend(f"250-{f}" for f in self.features)
        my_resp.append("250 HELP")
        return my_resp


class EHLOHandlerIncompatibleShort:
    async def handle_EHLO(self, server, session, envelope):
        return


class EHLOHandlerIncompatibleLong:
    async def handle_EHLO(self, server, session, envelope, hostname, responses, xtra):
        return


class MAILHandler:
    ReplacementOptions = ["WAS_HANDLED"]
    ReturnCode = StatusCode(250, b"Yeah, sure")

    async def handle_MAIL(self, server, session, envelope, address, options):
        envelope.mail_options = self.ReplacementOptions
        return self.ReturnCode.to_str()


class RCPTHandler:
    RejectCode = StatusCode(550, b"Rejected")

    async def handle_RCPT(self, server, session, envelope, address, options):
        envelope.rcpt_options.extend(options)
        if address == "bart@example.com":
            return self.RejectCode.to_str()
        envelope.rcpt_tos.append(address)
        return S.S250_OK.to_str()


class ErroringDataHandler:
    ReturnCode = StatusCode(599, b"Not today")

    async def handle_DATA(self, server, session, envelope):
        return self.ReturnCode.to_str()


class AUTHHandler:
    async def handle_AUTH(self, server, session, envelope, args):
        server.authenticates = True
        return S.S235_AUTH_SUCCESS.to_str()


class NoHooksHandler:
    pass


class DeprecatedHookController(Controller):
    class DeprecatedHookServer(Server):

        warnings: list = None

        def __init__(self, *args, **kws):
            super().__init__(*args, **kws)

        async def ehlo_hook(self):
            pass

        async def rset_hook(self):
            pass

    def factory(self):
        self.smtpd = self.DeprecatedHookServer(self.handler)
        return self.smtpd


class DeprecatedHandler:
    def process_message(self, peer, mailfrom, rcpttos, data, **kws):
        pass


class AsyncDeprecatedHandler:
    async def process_message(self, peer, mailfrom, rcpttos, data, **kws):
        pass


# endregion


# region ##### Fixtures #######################################################


@pytest.fixture
def debugging_controller(get_controller) -> Generator[Controller, None, None]:
    # Cannot use plain_controller fixture because we need to first create the
    # Debugging handler before creating the controller.
    stream = StringIO()
    handler = Debugging(stream)
    controller = get_controller(handler)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    controller.stop()
    stream.close()


@pytest.fixture
def temp_maildir(tmp_path: Path) -> Path:
    return tmp_path / "maildir"


@pytest.fixture
def mailbox_controller(
    temp_maildir, get_controller
) -> Generator[Controller, None, None]:
    handler = Mailbox(temp_maildir)
    controller = get_controller(handler)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    controller.stop()


@pytest.fixture
def with_fake_parser() -> Callable:
    """
    Gets a function that will instantiate a handler_class using the class's
    from_cli() @classmethod, using FakeParser as the parser.

    This function will also catch any exceptions and store the exception's type --
    alongside any message passed to FakeParser.error() -- in the handler object itself
    (using the HasFakeParser protocol/mixin).
    """
    parser = FakeParser()

    def handler_initer(handler_class: Type[T], *args) -> Union[T, HasFakeParser]:
        handler: Union[T, HasFakeParser]
        try:
            handler = handler_class.from_cli(parser, *args)
            handler.fparser = parser
            handler.exception = None
        except (Exception, SystemExit) as e:
            handler = SimpleNamespace(fparser=parser, exception=type(e))
        return handler

    return handler_initer


@pytest.fixture
def upstream_controller(get_controller) -> Generator[Controller, None, None]:
    upstream_handler = DataHandler()
    upstream_controller = get_controller(upstream_handler, port=9025)
    upstream_controller.start()
    # Notice that we do NOT invoke Global.set_addr_from() here
    #
    yield upstream_controller
    #
    upstream_controller.stop()


@pytest.fixture
def proxy_nodecode_controller(
    upstream_controller, get_controller
) -> Generator[Union[Controller, KnowsUpstream], None, None]:
    proxy_handler = Proxy(upstream_controller.hostname, upstream_controller.port)
    proxy_controller = get_controller(proxy_handler)
    proxy_controller.upstream = upstream_controller
    proxy_controller.start()
    Global.set_addr_from(proxy_controller)
    #
    yield proxy_controller
    #
    proxy_controller.stop()


@pytest.fixture
def proxy_decoding_controller(
    upstream_controller, get_controller
) -> Generator[Union[Controller, KnowsUpstream], None, None]:
    proxy_handler = Proxy(upstream_controller.hostname, upstream_controller.port)
    proxy_controller = get_controller(proxy_handler, decode_data=True)
    proxy_controller.upstream = upstream_controller
    proxy_controller.start()
    Global.set_addr_from(proxy_controller)
    #
    yield proxy_controller
    #
    proxy_controller.stop()


# endregion


class TestDebugging:
    @controller_data(decode_data=True)
    def test_debugging(self, debugging_controller, client):
        peer = client.sock.getsockname()
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test

                Testing
                """
            ),
        )
        handler = debugging_controller.handler
        assert isinstance(handler, Debugging)
        text = handler.stream.getvalue()
        assert text == dedent(
            f"""\
            ---------- MESSAGE FOLLOWS ----------
            mail options: ['SIZE=102']

            From: Anne Person <anne@example.com>
            To: Bart Person <bart@example.com>
            Subject: A test
            X-Peer: {peer!r}

            Testing
            ------------ END MESSAGE ------------
            """
        )

    def test_debugging_bytes(self, debugging_controller, client):
        peer = client.sock.getsockname()
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test

                Testing
                """
            ),
        )
        handler = debugging_controller.handler
        assert isinstance(handler, Debugging)
        text = handler.stream.getvalue()
        assert text == dedent(
            f"""\
            ---------- MESSAGE FOLLOWS ----------
            mail options: ['SIZE=102']

            From: Anne Person <anne@example.com>
            To: Bart Person <bart@example.com>
            Subject: A test
            X-Peer: {peer!r}

            Testing
            ------------ END MESSAGE ------------
            """
        )

    def test_debugging_without_options(self, debugging_controller, client):
        # Prevent ESMTP options.
        client.helo()
        peer = client.sock.getsockname()
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test

                Testing
                """
            ),
        )
        handler = debugging_controller.handler
        assert isinstance(handler, Debugging)
        text = handler.stream.getvalue()
        assert text == dedent(
            f"""\
            ---------- MESSAGE FOLLOWS ----------
            From: Anne Person <anne@example.com>
            To: Bart Person <bart@example.com>
            Subject: A test
            X-Peer: {peer!r}

            Testing
            ------------ END MESSAGE ------------
            """
        )

    def test_debugging_with_options(self, debugging_controller, client):
        peer = client.sock.getsockname()
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test

                Testing
                """
            ),
            mail_options=["BODY=7BIT"],
        )
        handler = debugging_controller.handler
        assert isinstance(handler, Debugging)
        text = handler.stream.getvalue()
        assert text == dedent(
            f"""\
            ---------- MESSAGE FOLLOWS ----------
            mail options: ['SIZE=102', 'BODY=7BIT']

            From: Anne Person <anne@example.com>
            To: Bart Person <bart@example.com>
            Subject: A test
            X-Peer: {peer!r}

            Testing
            ------------ END MESSAGE ------------
            """
        )


class TestMessage:
    @pytest.mark.parametrize(
        "content",
        [
            b"",
            bytearray(),
            "",
        ],
        ids=["bytes", "bytearray", "str"]
    )
    def test_prepare_message(self, temp_event_loop, content):
        sess_ = ServerSession(temp_event_loop)
        enve_ = Envelope()
        handler = MessageHandler()
        enve_.content = content
        msg = handler.prepare_message(sess_, enve_)
        assert isinstance(msg, Em_Message)
        assert msg.keys() == ['X-Peer', 'X-MailFrom', 'X-RcptTo']
        assert msg.get_payload() == ""

    @pytest.mark.parametrize(
        ("content", "expectre"),
        [
            (None, r"Expected str or bytes, got <class 'NoneType'>"),
            ([], r"Expected str or bytes, got <class 'list'>"),
            ({}, r"Expected str or bytes, got <class 'dict'>"),
            ((), r"Expected str or bytes, got <class 'tuple'>"),
        ],
        ids=("None", "List", "Dict", "Tuple")
    )
    def test_prepare_message_err(self, temp_event_loop, content, expectre):
        sess_ = ServerSession(temp_event_loop)
        enve_ = Envelope()
        handler = MessageHandler()
        enve_.content = content
        with pytest.raises(TypeError, match=expectre):
            _ = handler.prepare_message(sess_, enve_)

    @handler_data(class_=DataHandler)
    def test_message(self, plain_controller, client):
        handler = plain_controller.handler
        assert isinstance(handler, DataHandler)
        # In this test, the message content comes in as a bytes.
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Testing
                """
            ),
        )
        # The content is not converted, so it's bytes.
        assert handler.content == handler.original_content
        assert isinstance(handler.content, bytes)
        assert isinstance(handler.original_content, bytes)

    @handler_data(class_=DataHandler)
    def test_message_decoded(self, decoding_controller, client):
        handler = decoding_controller.handler
        assert isinstance(handler, DataHandler)
        # In this test, the message content comes in as a string.
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Testing
                """
            ),
        )
        assert handler.content != handler.original_content
        assert isinstance(handler.content, str)
        assert isinstance(handler.original_content, bytes)

    @handler_data(class_=AsyncMessageHandler)
    def test_message_async(self, plain_controller, client):
        handler = plain_controller.handler
        assert isinstance(handler, AsyncMessageHandler)
        # In this test, the message data comes in as bytes.
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Testing
                """
            ),
        )
        handled_message = handler.handled_message
        assert handled_message["subject"] == "A test"
        assert handled_message["message-id"] == "<ant>"
        assert handled_message["X-Peer"] is not None
        assert handled_message["X-MailFrom"] == "anne@example.com"
        assert handled_message["X-RcptTo"] == "bart@example.com"

    @handler_data(class_=AsyncMessageHandler)
    def test_message_decoded_async(self, decoding_controller, client):
        handler = decoding_controller.handler
        assert isinstance(handler, AsyncMessageHandler)
        # With a server that decodes the data, the messages come in as
        # strings.  There's no difference in the message seen by the
        # handler's handle_message() method, but internally this gives full
        # coverage.
        client.sendmail(
            "anne@example.com",
            ["bart@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Testing
                """
            ),
        )
        handled_message = handler.handled_message
        assert handled_message["subject"] == "A test"
        assert handled_message["message-id"] == "<ant>"
        assert handled_message["X-Peer"] is not None
        assert handled_message["X-MailFrom"] == "anne@example.com"
        assert handled_message["X-RcptTo"] == "bart@example.com"


class TestMailbox:
    def test_mailbox(self, temp_maildir, mailbox_controller, client):
        client.sendmail(
            "aperson@example.com",
            ["bperson@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Hi Bart, this is Anne.
                """
            ),
        )
        client.sendmail(
            "cperson@example.com",
            ["dperson@example.com"],
            dedent(
                """\
                From: Cate Person <cate@example.com>
                To: Dave Person <dave@example.com>
                Subject: A test
                Message-ID: <bee>

                Hi Dave, this is Cate.
                """
            ),
        )
        client.sendmail(
            "eperson@example.com",
            ["fperson@example.com"],
            dedent(
                """\
                From: Elle Person <elle@example.com>
                To: Fred Person <fred@example.com>
                Subject: A test
                Message-ID: <cat>

                Hi Fred, this is Elle.
                """
            ),
        )
        # Check the messages in the mailbox.
        mailbox = Maildir(temp_maildir)
        messages = sorted(mailbox, key=itemgetter("message-id"))
        expect = ["<ant>", "<bee>", "<cat>"]
        assert [message["message-id"] for message in messages] == expect

    def test_mailbox_reset(self, temp_maildir, mailbox_controller, client):
        client.sendmail(
            "aperson@example.com",
            ["bperson@example.com"],
            dedent(
                """\
                From: Anne Person <anne@example.com>
                To: Bart Person <bart@example.com>
                Subject: A test
                Message-ID: <ant>

                Hi Bart, this is Anne.
                """
            ),
        )
        mailbox_controller.handler.reset()
        mailbox = Maildir(temp_maildir)
        assert list(mailbox) == []


class TestCLI:
    def test_debugging_no_args(self, with_fake_parser):
        handler = with_fake_parser(Debugging)
        assert handler.exception is None
        assert handler.fparser.message is None
        assert handler.stream == sys.stdout

    def test_debugging_two_args(self, with_fake_parser):
        handler = with_fake_parser(Debugging, "foo", "bar")
        assert handler.exception is SystemExit
        assert handler.fparser.message == "Debugging usage: [stdout|stderr]"

    def test_debugging_stdout(self, with_fake_parser):
        handler = with_fake_parser(Debugging, "stdout")
        assert handler.exception is None
        assert handler.fparser.message is None
        assert handler.stream == sys.stdout

    def test_debugging_stderr(self, with_fake_parser):
        handler = with_fake_parser(Debugging, "stderr")
        assert handler.exception is None
        assert handler.fparser.message is None
        assert handler.stream == sys.stderr

    def test_debugging_bad_argument(self, with_fake_parser):
        handler = with_fake_parser(Debugging, "stdfoo")
        assert handler.exception is SystemExit
        assert handler.fparser.message == "Debugging usage: [stdout|stderr]"

    def test_sink_no_args(self, with_fake_parser):
        handler = with_fake_parser(Sink)
        assert handler.exception is None
        assert handler.fparser.message is None
        assert isinstance(handler, Sink)

    def test_sink_any_args(self, with_fake_parser):
        handler = with_fake_parser(Sink, "foo")
        assert handler.exception is SystemExit
        assert handler.fparser.message == "Sink handler does not accept arguments"

    def test_mailbox_no_args(self, with_fake_parser):
        handler = with_fake_parser(Mailbox)
        assert handler.exception is SystemExit
        assert handler.fparser.message == "The directory for the maildir is required"

    def test_mailbox_too_many_args(self, with_fake_parser):
        handler = with_fake_parser(Mailbox, "foo", "bar", "baz")
        assert handler.exception is SystemExit
        assert handler.fparser.message == "Too many arguments for Mailbox handler"

    def test_mailbox(self, with_fake_parser, temp_maildir):
        handler = with_fake_parser(Mailbox, temp_maildir)
        assert handler.exception is None
        assert handler.fparser.message is None
        assert isinstance(handler.mailbox, Maildir)
        assert handler.mail_dir == temp_maildir


class TestProxy:
    sender_addr = "anne@example.com"
    receiver_addr = "bart@example.com"

    source_lines = [
        f"From: Anne Person <{sender_addr}>",
        f"To: Bart Person <{receiver_addr}>",
        "Subject: A test",
        "%s",  # Insertion point; see below
        "Testing",
        "",
    ]

    # For "source" we insert an empty string
    source = "\n".join(source_lines) % ""

    # For "expected" we insert X-Peer with yet another template
    expected_template = (
        b"\r\n".join(ln.encode("ascii") for ln in source_lines) % b"X-Peer: %s\r\n"
    )

    # There are two controllers and two SMTPd's running here.  The
    # "upstream" one listens on port 9025 and is connected to a "data
    # handler" which captures the messages it receives.  The second -and
    # the one under test here- listens on port 9024 and proxies to the one
    # on port 9025.

    def test_deliver_bytes(self, proxy_nodecode_controller, client):
        client.sendmail(self.sender_addr, [self.receiver_addr], self.source)
        upstream = proxy_nodecode_controller.upstream
        upstream_handler = upstream.handler
        assert isinstance(upstream_handler, DataHandler)
        proxysess: ServerSession = proxy_nodecode_controller.smtpd.session
        expected = self.expected_template % proxysess.peer[0].encode("ascii")
        assert upstream.handler.content == expected
        assert upstream.handler.original_content == expected

    def test_deliver_str(self, proxy_decoding_controller, client):
        client.sendmail(self.sender_addr, [self.receiver_addr], self.source)
        upstream = proxy_decoding_controller.upstream
        upstream_handler = upstream.handler
        assert isinstance(upstream_handler, DataHandler)
        proxysess: ServerSession = proxy_decoding_controller.smtpd.session
        expected = self.expected_template % proxysess.peer[0].encode("ascii")
        assert upstream.handler.content == expected
        assert upstream.handler.original_content == expected


class TestProxyMocked:
    BAD_BART = {"bart@example.com": (500, "Bad Bart")}
    SOURCE = dedent(
        """\
        From: Anne Person <anne@example.com>
        To: Bart Person <bart@example.com>
        Subject: A test

        Testing
        """
    )

    @pytest.fixture
    def patch_smtp_refused(self, mocker):
        mock = mocker.patch("aiosmtpd.handlers.smtplib.SMTP")
        mock().sendmail.side_effect = SMTPRecipientsRefused(self.BAD_BART)

    def test_recipients_refused(
        self, caplog, patch_smtp_refused, proxy_decoding_controller, client
    ):
        logger_name = "mail.debug"
        caplog.set_level(logging.INFO, logger=logger_name)
        client.sendmail("anne@example.com", ["bart@example.com"], self.SOURCE)
        # The log contains information about what happened in the proxy.
        # Ideally it would be the newest 2 log records. However, sometimes asyncio
        # will emit a log entry right afterwards or inbetween causing test fail if we
        # just checked [-1] and [-2]. Therefore we need to scan backwards and simply
        # note the two log entries' relative position
        _l1 = _l2 = -1
        for _l1, rt in enumerate(reversed(caplog.record_tuples)):
            if rt == (logger_name, logging.INFO, "got SMTPRecipientsRefused"):
                break
        else:
            pytest.fail("Can't find first log entry")
        for _l2, rt in enumerate(reversed(caplog.record_tuples)):
            if rt == (
                logger_name,
                logging.INFO,
                f"we got some refusals: {self.BAD_BART}",
            ):
                break
        else:
            pytest.fail("Can't find second log entry")
        assert _l2 < _l1, "Log entries in wrong order"

    @pytest.fixture
    def patch_smtp_oserror(self, mocker):
        mock = mocker.patch("aiosmtpd.handlers.smtplib.SMTP")
        mock().sendmail.side_effect = OSError

    def test_oserror(
        self, caplog, patch_smtp_oserror, proxy_decoding_controller, client
    ):
        logger_name = "mail.debug"
        caplog.set_level(logging.INFO, logger=logger_name)
        client.sendmail("anne@example.com", ["bart@example.com"], self.SOURCE)
        for rt in reversed(caplog.record_tuples):
            if rt == (
                logger_name,
                logging.INFO,
                "we got some refusals: {'bart@example.com': (-1, b'ignore')}",
            ):
                break
        else:
            pytest.fail("Can't find log entry")


class TestHooks:
    @handler_data(class_=HELOHandler)
    def test_hook_HELO(self, plain_controller, client):
        assert isinstance(plain_controller.handler, HELOHandler)
        resp = client.helo("me")
        assert resp == HELOHandler.ReturnCode

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    @handler_data(class_=EHLOHandlerDeprecated)
    def test_hook_EHLO_deprecated(self, plain_controller, client):
        assert isinstance(plain_controller.handler, EHLOHandlerDeprecated)
        code, mesg = client.ehlo("me")
        lines = mesg.decode("utf-8").splitlines()
        assert code == 250
        assert lines[-1] == EHLOHandlerDeprecated.Domain

    def test_hook_EHLO_deprecated_warning(self):
        with pytest.warns(
            DeprecationWarning,
            match=(
                # Is a regex; escape regex special chars if necessary
                r"Use the 5-argument handle_EHLO\(\) hook instead of the "
                r"4-argument handle_EHLO\(\) hook; support for the 4-argument "
                r"handle_EHLO\(\) hook will be removed in version 2.0"
            ),
        ):
            _ = Server(EHLOHandlerDeprecated())

    @handler_data(
        class_=EHLOHandlerNew,
        args_=("FEATURE1", "FEATURE2 OPTION", "FEAT3 OPTA OPTB"),
    )
    def test_hook_EHLO_new(self, plain_controller, client):
        assert isinstance(plain_controller.handler, EHLOHandlerNew)
        code, mesg = client.ehlo("me")
        lines = mesg.decode("utf-8").splitlines()
        assert code == 250
        assert len(lines) == 5  # server name + 3 features + HELP
        handler = plain_controller.handler
        assert "250-8BITMIME" in handler.orig_responses
        assert "8bitmime" not in client.esmtp_features
        assert "250-SMTPUTF8" in handler.orig_responses
        assert "smtputf8" not in client.esmtp_features

        assert "feature1" in client.esmtp_features
        assert "feature2" in client.esmtp_features
        assert client.esmtp_features["feature2"] == "OPTION"
        assert "feat3" in client.esmtp_features
        assert client.esmtp_features["feat3"] == "OPTA OPTB"
        assert "help" in client.esmtp_features

    @pytest.mark.parametrize(
        "handler_class",
        [EHLOHandlerIncompatibleShort, EHLOHandlerIncompatibleLong],
        ids=["TooShort", "TooLong"],
    )
    def test_hook_EHLO_incompat(self, handler_class):
        with pytest.raises(RuntimeError, match="Unsupported EHLO Hook"):
            _ = Server(handler_class())

    @handler_data(class_=MAILHandler)
    def test_hook_MAIL(self, plain_controller, client):
        assert isinstance(plain_controller, Controller)
        handler = plain_controller.handler
        assert isinstance(handler, MAILHandler)
        client.ehlo("me")
        resp = client.mail("anne@example.com", ("BODY=7BIT", "SIZE=2000"))
        assert resp == MAILHandler.ReturnCode
        smtpd = plain_controller.smtpd
        assert smtpd.envelope.mail_options == MAILHandler.ReplacementOptions

    @handler_data(class_=RCPTHandler)
    def test_hook_RCPT(self, plain_controller, client):
        assert isinstance(plain_controller.handler, RCPTHandler)
        client.helo("me")
        with pytest.raises(SMTPRecipientsRefused) as excinfo:
            client.sendmail(
                "anne@example.com",
                ["bart@example.com"],
                dedent(
                    """\
                    From: anne@example.com
                    To: bart@example.com
                    Subject: Test

                    """
                ),
            )
        assert excinfo.value.recipients == {
            "bart@example.com": RCPTHandler.RejectCode,
        }

    @handler_data(class_=ErroringDataHandler)
    def test_hook_DATA(self, plain_controller, client):
        assert isinstance(plain_controller.handler, ErroringDataHandler)
        with pytest.raises(SMTPDataError) as excinfo:
            client.sendmail(
                "anne@example.com",
                ["bart@example.com"],
                dedent(
                    """\
                    From: anne@example.com
                    To: bart@example.com
                    Subject: Test

                    Yikes
                    """
                ),
            )
        expected: StatusCode = ErroringDataHandler.ReturnCode
        assert excinfo.value.smtp_code == expected.code
        assert excinfo.value.smtp_error == expected.mesg

    @controller_data(decode_data=True, auth_require_tls=False)
    @handler_data(class_=AUTHHandler)
    def test_hook_AUTH(self, plain_controller, client):
        assert isinstance(plain_controller.handler, AUTHHandler)
        client.ehlo("me")
        resp = client.login("test", "test")
        assert resp == S.S235_AUTH_SUCCESS

    @handler_data(class_=NoHooksHandler)
    def test_hook_NoHooks(self, plain_controller, client):
        assert isinstance(plain_controller.handler, NoHooksHandler)
        client.helo("me")
        client.mail("anne@example.com")
        client.rcpt(["bart@example.cm"])
        code, _ = client.data(
            dedent(
                """\
                From: anne@example.com
                To: bart@example.com
                Subject: Test

                """
            )
        )
        assert code == 250


class TestDeprecation:
    def _process_message_testing(self, controller, client):
        assert isinstance(controller, Controller)
        expectedre = r"Use handler.handle_DATA\(\) instead of .process_message\(\)"
        with pytest.warns(DeprecationWarning, match=expectedre):
            client.sendmail(
                "anne@example.com",
                ["bart@example.com"],
                dedent(
                    """
                    From: Anne Person <anne@example.com>
                    To: Bart Person <bart@example.com>
                    Subject: A test

                    Testing
                    """
                ),
            )

    @handler_data(class_=DeprecatedHandler)
    def test_process_message(self, plain_controller, client):
        """handler.process_message is Deprecated"""
        handler = plain_controller.handler
        assert isinstance(handler, DeprecatedHandler)
        controller = plain_controller
        self._process_message_testing(controller, client)

    @handler_data(class_=AsyncDeprecatedHandler)
    def test_process_message_async(self, plain_controller, client):
        """handler.process_message is Deprecated"""
        handler = plain_controller.handler
        assert isinstance(handler, AsyncDeprecatedHandler)
        controller = plain_controller
        self._process_message_testing(controller, client)

    @controller_data(class_=DeprecatedHookController)
    def test_ehlo_hook(self, plain_controller, client):
        """SMTP.ehlo_hook is Deprecated"""
        expectedre = r"Use handler.handle_EHLO\(\) instead of .ehlo_hook\(\)"
        with pytest.warns(DeprecationWarning, match=expectedre):
            client.ehlo("example.com")

    @controller_data(class_=DeprecatedHookController)
    def test_rset_hook(self, plain_controller, client):
        """SMTP.rset_hook is Deprecated"""
        expectedre = r"Use handler.handle_RSET\(\) instead of .rset_hook\(\)"
        with pytest.warns(DeprecationWarning, match=expectedre):
            client.rset()
