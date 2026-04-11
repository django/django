# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import asyncio
import asyncio.sslproto as sslproto
import binascii
import collections
import enum
import inspect
import logging
import re
import socket
import ssl
from base64 import b64decode, b64encode
from email._header_value_parser import get_addr_spec, get_angle_addr
from email.errors import HeaderParseError
from typing import (
    Any,
    AnyStr,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from warnings import warn

import attr
from public import public

from aiosmtpd import __version__, _get_or_new_eventloop
from aiosmtpd.proxy_protocol import ProxyData, get_proxy


# region #### Custom Data Types #######################################################

class _Missing(enum.Enum):
    MISSING = object()


class _AuthMechAttr(NamedTuple):
    method: "AuthMechanismType"
    is_builtin: bool


class _DataState(enum.Enum):
    NOMINAL = enum.auto()
    TOO_LONG = enum.auto()
    TOO_MUCH = enum.auto()


AuthCallbackType = Callable[[str, bytes, bytes], bool]
AuthenticatorType = Callable[["SMTP", "Session", "Envelope", str, Any], "AuthResult"]
AuthMechanismType = Callable[["SMTP", List[str]], Awaitable[Any]]
_TriStateType = Union[None, _Missing, bytes]

RT = TypeVar("RT")  # "ReturnType"
DecoratorType = Callable[[Callable[..., RT]], Callable[..., RT]]


# endregion


# region #### Constant & Constant-likes ###############################################

__all__ = [
    "AuthCallbackType",
    "AuthMechanismType",
    "MISSING",
    "__version__",
]  # Will be added to by @public
__ident__ = 'Python SMTP {}'.format(__version__)
log = logging.getLogger('mail.log')


BOGUS_LIMIT = 5
CALL_LIMIT_DEFAULT = 20
DATA_SIZE_DEFAULT = 2**25  # Where does this number come from, I wonder...
EMPTY_BARR = bytearray()
EMPTYBYTES = b''
MISSING = _Missing.MISSING
VALID_AUTHMECH = re.compile(r"[A-Z0-9_-]+\Z")

# https://tools.ietf.org/html/rfc3207.html#page-3
ALLOWED_BEFORE_STARTTLS = {"NOOP", "EHLO", "STARTTLS", "QUIT"}

# Auth hiding regexes
CLIENT_AUTH_B = re.compile(
    # Matches "AUTH" <mechanism> <whitespace_but_not_\r_nor_\n>
    br"(?P<authm>\s*AUTH\s+\S+[^\S\r\n]+)"
    # Param to AUTH <mechanism>. We only need to sanitize if param is given, which
    # for some mechanisms contain sensitive info. If no param is given, then we
    # can skip (match fails)
    br"(\S+)"
    # Optional bCRLF at end. Why optional? Because we also want to sanitize the
    # stripped line. If no bCRLF, then this group will be b""
    br"(?P<crlf>(?:\r\n)?)", re.IGNORECASE
)
"""Regex that matches 'AUTH <mech> <param>' commend"""

# endregion


@attr.s
class AuthResult:
    """
    Contains the result of authentication, to be returned to the smtp_AUTH method.
    All initialization arguments _must_ be keyworded!
    """

    success: bool = attr.ib(kw_only=True)
    """Indicates authentication is successful or not"""

    handled: bool = attr.ib(kw_only=True, default=True)
    """
    True means everything (including sending of status code) has been handled by the
    AUTH handler and smtp_AUTH should not do anything else.
    Applicable only if success == False.
    """

    message: Optional[str] = attr.ib(kw_only=True, default=None)
    """
    Optional message for additional handling by smtp_AUTH.
    Applicable only if handled == False.
    """

    auth_data: Optional[Any] = attr.ib(kw_only=True, default=None, repr=lambda x: "...")
    """
    Optional free-form authentication data. For the built-in mechanisms, it is usually
    an instance of LoginPassword. Other implementations are free to use any data
    structure here.
    """


@public
class LoginPassword(NamedTuple):
    login: bytes
    password: bytes

    def __str__(self) -> str:
        return f"LoginPassword(login='{self.login.decode()}', password=...)"

    def __repr__(self) -> str:
        return str(self)


@public
class Session:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.peer: Optional[str] = None
        self.ssl: Optional[dict[str, Any]] = None
        self.host_name: Optional[str] = None
        self.extended_smtp = False
        self.loop = loop

        self.proxy_data: Optional[ProxyData] = None
        """Data from PROXY Protocol handshake"""

        self._login_data = None

        self.auth_data = None
        """
        New system *optional* authentication data;
        can contain anything returned by the authenticator callback.
        Can even be None; check `authenticated` attribute to determine
        if AUTH successful or not.
        """

        self.authenticated: Optional[bool] = None

    @property
    def login_data(self) -> Any:
        """Legacy login_data, usually containing the username"""
        log.warning(
            "Session.login_data is deprecated and will be removed in version 2.0"
        )
        return self._login_data

    @login_data.setter
    def login_data(self, value: Any) -> None:
        log.warning(
            "Session.login_data is deprecated and will be removed in version 2.0"
        )
        self._login_data = value


@public
class Envelope:
    def __init__(self) -> None:
        self.mail_from: Optional[str] = None
        self.mail_options: List[str] = []
        self.smtp_utf8 = False
        self.content: Union[None, bytes, str] = None
        self.original_content: Optional[bytes] = None
        self.rcpt_tos: List[str] = []
        self.rcpt_options: List[str] = []


# This is here to enable debugging output when the -E option is given to the
# unit test suite.  In that case, this function is mocked to set the debug
# level on the loop (as if PYTHONASYNCIODEBUG=1 were set).
def make_loop() -> asyncio.AbstractEventLoop:
    return _get_or_new_eventloop()


@public
def syntax(
        text: str, extended: Optional[str] = None, when: Optional[str] = None
) -> DecoratorType:
    """
    A @decorator that provides helptext for (E)SMTP HELP.
    Applies for smtp_* methods only!

    :param text: Help text for (E)SMTP HELP
    :param extended: Additional text for ESMTP HELP (appended to text)
    :param when: The name of the attribute of SMTP class to check; if the value
        of the attribute is false-y then HELP will not be available for the command
    """
    def decorator(f: Callable[..., RT]) -> Callable[..., RT]:
        f.__smtp_syntax__ = text  # type: ignore[attr-defined]
        f.__smtp_syntax_extended__ = extended  # type: ignore[attr-defined]
        f.__smtp_syntax_when__ = when  # type: ignore[attr-defined]
        return f
    return decorator


@public
def auth_mechanism(actual_name: str) -> DecoratorType:
    """
    A @decorator to explicitly specifies the name of the AUTH mechanism implemented by
    the function/method this decorates

    :param actual_name: Name of AUTH mechanism. Must consists of [A-Z0-9_-] only.
        Will be converted to uppercase
    """
    def decorator(f: Callable[..., RT]) -> Callable[..., RT]:
        f.__auth_mechanism_name__ = actual_name  # type: ignore[attr-defined]
        return f

    actual_name = actual_name.upper()
    if not VALID_AUTHMECH.match(actual_name):
        raise ValueError(f"Invalid AUTH mechanism name: {actual_name}")
    return decorator


def login_always_fail(
        mechanism: str, login: bytes, password: bytes
) -> bool:
    return False


def is_int(o: Any) -> bool:
    return isinstance(o, int)


@public
class TLSSetupException(Exception):
    pass


@public
def sanitize(text: bytes) -> bytes:
    m = CLIENT_AUTH_B.match(text)
    if m:
        return m.group("authm") + b"********" + m.group("crlf")
    return text


@public
def sanitized_log(func: Callable[..., None], msg: AnyStr, *args, **kwargs) -> None:
    """
    Sanitize args before passing to a logging function.
    """
    sanitized_args = [
        sanitize(a) if isinstance(a, bytes) else a
        for a in args
    ]
    func(msg, *sanitized_args, **kwargs)


@public
class SMTP(asyncio.StreamReaderProtocol):
    """
    `Documentation can be found here
    <https://aiosmtpd.readthedocs.io/en/latest/smtp.html>`_
    """
    command_size_limit = 512
    command_size_limits: Dict[str, int] = collections.defaultdict(
        lambda: SMTP.command_size_limit)

    line_length_limit = 1001
    """Maximum line length according to RFC 5321 s 4.5.3.1.6"""
    # The number comes from this calculation:
    # (RFC 5322 s 2.1.1 + RFC 6532 s 3.4) 998 octets + CRLF = 1000 octets
    # (RFC 5321 s 4.5.3.1.6) 1000 octets + "transparent dot" = 1001 octets

    local_part_limit: int = 0
    """
    Maximum local part length. (RFC 5321 § 4.5.3.1.1 specifies 64, but lenient)
    If 0 or Falsey, local part length is unlimited.
    """

    AuthLoginUsernameChallenge = "User Name\x00"
    AuthLoginPasswordChallenge = "Password\x00"

    def __init__(
            self,
            handler: Any,
            *,
            data_size_limit: Optional[int] = DATA_SIZE_DEFAULT,
            enable_SMTPUTF8: bool = False,
            decode_data: bool = False,
            hostname: Optional[str] = None,
            ident: Optional[str] = None,
            tls_context: Optional[ssl.SSLContext] = None,
            require_starttls: bool = False,
            timeout: float = 300,
            auth_required: bool = False,
            auth_require_tls: bool = True,
            auth_exclude_mechanism: Optional[Iterable[str]] = None,
            auth_callback: Optional[AuthCallbackType] = None,
            command_call_limit: Union[int, Dict[str, int], None] = None,
            authenticator: Optional[AuthenticatorType] = None,
            proxy_protocol_timeout: Optional[Union[int, float]] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.__ident__ = ident or __ident__
        self.loop = loop if loop else make_loop()
        super().__init__(
            asyncio.StreamReader(loop=self.loop, limit=self.line_length_limit),
            client_connected_cb=self._cb_client_connected,
            loop=self.loop)
        self.event_handler = handler
        assert data_size_limit is None or isinstance(data_size_limit, int)
        self.data_size_limit = data_size_limit
        self.enable_SMTPUTF8 = enable_SMTPUTF8
        self._decode_data = decode_data
        self.command_size_limits.clear()
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = socket.getfqdn()
        self.tls_context = tls_context
        if tls_context:
            if (tls_context.verify_mode
                    not in {ssl.CERT_NONE, ssl.CERT_OPTIONAL}):  # noqa: DUO122
                log.warning("tls_context.verify_mode not in {CERT_NONE, "
                            "CERT_OPTIONAL}; this might cause client "
                            "connection problems")
            elif tls_context.check_hostname:
                log.warning("tls_context.check_hostname == True; "
                            "this might cause client connection problems")
        self.require_starttls = tls_context and require_starttls
        self._timeout_duration = timeout
        self._timeout_handle: Optional[asyncio.TimerHandle] = None
        self._tls_handshake_okay = True
        self._tls_protocol: Optional[sslproto.SSLProtocol] = None
        self._original_transport: Optional[asyncio.BaseTransport] = None
        self.session: Optional[Session] = None
        self.envelope: Optional[Envelope] = None
        self.transport: Optional[asyncio.BaseTransport] = None
        self._handler_coroutine: Optional[asyncio.Task[None]] = None
        if not auth_require_tls and auth_required:
            warn("Requiring AUTH while not requiring TLS "
                 "can lead to security vulnerabilities!")
            log.warning("auth_required == True but auth_require_tls == False")
        self._auth_require_tls = auth_require_tls

        if proxy_protocol_timeout is not None:
            if proxy_protocol_timeout <= 0:
                raise ValueError("proxy_protocol_timeout must be > 0")
            elif proxy_protocol_timeout < 3.0:
                log.warning("proxy_protocol_timeout < 3.0")
        self._proxy_timeout = proxy_protocol_timeout

        self._authenticator: Optional[AuthenticatorType]
        self._auth_callback: Optional[AuthCallbackType]
        if authenticator is not None:
            self._authenticator = authenticator
            self._auth_callback = None
        else:
            self._auth_callback = auth_callback or login_always_fail
            self._authenticator = None

        self._auth_required = auth_required

        # Get hooks & methods to significantly speedup getattr's
        self._auth_methods: Dict[str, _AuthMechAttr] = {
            getattr(
                mfunc, "__auth_mechanism_name__",
                mname.replace("auth_", "").replace("__", "-")
            ): _AuthMechAttr(mfunc, obj is self)
            for obj in (self, handler)
            for mname, mfunc in inspect.getmembers(obj)
            if mname.startswith("auth_")
        }
        for m in (auth_exclude_mechanism or []):
            self._auth_methods.pop(m, None)
        log.info(
            "Available AUTH mechanisms: "
            + " ".join(
                m + "(builtin)" if impl.is_builtin else m
                for m, impl in sorted(self._auth_methods.items())
            )
        )
        self._handle_hooks: Dict[str, Callable] = {
            m.replace("handle_", ""): getattr(handler, m)
            for m in dir(handler)
            if m.startswith("handle_")
        }

        # When we've deprecated the 4-arg form of handle_EHLO,
        # we can -- and should -- remove this whole code block
        ehlo_hook = self._handle_hooks.get("EHLO")
        if ehlo_hook is None:
            self._ehlo_hook_ver = None
        else:
            ehlo_hook_params = inspect.signature(ehlo_hook).parameters
            if len(ehlo_hook_params) == 4:
                self._ehlo_hook_ver = "old"
                warn("Use the 5-argument handle_EHLO() hook instead of "
                     "the 4-argument handle_EHLO() hook; "
                     "support for the 4-argument handle_EHLO() hook will be "
                     "removed in version 2.0",
                     DeprecationWarning)
            elif len(ehlo_hook_params) == 5:
                self._ehlo_hook_ver = "new"
            else:
                raise RuntimeError("Unsupported EHLO Hook")

        self._smtp_methods: Dict[str, Any] = {
            m.replace("smtp_", ""): getattr(self, m)
            for m in dir(self)
            if m.startswith("smtp_")
        }

        self._call_limit_default: int
        if command_call_limit is None:
            self._enforce_call_limit = False
        else:
            self._enforce_call_limit = True
            if isinstance(command_call_limit, int):
                self._call_limit_base = {}
                self._call_limit_default = command_call_limit
            elif isinstance(command_call_limit, dict):
                if not all(map(is_int, command_call_limit.values())):
                    raise TypeError("All command_call_limit values must be int")
                self._call_limit_base = command_call_limit
                self._call_limit_default = command_call_limit.get(
                    "*", CALL_LIMIT_DEFAULT
                )
            else:
                raise TypeError("command_call_limit must be int or Dict[str, int]")

    def _create_session(self) -> Session:
        return Session(self.loop)

    def _create_envelope(self) -> Envelope:
        return Envelope()

    async def _call_handler_hook(self, command: str, *args) -> Any:
        hook = self._handle_hooks.get(command)
        if hook is None:
            return MISSING
        status = await hook(self, self.session, self.envelope, *args)
        return status

    @property
    def max_command_size_limit(self) -> int:
        try:
            return max(self.command_size_limits.values())
        except ValueError:
            return self.command_size_limit

    def __del__(self):  # pragma: nocover
        # This is nocover-ed because the contents *totally* does NOT affect function-
        # ality, and in addition this comes directly from StreamReaderProtocol.__del__()
        # but with a getattr()+check addition to stop the annoying (but harmless)
        # "exception ignored" messages caused by AttributeError when self._closed is
        # missing (which seems to happen randomly).
        closed = getattr(self, "_closed", None)
        if closed is None:
            return
        if closed.done() and not closed.cancelled():
            closed.exception()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        # Reset state due to rfc3207 part 4.2.
        self._set_rset_state()
        self.session = self._create_session()
        self.session.peer = transport.get_extra_info('peername')
        self._reset_timeout()
        seen_starttls = (self._original_transport is not None)
        if self.transport is not None and seen_starttls:
            # It is STARTTLS connection over normal connection.
            self._reader._transport = transport  # type: ignore[attr-defined]
            self._writer._transport = transport  # type: ignore[attr-defined]
            self.transport = transport
            # Discard any leftover unencrypted data
            # See https://tools.ietf.org/html/rfc3207#page-7
            self._reader._buffer.clear()  # type: ignore[attr-defined]
            # Do SSL certificate checking as rfc3207 part 4.1 says.  Why is
            # _extra a protected attribute?
            assert self._tls_protocol is not None
            self.session.ssl = self._tls_protocol._extra
            hook = self._handle_hooks.get("STARTTLS")
            if hook is None:
                self._tls_handshake_okay = True
            else:
                self._tls_handshake_okay = hook(
                    self, self.session, self.envelope)
        else:
            super().connection_made(transport)
            self.transport = transport
            log.info('Peer: %r', self.session.peer)
            # Process the client's requests.
            self._handler_coroutine = self.loop.create_task(
                self._handle_client())

    def connection_lost(self, error: Optional[Exception]) -> None:
        assert self.session is not None
        log.info('%r connection lost', self.session.peer)
        assert self._timeout_handle is not None
        self._timeout_handle.cancel()
        # If STARTTLS was issued, then our transport is the SSL protocol
        # transport, and we need to close the original transport explicitly,
        # otherwise an unexpected eof_received() will be called *after* the
        # connection_lost().  At that point the stream reader will already be
        # destroyed and we'll get a traceback in super().eof_received() below.
        if self._original_transport is not None:
            self._original_transport.close()
        super().connection_lost(error)
        assert self._handler_coroutine is not None
        self._handler_coroutine.cancel()
        self.transport = None

    def eof_received(self) -> Optional[bool]:
        assert self.session is not None
        log.info('%r EOF received', self.session.peer)
        assert self._handler_coroutine is not None
        self._handler_coroutine.cancel()
        if self.session.ssl is not None:
            # If STARTTLS was issued, return False, because True has no effect
            # on an SSL transport and raises a warning. Our superclass has no
            # way of knowing we switched to SSL so it might return True.
            return False
        return super().eof_received()

    def _reset_timeout(self, duration: Optional[float] = None) -> None:
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
        self._timeout_handle = self.loop.call_later(
            duration or self._timeout_duration, self._timeout_cb
        )

    def _timeout_cb(self):
        assert self.session is not None
        log.info('%r connection timeout', self.session.peer)

        # Calling close() on the transport will trigger connection_lost(),
        # which gracefully closes the SSL transport if required and cleans
        # up state.
        assert self.transport is not None
        self.transport.close()

    def _cb_client_connected(
            self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        # This is redundant since we subclass StreamReaderProtocol, but I like
        # the shorter names.
        self._reader = reader
        self._writer = writer

    def _set_post_data_state(self):
        """Reset state variables to their post-DATA state."""
        self.envelope = self._create_envelope()

    def _set_rset_state(self):
        """Reset all state variables except the greeting."""
        self._set_post_data_state()

    async def push(self, status: AnyStr):
        if isinstance(status, str):
            response = bytes(
                status, 'utf-8' if self.enable_SMTPUTF8 else 'ascii')
        else:
            response = status
        assert isinstance(response, bytes)
        self._writer.write(response + b"\r\n")
        assert self.session is not None
        log.debug("%r << %r", self.session.peer, response)
        await self._writer.drain()

    async def handle_exception(self, error: Exception) -> str:
        if hasattr(self.event_handler, 'handle_exception'):
            status = await self.event_handler.handle_exception(error)
            return status
        else:
            assert self.session is not None
            log.exception('%r SMTP session exception', self.session.peer)
            status = '500 Error: ({}) {}'.format(
                error.__class__.__name__, str(error))
            return status

    async def _handle_client(self) -> None:
        assert self.session is not None
        log.info('%r handling connection', self.session.peer)

        if self._proxy_timeout is not None:
            self._reset_timeout(self._proxy_timeout)
            log.debug("%r waiting PROXY handshake", self.session.peer)
            self.session.proxy_data = await get_proxy(self._reader)
            if self.session.proxy_data:
                log.info("%r valid PROXY handshake", self.session.peer)
                status = await self._call_handler_hook("PROXY", self.session.proxy_data)
                log.debug("%r handle_PROXY returned %r", self.session.peer, status)
            else:
                log.warning("%r invalid PROXY handshake", self.session.peer)
                status = False
            if status is MISSING or not status:
                log.info("%r rejected by handle_PROXY", self.session.peer)
                assert self.transport is not None
                self.transport.close()
                return
            self._reset_timeout()

        await self.push('220 {} {}'.format(self.hostname, self.__ident__))
        if self._enforce_call_limit:
            call_limit: MutableMapping[str, int] = collections.defaultdict(
                lambda: self._call_limit_default,
                self._call_limit_base
            )
        else:
            # Not used, but this silences code inspection tools
            call_limit = {}
        bogus_budget = BOGUS_LIMIT

        while self.transport is not None:   # pragma: nobranch
            try:
                try:
                    line: bytes = await self._reader.readuntil()
                except asyncio.LimitOverrunError as error:
                    # Line too long. Read until end of line before sending 500.
                    await self._reader.read(error.consumed)
                    while True:
                        try:
                            await self._reader.readuntil()
                            break
                        except asyncio.LimitOverrunError as e:
                            # Line is even longer...
                            await self._reader.read(e.consumed)
                            continue
                    # Now that we have read a full line from the client,
                    # send error response and read the next command line.
                    await self.push('500 Command line too long')
                    continue
                sanitized_log(log.debug, '_handle_client readline: %r', line)
                # XXX this rstrip may not completely preserve old behavior.
                line = line.rstrip(b'\r\n')
                sanitized_log(log.info, '%r >> %r', self.session.peer, line)
                if not line:
                    await self.push('500 Error: bad syntax')
                    continue
                command_bytes, _, arg_bytes = line.partition(b" ")
                # Decode to string only the command name part, which must be
                # ASCII as per RFC.  If there is an argument, it is decoded to
                # UTF-8/surrogateescape so that non-UTF-8 data can be
                # re-encoded back to the original bytes when the SMTP command
                # is handled.
                try:
                    command = command_bytes.upper().decode(encoding='ascii')
                except UnicodeDecodeError:
                    await self.push('500 Error: bad syntax')
                    continue
                if not arg_bytes:
                    arg: Optional[str] = None
                else:
                    arg_bytes = arg_bytes.strip()
                    # Remote SMTP servers can send us UTF-8 content despite
                    # whether they've declared to do so or not.  Some old
                    # servers can send 8-bit data.  Use surrogateescape so
                    # that the fidelity of the decoding is preserved, and the
                    # original bytes can be retrieved.
                    if self.enable_SMTPUTF8:
                        arg = str(
                            arg_bytes, encoding='utf-8', errors='surrogateescape')
                    else:
                        try:
                            arg = str(arg_bytes, encoding='ascii', errors='strict')
                        except UnicodeDecodeError:
                            # This happens if enable_SMTPUTF8 is false, meaning
                            # that the server explicitly does not want to
                            # accept non-ASCII, but the client ignores that and
                            # sends non-ASCII anyway.
                            await self.push('500 Error: strict ASCII mode')
                            # Should we await self.handle_exception()?
                            continue
                max_sz = (
                    self.command_size_limits[command]
                    if self.session.extended_smtp
                    else self.command_size_limit
                )
                if len(line) > max_sz:
                    await self.push('500 Command line too long')
                    continue
                if not self._tls_handshake_okay and command != 'QUIT':
                    await self.push(
                        '554 Command refused due to lack of security')
                    continue
                if (self.require_starttls
                        and not self._tls_protocol
                        and command not in ALLOWED_BEFORE_STARTTLS):
                    # RFC3207 part 4
                    await self.push('530 Must issue a STARTTLS command first')
                    continue

                if self._enforce_call_limit:
                    budget = call_limit[command]
                    if budget < 1:
                        log.warning(
                            "%r over limit for %s", self.session.peer, command
                        )
                        await self.push(
                            f"421 4.7.0 {command} sent too many times"
                        )
                        self.transport.close()
                        continue
                    call_limit[command] = budget - 1

                method = self._smtp_methods.get(command)
                if method is None:
                    log.warning("%r unrecognised: %s", self.session.peer, command)
                    bogus_budget -= 1
                    if bogus_budget < 1:
                        log.warning("%r too many bogus commands", self.session.peer)
                        await self.push(
                            "502 5.5.1 Too many unrecognized commands, goodbye."
                        )
                        self.transport.close()
                        continue
                    await self.push(
                        f'500 Error: command "{command}" not recognized'
                    )
                    continue

                # Received a valid command, reset the timer.
                self._reset_timeout()
                await method(arg)
            except asyncio.CancelledError:
                # The connection got reset during the DATA command.
                # XXX If handler method raises ConnectionResetError, we should
                # verify that it was actually self._reader that was reset.
                log.info('%r Connection lost during _handle_client()',
                         self.session.peer)
                self._writer.close()
                raise
            except ConnectionResetError:
                log.info('%r Connection lost during _handle_client()',
                         self.session.peer)
                self._writer.close()
                raise
            except Exception as error:
                status = None
                try:
                    status = await self.handle_exception(error)
                except Exception as inner_error:
                    try:
                        log.exception('%r Exception in handle_exception()',
                                      self.session.peer)
                        status = '500 Error: ({}) {}'.format(
                            inner_error.__class__.__name__, str(inner_error))
                    except Exception:
                        status = '500 Error: Cannot describe error'
                finally:
                    if isinstance(error, TLSSetupException):
                        # This code branch is inside None check for self.transport
                        # so there shouldn't be a None self.transport but pytype
                        # still complains, so silence that error.
                        self.transport.close()  # pytype: disable=attribute-error
                        self.connection_lost(error)
                    else:
                        # The value of status is being set with ex-except and it
                        # shouldn't be None, but pytype isn't able to infer that
                        # so ignore the error related to wrong argument types.
                        await self.push(status)  # pytype: disable=wrong-arg-types

    async def check_helo_needed(self, helo: str = "HELO") -> bool:
        """
        Check if HELO/EHLO is needed.

        :param helo: The actual string of HELO/EHLO
        :return: True if HELO/EHLO is needed
        """
        assert self.session is not None
        if not self.session.host_name:
            await self.push(f'503 Error: send {helo} first')
            return True
        return False

    async def check_auth_needed(self, caller_method: str) -> bool:
        """
        Check if AUTH is needed.

        :param caller_method: The SMTP method needing a check (for logging)
        :return: True if AUTH is needed
        """
        assert self.session is not None
        if self._auth_required and not self.session.authenticated:
            log.info(f'{caller_method}: Authentication required')
            await self.push('530 5.7.0 Authentication required')
            return True
        return False

    # SMTP and ESMTP commands
    @syntax('HELO hostname')
    async def smtp_HELO(self, hostname: str):
        if not hostname:
            await self.push('501 Syntax: HELO hostname')
            return
        self._set_rset_state()
        assert self.session is not None
        self.session.extended_smtp = False
        status = await self._call_handler_hook('HELO', hostname)
        if status is MISSING:
            self.session.host_name = hostname
            status = '250 {}'.format(self.hostname)
        await self.push(status)

    @syntax('EHLO hostname')
    async def smtp_EHLO(self, hostname: str):
        if not hostname:
            await self.push('501 Syntax: EHLO hostname')
            return

        response = ['250-' + self.hostname, ]
        self._set_rset_state()
        assert self.session is not None
        self.session.extended_smtp = True
        if self.data_size_limit:
            response.append(f'250-SIZE {self.data_size_limit}')
            self.command_size_limits['MAIL'] += 26
        if not self._decode_data:
            response.append('250-8BITMIME')
        if self.enable_SMTPUTF8:
            response.append('250-SMTPUTF8')
            self.command_size_limits['MAIL'] += 10
        if self.tls_context and not self._tls_protocol:
            response.append('250-STARTTLS')
        if not self._auth_require_tls or self._tls_protocol:
            response.append(
                "250-AUTH " + " ".join(sorted(self._auth_methods.keys()))
            )

        if hasattr(self, 'ehlo_hook'):
            warn('Use handler.handle_EHLO() instead of .ehlo_hook()',
                 DeprecationWarning)
            await self.ehlo_hook()

        if self._ehlo_hook_ver is None:
            self.session.host_name = hostname
            response.append('250 HELP')
        elif self._ehlo_hook_ver == "old":
            # Old behavior: Send all responses first...
            for r in response:
                await self.push(r)
            # ... then send the response from the hook.
            response = [await self._call_handler_hook("EHLO", hostname)]
            # (The hook might internally send its own responses.)
        elif self._ehlo_hook_ver == "new":  # pragma: nobranch
            # New behavior: hand over list of responses so far to the hook, and
            # REPLACE existing list of responses with what the hook returns.
            # We will handle the push()ing
            response.append('250 HELP')
            response = await self._call_handler_hook("EHLO", hostname, response)

        for r in response:
            await self.push(r)

    @syntax('NOOP [ignored]')
    async def smtp_NOOP(self, arg: str):
        status = await self._call_handler_hook('NOOP', arg)
        await self.push('250 OK' if status is MISSING else status)

    @syntax('QUIT')
    async def smtp_QUIT(self, arg: str):
        if arg:
            await self.push('501 Syntax: QUIT')
        else:
            status = await self._call_handler_hook('QUIT')
            await self.push('221 Bye' if status is MISSING else status)
            assert self._handler_coroutine is not None
            self._handler_coroutine.cancel()
            assert self.transport is not None
            self.transport.close()

    @syntax('STARTTLS', when='tls_context')
    async def smtp_STARTTLS(self, arg: str):
        if arg:
            await self.push('501 Syntax: STARTTLS')
            return
        if not self.tls_context:
            await self.push('454 TLS not available')
            return
        await self.push('220 Ready to start TLS')
        # Create a waiter Future to wait for SSL handshake to complete
        waiter = self.loop.create_future()
        # Create SSL layer.
        # noinspection PyTypeChecker
        self._tls_protocol = sslproto.SSLProtocol(
            self.loop,
            self,
            self.tls_context,
            waiter,
            server_side=True)

        # Reconfigure transport layer.  Keep a reference to the original
        # transport so that we can close it explicitly when the connection is
        # lost.
        self._original_transport = self.transport
        assert self._original_transport is not None
        self._original_transport.set_protocol(self._tls_protocol)
        # Reconfigure the protocol layer.  Why is the app transport a protected
        # property, if it MUST be used externally?
        self.transport = self._tls_protocol._app_transport
        self._tls_protocol.connection_made(self._original_transport)
        # wait until handshake complete
        try:
            await waiter
        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise TLSSetupException() from error

    @syntax("AUTH <mechanism>")
    async def smtp_AUTH(self, arg: str) -> None:
        if await self.check_helo_needed("EHLO"):
            return
        assert self.session is not None
        if not self.session.extended_smtp:
            await self.push("500 Error: command 'AUTH' not recognized")
            return
        elif self._auth_require_tls and not self._tls_protocol:
            await self.push("538 5.7.11 Encryption required for requested "
                            "authentication mechanism")
            return
        elif self.session.authenticated:
            await self.push('503 Already authenticated')
            return
        elif not arg:
            await self.push('501 Not enough value')
            return

        args = arg.split()
        if len(args) > 2:
            await self.push('501 Too many values')
            return

        mechanism = args[0]
        if mechanism not in self._auth_methods:
            await self.push('504 5.5.4 Unrecognized authentication type')
            return

        CODE_SUCCESS = "235 2.7.0 Authentication successful"
        CODE_INVALID = "535 5.7.8 Authentication credentials invalid"
        status = await self._call_handler_hook('AUTH', args)
        if status is MISSING:
            auth_method = self._auth_methods[mechanism]
            log.debug(
                "Using %s auth_ hook for %r",
                "builtin" if auth_method.is_builtin else "handler",
                mechanism
            )
            # Pass 'self' to method so external methods can leverage this
            # class's helper methods such as push()
            auth_result = await auth_method.method(self, args)
            log.debug("auth_%s returned %r", mechanism, auth_result)

            # New system using `authenticator` and AuthResult
            if isinstance(auth_result, AuthResult):
                if auth_result.success:
                    self.session.authenticated = True
                    _auth_data = auth_result.auth_data
                    self.session.auth_data = _auth_data
                    # Custom mechanisms might not implement the "login" attribute, and
                    # that's okay.
                    self.session.login_data = getattr(_auth_data, "login", None)
                    status = auth_result.message or CODE_SUCCESS
                else:
                    if auth_result.handled:
                        status = None
                    elif auth_result.message:
                        status = auth_result.message
                    else:
                        status = CODE_INVALID

            # Old system using `auth_callback` and _TriState
            elif auth_result is None:
                # None means there's an error already handled by method and
                # we don't need to do anything more
                status = None
            elif auth_result is MISSING or auth_result is False:
                # MISSING means no error in AUTH process, but credentials
                # is rejected / not valid
                status = CODE_INVALID
            else:
                self.session.login_data = auth_result
                status = CODE_SUCCESS

        if status is not None:  # pragma: no branch
            await self.push(status)

    async def challenge_auth(
        self,
        challenge: Union[str, bytes],
        encode_to_b64: bool = True,
        log_client_response: bool = False,
    ) -> Union[_Missing, bytes]:
        """
        Send challenge during authentication. "334 " will be prefixed, so do NOT
        put "334 " at start of server_message.

        :param challenge: Challenge to send to client. If str, will be utf8-encoded.
        :param encode_to_b64: If true, then perform Base64 encoding on challenge
        :param log_client_response: Perform logging of client's response.
            WARNING: Might cause leak of sensitive information! Do not turn on
            unless _absolutely_ necessary!
        :return: Response from client, or MISSING
        """
        challenge = (
            challenge.encode() if isinstance(challenge, str) else challenge
        )
        assert isinstance(challenge, bytes)
        # Trailing space is MANDATORY even if challenge is empty.
        # See:
        #   - https://tools.ietf.org/html/rfc4954#page-4 ¶ 5
        #   - https://tools.ietf.org/html/rfc4954#page-13 "continue-req"
        challenge = b"334 " + (b64encode(challenge) if encode_to_b64 else challenge)
        assert self.session is not None
        log.debug("%r << challenge: %r", self.session.peer, challenge)
        await self.push(challenge)
        line = await self._reader.readline()      # pytype: disable=attribute-error
        if log_client_response:
            warn("AUTH interaction logging is enabled!")
            warn("Sensitive information might be leaked!")
            log.debug("%r >> %r", self.session.peer, line)
        blob: bytes = line.strip()
        # '*' handling in accordance with RFC4954
        if blob == b"*":
            log.warning("%r aborted AUTH with '*'", self.session.peer)
            await self.push("501 5.7.0 Auth aborted")
            return MISSING
        try:
            decoded_blob = b64decode(blob, validate=True)
        except binascii.Error:
            log.debug("%r can't decode base64: %s", self.session.peer, blob)
            await self.push("501 5.5.2 Can't decode base64")
            return MISSING
        return decoded_blob

    _334_PREFIX = re.compile(r"^334 ")

    async def _auth_interact(
            self,
            server_message: str
    ) -> Union[_Missing, bytes]:  # pragma: nocover
        warn(
            "_auth_interact will be deprecated in version 2.0. "
            "Please use challenge_auth() instead.",
            DeprecationWarning
        )
        return await self.challenge_auth(
            challenge=self._334_PREFIX.sub("", server_message),
            encode_to_b64=False,
        )

    def _authenticate(self, mechanism: str, auth_data: Any) -> AuthResult:
        if self._authenticator is not None:
            # self.envelope is likely still empty, but we'll pass it anyways to
            # make the invocation similar to the one in _call_handler_hook
            assert self.session is not None
            assert self.envelope is not None
            return self._authenticator(
                self, self.session, self.envelope, mechanism, auth_data
            )
        else:
            assert self._auth_callback is not None
            assert isinstance(auth_data, LoginPassword)
            if self._auth_callback(mechanism, *auth_data):
                return AuthResult(success=True, handled=True, auth_data=auth_data)
            else:
                return AuthResult(success=False, handled=False)

    # IMPORTANT NOTES FOR THE auth_* METHODS
    # ======================================
    # Please note that there are two systems for return values in #2.
    #
    # 1. For internal methods, due to how they are called, we must ignore the first arg
    # 2. (OLD SYSTEM) All auth_* methods can return one of three values:
    #    - None: An error happened and handled;
    #            smtp_AUTH should do nothing more
    #    - MISSING or False: Authentication failed, but not because of error
    #    - [Any]: Authentication succeeded and this is the 'identity' of
    #             the SMTP user
    #      - 'identity' is not always username, depending on the auth mecha-
    #        nism. Might be a session key, a one-time user ID, or any kind of
    #        object, actually.
    # 2. (NEW SYSTEM) All auth_* methods must return an AuthResult object.
    #    For explanation on the object's attributes,
    #    see the AuthResult class definition.
    # 3. Auth credentials checking is performed in the auth_* methods because
    #    more advanced auth mechanism might not return login+password pair
    #    (see #2 above)

    async def auth_PLAIN(self, _, args: List[str]) -> AuthResult:
        login_and_password: _TriStateType
        if len(args) == 1:
            login_and_password = await self.challenge_auth("")
            if login_and_password is MISSING:
                return AuthResult(success=False)
        else:
            try:
                login_and_password = b64decode(args[1].encode(), validate=True)
            except Exception:
                await self.push("501 5.5.2 Can't decode base64")
                return AuthResult(success=False, handled=True)
        try:
            # login data is "{authz_id}\x00{login_id}\x00{password}"
            # authz_id can be null, and currently ignored
            # See https://tools.ietf.org/html/rfc4616#page-3
            _, login, password = login_and_password.split(b"\x00")  # noqa: E501
        except ValueError:  # not enough args
            await self.push("501 5.5.2 Can't split auth value")
            return AuthResult(success=False, handled=True)
        # Verify login data
        assert login is not None
        assert password is not None
        return self._authenticate("PLAIN", LoginPassword(login, password))

    async def auth_LOGIN(self, _, args: List[str]) -> AuthResult:
        login: _TriStateType
        if len(args) == 1:
            # Client sent only "AUTH LOGIN"
            login = await self.challenge_auth(self.AuthLoginUsernameChallenge)
            if login is MISSING:
                return AuthResult(success=False)
        else:
            # Client sent "AUTH LOGIN <b64-encoded-username>"
            try:
                login = b64decode(args[1].encode(), validate=True)
            except Exception:
                await self.push("501 5.5.2 Can't decode base64")
                return AuthResult(success=False, handled=True)
        assert login is not None

        password: _TriStateType
        password = await self.challenge_auth(self.AuthLoginPasswordChallenge)
        if password is MISSING:
            return AuthResult(success=False)
        assert password is not None

        return self._authenticate("LOGIN", LoginPassword(login, password))

    def _strip_command_keyword(self, keyword: str, arg: str) -> Optional[str]:
        keylen = len(keyword)
        if arg[:keylen].upper() == keyword:
            return arg[keylen:].strip()
        return None

    def _getaddr(self, arg: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try to parse address given in SMTP command.

        Returns address=None if arg can't be parsed properly (get_angle_addr /
        get_addr_spec raised HeaderParseError)
        """

        class AddrSpec(Protocol):
            @property
            def addr_spec(self) -> str:
                ...

        if not arg:
            return '', ''
        address: AddrSpec
        try:
            if arg.lstrip().startswith('<'):
                address, rest = get_angle_addr(arg)
            else:
                address, rest = get_addr_spec(arg)
        except HeaderParseError:
            return None, None
        addr = address.addr_spec
        localpart, atsign, domainpart = addr.rpartition("@")
        if self.local_part_limit and len(localpart) > self.local_part_limit:
            return None, None
        return addr, rest

    def _getparams(
            self, params: Sequence[str]
    ) -> Optional[Dict[str, Union[str, bool]]]:
        # Return params as dictionary. Return None if not all parameters
        # appear to be syntactically valid according to RFC 1869.
        result: Dict[str, Union[str, bool]] = {}
        for param in params:
            param, eq, value = param.partition('=')
            if not param.isalnum() or eq and not value:
                return None
            result[param] = value if eq else True
        return result

    # noinspection PyUnresolvedReferences
    def _syntax_available(self, method: Callable) -> bool:
        if not hasattr(method, '__smtp_syntax__'):
            return False
        if method.__smtp_syntax_when__:  # type: ignore[attr-defined]
            return bool(getattr(self, method.__smtp_syntax_when__))  # type: ignore[attr-defined]
        return True

    @syntax('HELP [command]')
    async def smtp_HELP(self, arg: str) -> None:
        if await self.check_auth_needed("HELP"):
            return
        code = 250
        if arg:
            method = self._smtp_methods.get(arg.upper())
            if method and self._syntax_available(method):
                help_str = method.__smtp_syntax__
                assert self.session is not None
                if (self.session.extended_smtp
                        and method.__smtp_syntax_extended__):
                    help_str += method.__smtp_syntax_extended__
                await self.push('250 Syntax: ' + help_str)
                return
            code = 501
        commands = []
        for name, method in self._smtp_methods.items():
            if self._syntax_available(method):
                commands.append(name)
        commands.sort()
        await self.push(
            '{} Supported commands: {}'.format(code, ' '.join(commands)))

    @syntax('VRFY <address>')
    async def smtp_VRFY(self, arg: str) -> None:
        if await self.check_auth_needed("VRFY"):
            return
        if arg:
            address, params = self._getaddr(arg)
            if address is None:
                await self.push('502 Could not VRFY ' + arg)
            else:
                status = await self._call_handler_hook('VRFY', address)
                await self.push(
                    '252 Cannot VRFY user, but will accept message '
                    'and attempt delivery'
                    if status is MISSING else status)
        else:
            await self.push('501 Syntax: VRFY <address>')

    @syntax('MAIL FROM: <address>', extended=' [SP <mail-parameters>]')
    async def smtp_MAIL(self, arg: Optional[str]) -> None:
        if await self.check_helo_needed():
            return
        if await self.check_auth_needed("MAIL"):
            return
        syntaxerr = '501 Syntax: MAIL FROM: <address>'
        assert self.session is not None
        if self.session.extended_smtp:
            syntaxerr += ' [SP <mail-parameters>]'
        if arg is None:
            await self.push(syntaxerr)
            return
        arg = self._strip_command_keyword('FROM:', arg)
        if arg is None:
            await self.push(syntaxerr)
            return
        address, addrparams = self._getaddr(arg)
        if address is None:
            await self.push("553 5.1.3 Error: malformed address")
            return
        if not address:
            await self.push(syntaxerr)
            return
        if not self.session.extended_smtp and addrparams:
            await self.push(syntaxerr)
            return
        assert self.envelope is not None
        if self.envelope.mail_from:
            await self.push('503 Error: nested MAIL command')
            return
        assert addrparams is not None
        mail_options = addrparams.upper().split()
        params = self._getparams(mail_options)
        if params is None:
            await self.push(syntaxerr)
            return
        if not self._decode_data:
            body = params.pop('BODY', '7BIT')
            if body not in ['7BIT', '8BITMIME']:
                await self.push(
                    '501 Error: BODY can only be one of 7BIT, 8BITMIME')
                return
        smtputf8 = params.pop('SMTPUTF8', False)
        if not isinstance(smtputf8, bool):
            await self.push('501 Error: SMTPUTF8 takes no arguments')
            return
        if smtputf8 and not self.enable_SMTPUTF8:
            await self.push('501 Error: SMTPUTF8 disabled')
            return
        self.envelope.smtp_utf8 = smtputf8
        size = params.pop('SIZE', None)
        if size:
            if isinstance(size, bool) or not size.isdigit():
                await self.push(syntaxerr)
                return
            elif self.data_size_limit and int(size) > self.data_size_limit:
                await self.push(
                    '552 Error: message size exceeds fixed maximum message '
                    'size')
                return
        if len(params) > 0:
            await self.push(
                '555 MAIL FROM parameters not recognized or not implemented')
            return
        status = await self._call_handler_hook('MAIL', address, mail_options)
        if status is MISSING:
            self.envelope.mail_from = address
            self.envelope.mail_options.extend(mail_options)
            status = '250 OK'
        log.info('%r sender: %s', self.session.peer, address)
        await self.push(status)

    @syntax('RCPT TO: <address>', extended=' [SP <mail-parameters>]')
    async def smtp_RCPT(self, arg: Optional[str]) -> None:
        if await self.check_helo_needed():
            return
        if await self.check_auth_needed("RCPT"):
            return
        assert self.envelope is not None
        if not self.envelope.mail_from:
            await self.push("503 Error: need MAIL command")
            return

        syntaxerr = '501 Syntax: RCPT TO: <address>'
        assert self.session is not None
        if self.session.extended_smtp:
            syntaxerr += ' [SP <mail-parameters>]'
        if arg is None:
            await self.push(syntaxerr)
            return
        arg = self._strip_command_keyword('TO:', arg)
        if arg is None:
            await self.push(syntaxerr)
            return
        address, params = self._getaddr(arg)
        if address is None:
            await self.push("553 5.1.3 Error: malformed address")
            return
        if not address:
            await self.push(syntaxerr)
            return
        if not self.session.extended_smtp and params:
            await self.push(syntaxerr)
            return
        assert params is not None
        rcpt_options = params.upper().split()
        params_dict = self._getparams(rcpt_options)
        if params_dict is None:
            await self.push(syntaxerr)
            return
        # XXX currently there are no options we recognize.
        if len(params_dict) > 0:
            await self.push(
                '555 RCPT TO parameters not recognized or not implemented'
            )
            return

        status = await self._call_handler_hook('RCPT', address, rcpt_options)
        if status is MISSING:
            self.envelope.rcpt_tos.append(address)
            self.envelope.rcpt_options.extend(rcpt_options)
            status = '250 OK'
        log.info('%r recip: %s', self.session.peer, address)
        await self.push(status)

    @syntax('RSET')
    async def smtp_RSET(self, arg: str):
        if arg:
            await self.push('501 Syntax: RSET')
            return
        self._set_rset_state()
        if hasattr(self, 'rset_hook'):
            warn('Use handler.handle_RSET() instead of .rset_hook()',
                 DeprecationWarning)
            await self.rset_hook()
        status = await self._call_handler_hook('RSET')
        await self.push('250 OK' if status is MISSING else status)

    @syntax('DATA')
    async def smtp_DATA(self, arg: str) -> None:
        if await self.check_helo_needed():
            return
        if await self.check_auth_needed("DATA"):
            return
        assert self.envelope is not None
        if not self.envelope.rcpt_tos:
            await self.push('503 Error: need RCPT command')
            return
        if arg:
            await self.push('501 Syntax: DATA')
            return

        await self.push('354 End data with <CR><LF>.<CR><LF>')
        data: List[bytearray] = []

        num_bytes: int = 0
        limit: Optional[int] = self.data_size_limit
        line_fragments: List[bytes] = []
        state: _DataState = _DataState.NOMINAL
        while self.transport is not None:           # pragma: nobranch
            # Since eof_received cancels this coroutine,
            # readuntil() can never raise asyncio.IncompleteReadError.
            try:
                # https://datatracker.ietf.org/doc/html/rfc5321#section-2.3.8
                line: bytes = await self._reader.readuntil(b'\r\n')
                log.debug('DATA readline: %s', line)
                assert line.endswith(b'\r\n')
            except asyncio.CancelledError:
                # The connection got reset during the DATA command.
                log.info('Connection lost during DATA')
                self._writer.close()
                raise
            except asyncio.LimitOverrunError as e:
                # The line exceeds StreamReader's "stream limit".
                # Delay SMTP Status Code sending until data receive is complete
                # This seems to be implied in RFC 5321 § 4.2.5
                if state == _DataState.NOMINAL:
                    # Transition to TOO_LONG only if we haven't gone TOO_MUCH yet
                    state = _DataState.TOO_LONG
                # Discard data immediately to prevent memory pressure
                data *= 0
                # Drain the stream anyways
                line = await self._reader.read(e.consumed)
                assert not line.endswith(b'\r\n')
            # A lone dot in a line signals the end of DATA.
            if not line_fragments and line == b'.\r\n':
                break
            num_bytes += len(line)
            if state == _DataState.NOMINAL and limit and num_bytes > limit:
                # Delay SMTP Status Code sending until data receive is complete
                # This seems to be implied in RFC 5321 § 4.2.5
                state = _DataState.TOO_MUCH
                # Discard data immediately to prevent memory pressure
                data *= 0
            line_fragments.append(line)
            if line.endswith(b'\r\n'):
                # Record data only if state is "NOMINAL"
                if state == _DataState.NOMINAL:
                    line = EMPTY_BARR.join(line_fragments)
                    if len(line) > self.line_length_limit:
                        # Theoretically we shouldn't reach this place. But it's always
                        # good to practice DEFENSIVE coding.
                        state = _DataState.TOO_LONG
                        # Discard data immediately to prevent memory pressure
                        data *= 0
                    else:
                        data.append(EMPTY_BARR.join(line_fragments))
                line_fragments *= 0

        # Day of reckoning! Let's take care of those out-of-nominal situations
        if state != _DataState.NOMINAL:
            if state == _DataState.TOO_LONG:
                await self.push("500 Line too long (see RFC5321 4.5.3.1.6)")
            elif state == _DataState.TOO_MUCH:  # pragma: nobranch
                await self.push('552 Error: Too much mail data')
            self._set_post_data_state()
            return

        # If unfinished_line is non-empty, then the connection was closed.
        assert not line_fragments

        # Remove extraneous carriage returns and de-transparency
        # according to RFC 5321, Section 4.5.2.
        for text in data:
            if text.startswith(b'.'):
                del text[0]
        original_content: bytes = EMPTYBYTES.join(data)
        # Discard data immediately to prevent memory pressure
        data *= 0

        content: Union[str, bytes]
        if self._decode_data:
            if self.enable_SMTPUTF8:
                content = original_content.decode('utf-8', errors='surrogateescape')
            else:
                try:
                    content = original_content.decode('ascii', errors='strict')
                except UnicodeDecodeError:
                    # This happens if enable_smtputf8 is false, meaning that
                    # the server explicitly does not want to accept non-ascii,
                    # but the client ignores that and sends non-ascii anyway.
                    await self.push('500 Error: strict ASCII mode')
                    return
        else:
            content = original_content
        self.envelope.content = content
        self.envelope.original_content = original_content

        # Call the new API first if it's implemented.
        if "DATA" in self._handle_hooks:
            status = await self._call_handler_hook('DATA')
        else:
            # Backward compatibility.
            status = MISSING
            if hasattr(self.event_handler, 'process_message'):
                warn('Use handler.handle_DATA() instead of .process_message()',
                     DeprecationWarning)
                assert self.session is not None
                args = (self.session.peer, self.envelope.mail_from,
                        self.envelope.rcpt_tos, self.envelope.content)
                if asyncio.iscoroutinefunction(
                        self.event_handler.process_message):
                    status = await self.event_handler.process_message(*args)
                else:
                    status = self.event_handler.process_message(*args)
                # The deprecated API can return None which means, return the
                # default status.  Don't worry about coverage for this case as
                # it's a deprecated API that will go away after 1.0.
                if status is None:                  # pragma: nocover
                    status = MISSING
        self._set_post_data_state()
        await self.push('250 OK' if status is MISSING else status)

    # Commands that have not been implemented.
    async def smtp_EXPN(self, arg: str):
        await self.push('502 EXPN not implemented')
