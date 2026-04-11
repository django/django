# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Handlers which provide custom processing at various events.

At certain times in the SMTP protocol, various events can be processed.  These
events include the SMTP commands, and at the completion of the data receipt.
Pass in an instance of one of these classes, or derive your own, to provide
your own handling of messages.  Implement only the methods you care about.
"""

import asyncio
import logging
import mailbox
import os
import re
import smtplib
import sys
from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from email.message import Message as Em_Message
from email.parser import BytesParser, Parser
from typing import Any, List, TextIO, Type, TypeVar, Optional, Union

from public import public

from aiosmtpd import _get_or_new_eventloop
from aiosmtpd.smtp import SMTP as SMTPServer
from aiosmtpd.smtp import Envelope as SMTPEnvelope
from aiosmtpd.smtp import Session as SMTPSession

T = TypeVar("T")

EMPTYBYTES = b""
COMMASPACE = ", "
CRLF = b"\r\n"
NLCRE = re.compile(br"\r\n|\r|\n")
log = logging.getLogger("mail.debug")


def _format_peer(peer: str) -> str:
    # This is a separate function mostly so the test suite can craft a
    # reproducible output.
    return "X-Peer: {!r}".format(peer)


def message_from_bytes(s, *args, **kws):
    return BytesParser(*args, **kws).parsebytes(s)


def message_from_string(s, *args, **kws):
    return Parser(*args, **kws).parsestr(s)


@public
class Debugging:
    def __init__(self, stream: Optional[TextIO] = None):
        self.stream: TextIO = sys.stdout if stream is None else stream

    @classmethod
    def from_cli(cls: Type[T], parser: ArgumentParser, *args) -> T:
        # TODO(PY311): Use Self instead of T.
        error = False
        stream = None
        if len(args) == 0:
            pass
        elif len(args) > 1:
            error = True
        elif args[0] == "stdout":
            stream = sys.stdout
        elif args[0] == "stderr":
            stream = sys.stderr
        else:
            error = True
        if error:
            parser.error("Debugging usage: [stdout|stderr]")
        return cls(stream)  # type: ignore[call-arg]

    def _print_message_content(self, peer: str, data: Union[str, bytes]) -> None:
        in_headers = True
        for line in data.splitlines():
            # Dump the RFC 2822 headers first.
            if in_headers and not line:
                print(_format_peer(peer), file=self.stream)
                in_headers = False
            if isinstance(line, bytes):
                # Avoid spurious 'str on bytes instance' warning.
                line = line.decode("utf-8", "replace")
            print(line, file=self.stream)

    async def handle_DATA(
        self, server: SMTPServer, session: SMTPSession, envelope: SMTPEnvelope
    ) -> str:
        print("---------- MESSAGE FOLLOWS ----------", file=self.stream)
        # Yes, actually test for truthiness since it's possible for either the
        # keywords to be missing, or for their values to be empty lists.
        add_separator = False
        if envelope.mail_options:
            print("mail options:", envelope.mail_options, file=self.stream)
            add_separator = True
        # rcpt_options are not currently support by the SMTP class.
        rcpt_options = envelope.rcpt_options
        if any(rcpt_options):  # pragma: nocover
            print("rcpt options:", rcpt_options, file=self.stream)
            add_separator = True
        if add_separator:
            print(file=self.stream)
        assert session.peer is not None
        assert envelope.content is not None
        self._print_message_content(session.peer, envelope.content)
        print("------------ END MESSAGE ------------", file=self.stream)
        return "250 OK"


@public
class Proxy:
    def __init__(self, remote_hostname: str, remote_port: int):
        self._hostname = remote_hostname
        self._port = remote_port

    async def handle_DATA(
        self, server: SMTPServer, session: SMTPSession, envelope: SMTPEnvelope
    ) -> str:
        if isinstance(envelope.content, str):
            content = envelope.original_content
        else:
            content = envelope.content
        assert content is not None
        lines = content.splitlines(keepends=True)
        # Look for the last header
        _i = 0
        ending = CRLF
        for _i, line in enumerate(lines):  # pragma: nobranch
            if NLCRE.match(line):
                ending = line
                break
        assert session.peer is not None
        peer = session.peer[0].encode("ascii")
        lines.insert(_i, b"X-Peer: " + peer + ending)
        data = EMPTYBYTES.join(lines)
        assert envelope.mail_from is not None
        assert all(r is not None for r in envelope.rcpt_tos)
        refused = self._deliver(envelope.mail_from, envelope.rcpt_tos, data)
        # TBD: what to do with refused addresses?
        log.info("we got some refusals: %s", refused)
        return "250 OK"

    def _deliver(
        self,
        mail_from: str,
        rcpt_tos: List[str],
        data: Union[str, bytes]
    ) -> Any:
        refused = {}
        try:
            s = smtplib.SMTP()
            s.connect(self._hostname, self._port)
            try:
                refused = s.sendmail(mail_from, rcpt_tos, data)  # pytype: disable=wrong-arg-types  # noqa: E501
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused as e:
            log.info("got SMTPRecipientsRefused")
            refused = e.recipients
        except (OSError, smtplib.SMTPException) as e:
            log.exception("got %s", e.__class__)
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise, fake it with a non-triggering
            # exception code.
            errcode = getattr(e, "smtp_code", -1)
            errmsg = getattr(e, "smtp_error", b"ignore")
            for r in rcpt_tos:
                refused[r] = (errcode, errmsg)
        return refused


@public
class Sink:
    @classmethod
    def from_cli(cls: Type[T], parser: ArgumentParser, *args) -> T:
        if len(args) > 0:
            parser.error("Sink handler does not accept arguments")
        return cls()


class MessageBase(metaclass=ABCMeta):
    def __init__(self, message_class: Optional[Type[Em_Message]] = None):
        self.message_class = message_class

    def prepare_message(
        self, session: SMTPSession, envelope: SMTPEnvelope
    ) -> Em_Message:
        # If the server was created with decode_data True, then data will be a
        # str, otherwise it will be bytes.
        data = envelope.content
        message: Em_Message
        if isinstance(data, (bytes, bytearray)):
            message = message_from_bytes(data, self.message_class)
        elif isinstance(data, str):
            message = message_from_string(data, self.message_class)
        else:
            raise TypeError(f"Expected str or bytes, got {type(data)}")
        assert isinstance(message, Em_Message)
        message["X-Peer"] = str(session.peer)
        message["X-MailFrom"] = envelope.mail_from
        message["X-RcptTo"] = COMMASPACE.join(envelope.rcpt_tos)
        return message

    @abstractmethod
    async def handle_DATA(
        self, server: SMTPServer, session: SMTPSession, envelope: SMTPEnvelope
    ) -> str:
        ...


@public
class Message(MessageBase, metaclass=ABCMeta):
    async def handle_DATA(
        self, server: SMTPServer, session: SMTPSession, envelope: SMTPEnvelope
    ) -> str:
        message = self.prepare_message(session, envelope)
        self.handle_message(message)
        return "250 OK"

    @abstractmethod
    def handle_message(self, message: Em_Message) -> None:
        ...


@public
class AsyncMessage(MessageBase, metaclass=ABCMeta):
    def __init__(
        self,
        message_class: Optional[Type[Em_Message]] = None,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        super().__init__(message_class)
        self.loop = loop or _get_or_new_eventloop()

    async def handle_DATA(
        self, server: SMTPServer, session: SMTPSession, envelope: SMTPEnvelope
    ) -> str:
        message = self.prepare_message(session, envelope)
        await self.handle_message(message)
        return "250 OK"

    @abstractmethod
    async def handle_message(self, message: Em_Message) -> None:
        ...


@public
class Mailbox(Message):
    def __init__(
        self,
        mail_dir: os.PathLike,
        message_class: Optional[Type[Em_Message]] = None,
    ):
        self.mailbox = mailbox.Maildir(mail_dir)
        self.mail_dir = mail_dir
        super().__init__(message_class)

    def handle_message(self, message: Em_Message) -> None:
        self.mailbox.add(message)

    def reset(self) -> None:
        self.mailbox.clear()

    @classmethod
    def from_cli(cls: Type[T], parser: ArgumentParser, *args) -> T:
        # TODO(PY311): Use Self instead of T.
        if len(args) < 1:
            parser.error("The directory for the maildir is required")
        elif len(args) > 1:
            parser.error("Too many arguments for Mailbox handler")
        return cls(args[0])  # type: ignore[call-arg]
