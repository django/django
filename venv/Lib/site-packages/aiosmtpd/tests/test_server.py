# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

"""Test other aspects of the server implementation."""

import asyncio
import errno
import platform
import socket
import sys
import time
from contextlib import ExitStack
from functools import partial
from threading import Event
from pathlib import Path
from smtplib import SMTP as SMTPClient, SMTPServerDisconnected
from tempfile import mkdtemp
from threading import Thread
from typing import Generator, Optional

import pytest
from pytest_mock import MockFixture

from aiosmtpd.controller import (
    Controller,
    UnixSocketController,
    UnthreadedController,
    UnixSocketMixin,
    UnixSocketUnthreadedController,
    _FakeServer,
    get_localhost,
    _server_to_client_ssl_ctx,
)
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import SMTP as Server
from aiosmtpd.testing.helpers import catchup_delay

from .conftest import Global, AUTOSTOP_DELAY


class SlowStartController(Controller):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("ready_timeout", 0.5)
        super().__init__(*args, **kwargs)

    def _run(self, ready_event: Event):
        time.sleep(self.ready_timeout * 1.5)
        super()._run(ready_event)


class SlowFactoryController(Controller):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("ready_timeout", 0.5)
        super().__init__(*args, **kwargs)

    def factory(self):
        time.sleep(self.ready_timeout * 3)
        return super().factory()

    def _factory_invoker(self):
        time.sleep(self.ready_timeout * 3)
        return super()._factory_invoker()


def in_win32():
    return platform.system().casefold() == "windows"


def in_wsl():
    # WSL 1.0 somehow allows more than one listener on one port.
    # So we have to detect when we're running on WSL so we can skip some tests.

    # On Windows, platform.release() returns the Windows version (e.g., "7" or "10")
    # On Linux (incl. WSL), platform.release() returns the kernel version.
    # As of 2021-02-07, only WSL has a kernel with "Microsoft" in the version.
    return "microsoft" in platform.release().casefold()


def in_cygwin():
    return platform.system().casefold().startswith("cygwin")


@pytest.fixture(scope="module")
def safe_socket_dir() -> Generator[Path, None, None]:
    # See:
    #   - https://github.com/aio-libs/aiohttp/issues/3572
    #   - https://github.com/aio-libs/aiohttp/pull/3832/files
    #   - https://unix.stackexchange.com/a/367012/5589
    tmpdir = Path(mkdtemp()).absolute()
    assert len(str(tmpdir)) <= 87  # 92 (max on HP-UX) minus 5 (allow 4-char fn)
    #
    yield tmpdir
    #
    plist = list(tmpdir.rglob("*"))
    for p in reversed(plist):
        if p.is_dir():
            p.rmdir()
        else:
            p.unlink()
    tmpdir.rmdir()


def assert_smtp_socket(controller: UnixSocketMixin) -> bool:
    assert Path(controller.unix_socket).exists()
    sockfile = controller.unix_socket
    if controller.ssl_context:
        ssl_context = _server_to_client_ssl_ctx(controller.ssl_context)
    else:
        ssl_context = None
    with ExitStack() as stk:
        sock: socket.socket = stk.enter_context(
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        )
        sock.settimeout(AUTOSTOP_DELAY)
        sock.connect(str(sockfile))
        if ssl_context:
            sock = stk.enter_context(ssl_context.wrap_socket(sock))
        catchup_delay()
        try:
            resp = sock.recv(1024)
        except socket.timeout:
            return False
        if not resp:
            return False
        assert resp.startswith(b"220 ")
        assert resp.endswith(b"\r\n")
        sock.send(b"EHLO socket.test\r\n")
        # We need to "build" resparr because, especially when socket is wrapped
        # in SSL, the SMTP server takes it sweet time responding with the list
        # of ESMTP features ...
        resparr = bytearray()
        while not resparr.endswith(b"250 HELP\r\n"):
            catchup_delay()
            resp = sock.recv(1024)
            if not resp:
                break
            resparr += resp
        assert resparr.endswith(b"250 HELP\r\n")
        sock.send(b"QUIT\r\n")
        catchup_delay()
        resp = sock.recv(1024)
        assert resp.startswith(b"221")
    return True


class TestServer:
    """Tests for the aiosmtpd.smtp.SMTP class"""

    def test_smtp_utf8(self, plain_controller, client):
        code, mesg = client.ehlo("example.com")
        assert code == 250
        assert b"SMTPUTF8" in mesg.splitlines()

    def test_default_max_command_size_limit(self):
        server = Server(Sink())
        assert server.max_command_size_limit == 512

    def test_special_max_command_size_limit(self):
        server = Server(Sink())
        server.command_size_limits["DATA"] = 1024
        assert server.max_command_size_limit == 1024

    def test_warn_authreq_notls(self):
        expectedre = (
            r"Requiring AUTH while not requiring TLS can lead to "
            r"security vulnerabilities!"
        )
        with pytest.warns(UserWarning, match=expectedre):
            Server(Sink(), auth_require_tls=False, auth_required=True)


@pytest.mark.skipif(sys.platform == "win32", reason="No idea what is causing error")
class TestController:
    """Tests for the aiosmtpd.controller.Controller class"""

    @pytest.mark.filterwarnings("ignore")
    def test_ready_timeout(self):
        cont = SlowStartController(Sink())
        expectre = (
            "SMTP server failed to start within allotted time. "
            "This might happen if the system is too busy. "
            "Try increasing the `ready_timeout` parameter."
        )
        try:
            with pytest.raises(TimeoutError, match=expectre):
                cont.start()
        finally:
            cont.stop()

    @pytest.mark.filterwarnings("ignore")
    def test_factory_timeout(self):
        cont = SlowFactoryController(Sink())
        expectre = (
            r"SMTP server started, but not responding within allotted time. "
            r"This might happen if the system is too busy. "
            r"Try increasing the `ready_timeout` parameter."
        )
        try:
            with pytest.raises(TimeoutError, match=expectre):
                cont.start()
        finally:
            cont.stop()

    def test_reuse_loop(self, temp_event_loop):
        cont = Controller(Sink(), loop=temp_event_loop)
        assert cont.loop is temp_event_loop
        try:
            cont.start()
            assert cont.smtpd.loop is temp_event_loop
        finally:
            cont.stop()

    @pytest.mark.skipif(in_wsl(), reason="WSL prevents socket collision")
    def test_socket_error_dupe(self, plain_controller, client):
        contr2 = Controller(
            Sink(), hostname=Global.SrvAddr.host, port=Global.SrvAddr.port
        )
        expectedre = r"error while attempting to bind on address"
        try:
            with pytest.raises(socket.error, match=expectedre):
                contr2.start()
        finally:
            contr2.stop()

    @pytest.mark.skipif(in_wsl(), reason="WSL prevents socket collision")
    def test_socket_error_default(self):
        contr1 = Controller(Sink())
        contr2 = Controller(Sink())
        expectedre = r"error while attempting to bind on address"
        try:
            with pytest.raises(socket.error, match=expectedre):
                contr1.start()
                contr2.start()
        finally:
            contr2.stop()
            contr1.stop()

    def test_server_attribute(self):
        controller = Controller(Sink())
        assert controller.server is None
        try:
            controller.start()
            assert controller.server is not None
        finally:
            controller.stop()
        assert controller.server is None

    @pytest.mark.filterwarnings(
        "ignore:server_kwargs will be removed:DeprecationWarning"
    )
    def test_enablesmtputf8_flag(self):
        # Default is True
        controller = Controller(Sink())
        assert controller.SMTP_kwargs["enable_SMTPUTF8"]
        # Explicit set must be reflected in server_kwargs
        controller = Controller(Sink(), enable_SMTPUTF8=True)
        assert controller.SMTP_kwargs["enable_SMTPUTF8"]
        controller = Controller(Sink(), enable_SMTPUTF8=False)
        assert not controller.SMTP_kwargs["enable_SMTPUTF8"]
        # Explicit set must override server_kwargs
        kwargs = dict(enable_SMTPUTF8=False)
        controller = Controller(Sink(), enable_SMTPUTF8=True, server_kwargs=kwargs)
        assert controller.SMTP_kwargs["enable_SMTPUTF8"]
        kwargs = dict(enable_SMTPUTF8=True)
        controller = Controller(Sink(), enable_SMTPUTF8=False, server_kwargs=kwargs)
        assert not controller.SMTP_kwargs["enable_SMTPUTF8"]
        # Set through server_kwargs must not be overridden if no explicit set
        kwargs = dict(enable_SMTPUTF8=False)
        controller = Controller(Sink(), server_kwargs=kwargs)
        assert not controller.SMTP_kwargs["enable_SMTPUTF8"]

    @pytest.mark.filterwarnings(
        "ignore:server_kwargs will be removed:DeprecationWarning"
    )
    def test_serverhostname_arg(self):
        contsink = partial(Controller, Sink())
        controller = contsink()
        assert "hostname" not in controller.SMTP_kwargs
        controller = contsink(server_hostname="testhost1")
        assert controller.SMTP_kwargs["hostname"] == "testhost1"
        kwargs = dict(hostname="testhost2")
        controller = contsink(server_kwargs=kwargs)
        assert controller.SMTP_kwargs["hostname"] == "testhost2"
        controller = contsink(server_hostname="testhost3", server_kwargs=kwargs)
        assert controller.SMTP_kwargs["hostname"] == "testhost3"

    def test_hostname_empty(self):
        # WARNING: This test _always_ succeeds in Windows.
        cont = Controller(Sink(), hostname="")
        try:
            cont.start()
        finally:
            cont.stop()

    def test_hostname_none(self):
        cont = Controller(Sink())
        try:
            cont.start()
        finally:
            cont.stop()

    def test_testconn_raises(self, mocker: MockFixture):
        mocker.patch("socket.socket.recv", side_effect=RuntimeError("MockError"))
        cont = Controller(Sink(), hostname="")
        try:
            with pytest.raises(RuntimeError, match="MockError"):
                cont.start()
        finally:
            cont.stop()

    def test_getlocalhost(self):
        assert get_localhost() in ("127.0.0.1", "::1")

    def test_getlocalhost_noipv6(self, mocker):
        mock_hasip6 = mocker.patch("aiosmtpd.controller._has_ipv6", return_value=False)
        assert get_localhost() == "127.0.0.1"
        assert mock_hasip6.called

    def test_getlocalhost_6yes(self, mocker: MockFixture):
        mock_sock = mocker.Mock()
        mock_makesock: mocker.Mock = mocker.patch("aiosmtpd.controller.makesock")
        mock_makesock.return_value.__enter__.return_value = mock_sock
        assert get_localhost() == "::1"
        mock_makesock.assert_called_with(socket.AF_INET6, socket.SOCK_STREAM)
        assert mock_sock.bind.called

    # Apparently errno.E* constants adapts to the OS, so on Windows they will
    # automatically use the analogous WSAE* constants
    @pytest.mark.parametrize("err", [errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT])
    def test_getlocalhost_6no(self, mocker, err):
        mock_makesock: mocker.Mock = mocker.patch(
            "aiosmtpd.controller.makesock",
            side_effect=OSError(errno.EADDRNOTAVAIL, "Mock IP4-only"),
        )
        assert get_localhost() == "127.0.0.1"
        mock_makesock.assert_called_with(socket.AF_INET6, socket.SOCK_STREAM)

    def test_getlocalhost_6inuse(self, mocker):
        mock_makesock: mocker.Mock = mocker.patch(
            "aiosmtpd.controller.makesock",
            side_effect=OSError(errno.EADDRINUSE, "Mock IP6 used"),
        )
        assert get_localhost() == "::1"
        mock_makesock.assert_called_with(socket.AF_INET6, socket.SOCK_STREAM)

    def test_getlocalhost_error(self, mocker):
        mock_makesock: mocker.Mock = mocker.patch(
            "aiosmtpd.controller.makesock",
            side_effect=OSError(errno.EFAULT, "Mock Error"),
        )
        with pytest.raises(OSError, match="Mock Error") as exc:
            get_localhost()
        assert exc.value.errno == errno.EFAULT
        mock_makesock.assert_called_with(socket.AF_INET6, socket.SOCK_STREAM)

    def test_stop_default(self):
        controller = Controller(Sink())
        with pytest.raises(AssertionError, match="SMTP daemon not running"):
            controller.stop()

    def test_stop_assert(self):
        controller = Controller(Sink())
        with pytest.raises(AssertionError, match="SMTP daemon not running"):
            controller.stop(no_assert=False)

    def test_stop_noassert(self):
        controller = Controller(Sink())
        controller.stop(no_assert=True)


@pytest.mark.skipif(in_cygwin(), reason="Cygwin AF_UNIX is problematic")
@pytest.mark.skipif(in_win32(), reason="Win32 does not yet fully implement AF_UNIX")
class TestUnixSocketController:
    def test_server_creation(self, safe_socket_dir):
        sockfile = safe_socket_dir / "smtp"
        cont = UnixSocketController(Sink(), unix_socket=sockfile)
        try:
            cont.start()
            assert_smtp_socket(cont)
        finally:
            cont.stop()

    def test_server_creation_ssl(self, safe_socket_dir, ssl_context_server):
        sockfile = safe_socket_dir / "smtp"
        cont = UnixSocketController(
            Sink(), unix_socket=sockfile, ssl_context=ssl_context_server
        )
        try:
            cont.start()
            # Allow additional time for SSL to kick in
            catchup_delay()
            assert_smtp_socket(cont)
        finally:
            cont.stop()


class TestUnthreaded:
    @pytest.fixture
    def runner(self):
        thread: Optional[Thread] = None

        def _runner(loop: asyncio.AbstractEventLoop):
            loop.run_forever()

        def starter(loop: asyncio.AbstractEventLoop):
            nonlocal thread
            thread = Thread(target=_runner, args=(loop,))
            thread.daemon = True
            thread.start()
            catchup_delay()

        def joiner(timeout: Optional[float] = None):
            nonlocal thread
            assert isinstance(thread, Thread)
            thread.join(timeout=timeout)

        def is_alive():
            nonlocal thread
            assert isinstance(thread, Thread)
            return thread.is_alive()

        starter.join = joiner
        starter.is_alive = is_alive
        return starter

    @pytest.mark.skipif(in_cygwin(), reason="Cygwin AF_UNIX is problematic")
    @pytest.mark.skipif(in_win32(), reason="Win32 does not yet fully implement AF_UNIX")
    def test_unixsocket(self, safe_socket_dir, autostop_loop, runner):
        sockfile = safe_socket_dir / "smtp"
        cont = UnixSocketUnthreadedController(
            Sink(), unix_socket=sockfile, loop=autostop_loop
        )
        cont.begin()
        # Make sure event loop is not running (will be started in thread)
        assert autostop_loop.is_running() is False
        runner(autostop_loop)
        # Make sure event loop is up and running (started within thread)
        assert autostop_loop.is_running() is True
        # Check we can connect
        assert_smtp_socket(cont)
        # Wait until thread ends, which it will be when the loop autostops
        runner.join(timeout=AUTOSTOP_DELAY)
        assert runner.is_alive() is False
        catchup_delay()
        assert autostop_loop.is_running() is False
        # At this point, the loop _has_ stopped, but the task is still listening
        assert assert_smtp_socket(cont) is False
        # Stop the task
        cont.end()
        catchup_delay()
        # Now the listener has gone away
        # noinspection PyTypeChecker
        with pytest.raises((socket.timeout, ConnectionError)):
            assert_smtp_socket(cont)

    @pytest.mark.filterwarnings(
        "ignore::pytest.PytestUnraisableExceptionWarning"
    )
    def test_inet_loopstop(self, autostop_loop, runner):
        """
        Verify behavior when the loop is stopped before controller is stopped
        """
        autostop_loop.set_debug(True)
        cont = UnthreadedController(Sink(), loop=autostop_loop)
        cont.begin()
        # Make sure event loop is not running (will be started in thread)
        assert autostop_loop.is_running() is False
        runner(autostop_loop)
        # Make sure event loop is up and running (started within thread)
        assert autostop_loop.is_running() is True
        # Check we can connect
        with SMTPClient(cont.hostname, cont.port, timeout=AUTOSTOP_DELAY) as client:
            code, _ = client.helo("example.org")
            assert code == 250
        # Wait until thread ends, which it will be when the loop autostops
        runner.join(timeout=AUTOSTOP_DELAY)
        assert runner.is_alive() is False
        catchup_delay()
        assert autostop_loop.is_running() is False
        # At this point, the loop _has_ stopped, but the task is still listening,
        # so rather than socket.timeout, we'll get a refusal instead, thus causing
        # SMTPServerDisconnected
        with pytest.raises(SMTPServerDisconnected):
            SMTPClient(cont.hostname, cont.port, timeout=0.1)
        cont.end()
        catchup_delay()
        cont.ended.wait()
        # Now the listener has gone away, and thus we will end up with socket.timeout
        # or ConnectionError (depending on OS)
        # noinspection PyTypeChecker
        with pytest.raises((socket.timeout, ConnectionError)):
            SMTPClient(cont.hostname, cont.port, timeout=0.1)

    @pytest.mark.filterwarnings(
        "ignore::pytest.PytestUnraisableExceptionWarning"
    )
    def test_inet_contstop(self, temp_event_loop, runner):
        """
        Verify behavior when the controller is stopped before loop is stopped
        """
        cont = UnthreadedController(Sink(), loop=temp_event_loop)
        cont.begin()
        # Make sure event loop is not running (will be started in thread)
        assert temp_event_loop.is_running() is False
        runner(temp_event_loop)
        # Make sure event loop is up and running
        assert temp_event_loop.is_running() is True
        try:
            # Check that we can connect
            with SMTPClient(cont.hostname, cont.port, timeout=AUTOSTOP_DELAY) as client:
                code, _ = client.helo("example.org")
                assert code == 250
                client.quit()
            catchup_delay()
            temp_event_loop.call_soon_threadsafe(cont.end)
            for _ in range(10):  # 10 is arbitrary
                catchup_delay()  # effectively yield to other threads/event loop
                if cont.ended.wait(1.0):
                    break
            assert temp_event_loop.is_running() is True
            # Because we've called .end() there, the server listener should've gone
            # away, so we should end up with a socket.timeout or ConnectionError or
            # SMTPServerDisconnected (depending on lotsa factors)
            expect_errs = (socket.timeout, ConnectionError, SMTPServerDisconnected)
            # noinspection PyTypeChecker
            with pytest.raises(expect_errs):
                SMTPClient(cont.hostname, cont.port, timeout=0.1)
        finally:
            # Wrap up, or else we'll hang
            temp_event_loop.call_soon_threadsafe(cont.cancel_tasks)
            catchup_delay()
            runner.join()
        assert runner.is_alive() is False
        assert temp_event_loop.is_running() is False
        assert temp_event_loop.is_closed() is False


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="Hangs on 3.12")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestFactory:
    def test_normal_situation(self):
        cont = Controller(Sink())
        try:
            cont.start()
            catchup_delay()
            assert cont.smtpd is not None
            assert cont._thread_exception is None
        finally:
            cont.stop()

    def test_unknown_args_direct(self, silence_event_loop_closed: bool):
        unknown = "this_is_an_unknown_kwarg"
        cont = Controller(Sink(), ready_timeout=0.3, **{unknown: True})
        expectedre = r"__init__.. got an unexpected keyword argument '" + unknown + r"'"
        try:
            with pytest.raises(TypeError, match=expectedre):
                cont.start()
            assert cont.smtpd is None
            assert isinstance(cont._thread_exception, TypeError)
        finally:
            cont.stop()

    @pytest.mark.filterwarnings(
        "ignore:server_kwargs will be removed:DeprecationWarning"
    )
    def test_unknown_args_inkwargs(self, silence_event_loop_closed: bool):
        unknown = "this_is_an_unknown_kwarg"
        cont = Controller(Sink(), ready_timeout=0.3, server_kwargs={unknown: True})
        expectedre = r"__init__.. got an unexpected keyword argument '" + unknown + r"'"
        try:
            with pytest.raises(TypeError, match=expectedre):
                cont.start()
            assert cont.smtpd is None
        finally:
            cont.stop()

    def test_factory_none(self, mocker: MockFixture, silence_event_loop_closed: bool):
        # Hypothetical situation where factory() did not raise an Exception
        # but returned None instead
        mocker.patch("aiosmtpd.controller.SMTP", return_value=None)
        cont = Controller(Sink(), ready_timeout=0.3)
        expectedre = r"factory\(\) returned None"
        try:
            with pytest.raises(RuntimeError, match=expectedre):
                cont.start()
            assert cont.smtpd is None
        finally:
            cont.stop()

    def test_noexc_smtpd_missing(
        self, mocker: MockFixture, silence_event_loop_closed: bool
    ):
        # Hypothetical situation where factory() failed but no
        # Exception was generated.
        cont = Controller(Sink())

        def hijacker(*args, **kwargs):
            cont._thread_exception = None
            # Must still return an (unmocked) _FakeServer to prevent a whole bunch
            # of messy exceptions, although they doesn't affect the test at all.
            return _FakeServer(cont.loop)

        mocker.patch("aiosmtpd.controller._FakeServer", side_effect=hijacker)
        mocker.patch(
            "aiosmtpd.controller.SMTP", side_effect=RuntimeError("Simulated Failure")
        )

        expectedre = r"Unknown Error, failed to init SMTP server"
        try:
            with pytest.raises(RuntimeError, match=expectedre):
                cont.start()
            assert cont.smtpd is None
            assert cont._thread_exception is None
        finally:
            cont.stop()


class TestCompat:
    def test_version(self):
        from aiosmtpd import __version__ as init_version
        from aiosmtpd.smtp import __version__ as smtp_version

        assert smtp_version is init_version
