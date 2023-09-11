# Copyright 2014-present Facebook, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  * Neither the name Facebook nor the names of its contributors may be used to
#    endorse or promote products derived from this software without specific
#    prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# no unicode literals

import inspect
import os
import math
import socket
import subprocess
import time

# Sometimes it's really hard to get Python extensions to compile,
# so fall back to a pure Python implementation.
try:
    from . import bser
    # Demandimport causes modules to be loaded lazily. Force the load now
    # so that we can fall back on pybser if bser doesn't exist
    bser.pdu_info
except ImportError:
    from . import pybser as bser

from . import (
    capabilities,
    compat,
    encoding,
    load,
)


if os.name == 'nt':
    import ctypes
    import ctypes.wintypes

    wintypes = ctypes.wintypes
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_FLAG_OVERLAPPED = 0x40000000
    OPEN_EXISTING = 3
    INVALID_HANDLE_VALUE = -1
    FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
    FORMAT_MESSAGE_ALLOCATE_BUFFER = 0x00000100
    FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200
    WAIT_FAILED = 0xFFFFFFFF
    WAIT_TIMEOUT = 0x00000102
    WAIT_OBJECT_0 = 0x00000000
    WAIT_IO_COMPLETION = 0x000000C0
    INFINITE = 0xFFFFFFFF

    # Overlapped I/O operation is in progress. (997)
    ERROR_IO_PENDING = 0x000003E5

    # The pointer size follows the architecture
    # We use WPARAM since this type is already conditionally defined
    ULONG_PTR = ctypes.wintypes.WPARAM

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ("Internal", ULONG_PTR), ("InternalHigh", ULONG_PTR),
            ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE)
        ]

        def __init__(self):
            self.Internal = 0
            self.InternalHigh = 0
            self.Offset = 0
            self.OffsetHigh = 0
            self.hEvent = 0

    LPDWORD = ctypes.POINTER(wintypes.DWORD)

    CreateFile = ctypes.windll.kernel32.CreateFileA
    CreateFile.argtypes = [wintypes.LPSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                           wintypes.HANDLE]
    CreateFile.restype = wintypes.HANDLE

    CloseHandle = ctypes.windll.kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL

    ReadFile = ctypes.windll.kernel32.ReadFile
    ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                         LPDWORD, ctypes.POINTER(OVERLAPPED)]
    ReadFile.restype = wintypes.BOOL

    WriteFile = ctypes.windll.kernel32.WriteFile
    WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                          LPDWORD, ctypes.POINTER(OVERLAPPED)]
    WriteFile.restype = wintypes.BOOL

    GetLastError = ctypes.windll.kernel32.GetLastError
    GetLastError.argtypes = []
    GetLastError.restype = wintypes.DWORD

    SetLastError = ctypes.windll.kernel32.SetLastError
    SetLastError.argtypes = [wintypes.DWORD]
    SetLastError.restype = None

    FormatMessage = ctypes.windll.kernel32.FormatMessageA
    FormatMessage.argtypes = [wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                              wintypes.DWORD, ctypes.POINTER(wintypes.LPSTR),
                              wintypes.DWORD, wintypes.LPVOID]
    FormatMessage.restype = wintypes.DWORD

    LocalFree = ctypes.windll.kernel32.LocalFree

    GetOverlappedResult = ctypes.windll.kernel32.GetOverlappedResult
    GetOverlappedResult.argtypes = [wintypes.HANDLE,
                                    ctypes.POINTER(OVERLAPPED), LPDWORD,
                                    wintypes.BOOL]
    GetOverlappedResult.restype = wintypes.BOOL

    GetOverlappedResultEx = getattr(ctypes.windll.kernel32,
                                    'GetOverlappedResultEx', None)
    if GetOverlappedResultEx is not None:
        GetOverlappedResultEx.argtypes = [wintypes.HANDLE,
                                          ctypes.POINTER(OVERLAPPED), LPDWORD,
                                          wintypes.DWORD, wintypes.BOOL]
        GetOverlappedResultEx.restype = wintypes.BOOL

    WaitForSingleObjectEx = ctypes.windll.kernel32.WaitForSingleObjectEx
    WaitForSingleObjectEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL]
    WaitForSingleObjectEx.restype = wintypes.DWORD

    CreateEvent = ctypes.windll.kernel32.CreateEventA
    CreateEvent.argtypes = [LPDWORD, wintypes.BOOL, wintypes.BOOL,
                            wintypes.LPSTR]
    CreateEvent.restype = wintypes.HANDLE

    # Windows Vista is the minimum supported client for CancelIoEx.
    CancelIoEx = ctypes.windll.kernel32.CancelIoEx
    CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)]
    CancelIoEx.restype = wintypes.BOOL

# 2 bytes marker, 1 byte int size, 8 bytes int64 value
sniff_len = 13

# This is a helper for debugging the client.
_debugging = False
if _debugging:

    def log(fmt, *args):
        print('[%s] %s' %
              (time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime()),
               fmt % args[:]))
else:

    def log(fmt, *args):
        pass


def _win32_strerror(err):
    """ expand a win32 error code into a human readable message """

    # FormatMessage will allocate memory and assign it here
    buf = ctypes.c_char_p()
    FormatMessage(
        FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER
        | FORMAT_MESSAGE_IGNORE_INSERTS, None, err, 0, buf, 0, None)
    try:
        return buf.value
    finally:
        LocalFree(buf)


class WatchmanError(Exception):
    def __init__(self, msg=None, cmd=None):
        self.msg = msg
        self.cmd = cmd

    def setCommand(self, cmd):
        self.cmd = cmd

    def __str__(self):
        if self.cmd:
            return '%s, while executing %s' % (self.msg, self.cmd)
        return self.msg


class BSERv1Unsupported(WatchmanError):
    pass


class WatchmanEnvironmentError(WatchmanError):
    def __init__(self, msg, errno, errmsg, cmd=None):
        super(WatchmanEnvironmentError, self).__init__(
            '{0}: errno={1} errmsg={2}'.format(msg, errno, errmsg),
            cmd)


class SocketConnectError(WatchmanError):
    def __init__(self, sockpath, exc):
        super(SocketConnectError, self).__init__(
            'unable to connect to %s: %s' % (sockpath, exc))
        self.sockpath = sockpath
        self.exc = exc


class SocketTimeout(WatchmanError):
    """A specialized exception raised for socket timeouts during communication to/from watchman.
       This makes it easier to implement non-blocking loops as callers can easily distinguish
       between a routine timeout and an actual error condition.

       Note that catching WatchmanError will also catch this as it is a super-class, so backwards
       compatibility in exception handling is preserved.
    """


class CommandError(WatchmanError):
    """error returned by watchman

    self.msg is the message returned by watchman.
    """
    def __init__(self, msg, cmd=None):
        super(CommandError, self).__init__(
            'watchman command error: %s' % (msg, ),
            cmd,
        )


class Transport(object):
    """ communication transport to the watchman server """
    buf = None

    def close(self):
        """ tear it down """
        raise NotImplementedError()

    def readBytes(self, size):
        """ read size bytes """
        raise NotImplementedError()

    def write(self, buf):
        """ write some data """
        raise NotImplementedError()

    def setTimeout(self, value):
        pass

    def readLine(self):
        """ read a line
        Maintains its own buffer, callers of the transport should not mix
        calls to readBytes and readLine.
        """
        if self.buf is None:
            self.buf = []

        # Buffer may already have a line if we've received unilateral
        # response(s) from the server
        if len(self.buf) == 1 and b"\n" in self.buf[0]:
            (line, b) = self.buf[0].split(b"\n", 1)
            self.buf = [b]
            return line

        while True:
            b = self.readBytes(4096)
            if b"\n" in b:
                result = b''.join(self.buf)
                (line, b) = b.split(b"\n", 1)
                self.buf = [b]
                return result + line
            self.buf.append(b)


class Codec(object):
    """ communication encoding for the watchman server """
    transport = None

    def __init__(self, transport):
        self.transport = transport

    def receive(self):
        raise NotImplementedError()

    def send(self, *args):
        raise NotImplementedError()

    def setTimeout(self, value):
        self.transport.setTimeout(value)


class UnixSocketTransport(Transport):
    """ local unix domain socket transport """
    sock = None

    def __init__(self, sockpath, timeout):
        self.sockpath = sockpath
        self.timeout = timeout

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self.sockpath)
            self.sock = sock
        except socket.error as e:
            sock.close()
            raise SocketConnectError(self.sockpath, e)

    def close(self):
        self.sock.close()
        self.sock = None

    def setTimeout(self, value):
        self.timeout = value
        self.sock.settimeout(self.timeout)

    def readBytes(self, size):
        try:
            buf = [self.sock.recv(size)]
            if not buf[0]:
                raise WatchmanError('empty watchman response')
            return buf[0]
        except socket.timeout:
            raise SocketTimeout('timed out waiting for response')

    def write(self, data):
        try:
            self.sock.sendall(data)
        except socket.timeout:
            raise SocketTimeout('timed out sending query command')


def _get_overlapped_result_ex_impl(pipe, olap, nbytes, millis, alertable):
    """ Windows 7 and earlier does not support GetOverlappedResultEx. The
    alternative is to use GetOverlappedResult and wait for read or write
    operation to complete. This is done be using CreateEvent and
    WaitForSingleObjectEx. CreateEvent, WaitForSingleObjectEx
    and GetOverlappedResult are all part of Windows API since WindowsXP.
    This is the exact same implementation that can be found in the watchman
    source code (see get_overlapped_result_ex_impl in stream_win.c). This
    way, maintenance should be simplified.
    """
    log('Preparing to wait for maximum %dms', millis )
    if millis != 0:
        waitReturnCode = WaitForSingleObjectEx(olap.hEvent, millis, alertable)
        if waitReturnCode == WAIT_OBJECT_0:
            # Event is signaled, overlapped IO operation result should be available.
            pass
        elif waitReturnCode == WAIT_IO_COMPLETION:
            # WaitForSingleObjectEx returnes because the system added an I/O completion
            # routine or an asynchronous procedure call (APC) to the thread queue.
            SetLastError(WAIT_IO_COMPLETION)
            pass
        elif waitReturnCode == WAIT_TIMEOUT:
            # We reached the maximum allowed wait time, the IO operation failed
            # to complete in timely fashion.
            SetLastError(WAIT_TIMEOUT)
            return False
        elif waitReturnCode == WAIT_FAILED:
            # something went wrong calling WaitForSingleObjectEx
            err = GetLastError()
            log('WaitForSingleObjectEx failed: %s', _win32_strerror(err))
            return False
        else:
            # unexpected situation deserving investigation.
            err = GetLastError()
            log('Unexpected error: %s', _win32_strerror(err))
            return False

    return GetOverlappedResult(pipe, olap, nbytes, False)


class WindowsNamedPipeTransport(Transport):
    """ connect to a named pipe """

    def __init__(self, sockpath, timeout):
        self.sockpath = sockpath
        self.timeout = int(math.ceil(timeout * 1000))
        self._iobuf = None

        self.pipe = CreateFile(sockpath, GENERIC_READ | GENERIC_WRITE, 0, None,
                               OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None)

        if self.pipe == INVALID_HANDLE_VALUE:
            self.pipe = None
            self._raise_win_err('failed to open pipe %s' % sockpath,
                                GetLastError())

        # event for the overlapped I/O operations
        self._waitable = CreateEvent(None, True, False, None)
        if self._waitable is None:
            self._raise_win_err('CreateEvent failed', GetLastError())

        self._get_overlapped_result_ex = GetOverlappedResultEx
        if (os.getenv('WATCHMAN_WIN7_COMPAT') == '1' or
            self._get_overlapped_result_ex is None):
            self._get_overlapped_result_ex = _get_overlapped_result_ex_impl

    def _raise_win_err(self, msg, err):
        raise IOError('%s win32 error code: %d %s' %
                      (msg, err, _win32_strerror(err)))

    def close(self):
        if self.pipe:
            log('Closing pipe')
            CloseHandle(self.pipe)
        self.pipe = None

        if self._waitable is not None:
            # We release the handle for the event
            CloseHandle(self._waitable)
        self._waitable = None

    def setTimeout(self, value):
        # convert to milliseconds
        self.timeout = int(value * 1000)

    def readBytes(self, size):
        """ A read can block for an unbounded amount of time, even if the
            kernel reports that the pipe handle is signalled, so we need to
            always perform our reads asynchronously
        """

        # try to satisfy the read from any buffered data
        if self._iobuf:
            if size >= len(self._iobuf):
                res = self._iobuf
                self.buf = None
                return res
            res = self._iobuf[:size]
            self._iobuf = self._iobuf[size:]
            return res

        # We need to initiate a read
        buf = ctypes.create_string_buffer(size)
        olap = OVERLAPPED()
        olap.hEvent = self._waitable

        log('made read buff of size %d', size)

        # ReadFile docs warn against sending in the nread parameter for async
        # operations, so we always collect it via GetOverlappedResultEx
        immediate = ReadFile(self.pipe, buf, size, None, olap)

        if not immediate:
            err = GetLastError()
            if err != ERROR_IO_PENDING:
                self._raise_win_err('failed to read %d bytes' % size,
                                    GetLastError())

        nread = wintypes.DWORD()
        if not self._get_overlapped_result_ex(self.pipe, olap, nread,
                                              0 if immediate else self.timeout,
                                              True):
            err = GetLastError()
            CancelIoEx(self.pipe, olap)

            if err == WAIT_TIMEOUT:
                log('GetOverlappedResultEx timedout')
                raise SocketTimeout('timed out after waiting %dms for read' %
                                    self.timeout)

            log('GetOverlappedResultEx reports error %d', err)
            self._raise_win_err('error while waiting for read', err)

        nread = nread.value
        if nread == 0:
            # Docs say that named pipes return 0 byte when the other end did
            # a zero byte write.  Since we don't ever do that, the only
            # other way this shows up is if the client has gotten in a weird
            # state, so let's bail out
            CancelIoEx(self.pipe, olap)
            raise IOError('Async read yielded 0 bytes; unpossible!')

        # Holds precisely the bytes that we read from the prior request
        buf = buf[:nread]

        returned_size = min(nread, size)
        if returned_size == nread:
            return buf

        # keep any left-overs around for a later read to consume
        self._iobuf = buf[returned_size:]
        return buf[:returned_size]

    def write(self, data):
        olap = OVERLAPPED()
        olap.hEvent = self._waitable

        immediate = WriteFile(self.pipe, ctypes.c_char_p(data), len(data),
                              None, olap)

        if not immediate:
            err = GetLastError()
            if err != ERROR_IO_PENDING:
                self._raise_win_err('failed to write %d bytes' % len(data),
                                    GetLastError())

        # Obtain results, waiting if needed
        nwrote = wintypes.DWORD()
        if self._get_overlapped_result_ex(self.pipe, olap, nwrote,
                                          0 if immediate else self.timeout,
                                          True):
            log('made write of %d bytes', nwrote.value)
            return nwrote.value

        err = GetLastError()

        # It's potentially unsafe to allow the write to continue after
        # we unwind, so let's make a best effort to avoid that happening
        CancelIoEx(self.pipe, olap)

        if err == WAIT_TIMEOUT:
            raise SocketTimeout('timed out after waiting %dms for write' %
                                self.timeout)
        self._raise_win_err('error while waiting for write of %d bytes' %
                            len(data), err)


class CLIProcessTransport(Transport):
    """ open a pipe to the cli to talk to the service
    This intended to be used only in the test harness!

    The CLI is an oddball because we only support JSON input
    and cannot send multiple commands through the same instance,
    so we spawn a new process for each command.

    We disable server spawning for this implementation, again, because
    it is intended to be used only in our test harness.  You really
    should not need to use the CLI transport for anything real.

    While the CLI can output in BSER, our Transport interface doesn't
    support telling this instance that it should do so.  That effectively
    limits this implementation to JSON input and output only at this time.

    It is the responsibility of the caller to set the send and
    receive codecs appropriately.
    """
    proc = None
    closed = True

    def __init__(self, sockpath, timeout, binpath='watchman'):
        self.sockpath = sockpath
        self.timeout = timeout
        self.binpath = binpath

    def close(self):
        if self.proc:
            if self.proc.pid is not None:
                self.proc.kill()
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc.wait()
            self.proc = None

    def _connect(self):
        if self.proc:
            return self.proc
        args = [
            self.binpath,
            '--sockname={0}'.format(self.sockpath),
            '--logfile=/BOGUS',
            '--statefile=/BOGUS',
            '--no-spawn',
            '--no-local',
            '--no-pretty',
            '-j',
        ]
        self.proc = subprocess.Popen(args,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        return self.proc

    def readBytes(self, size):
        self._connect()
        res = self.proc.stdout.read(size)
        if not res:
            raise WatchmanError('EOF on CLI process transport')
        return res

    def write(self, data):
        if self.closed:
            self.close()
            self.closed = False
        self._connect()
        res = self.proc.stdin.write(data)
        self.proc.stdin.close()
        self.closed = True
        return res


class BserCodec(Codec):
    """ use the BSER encoding.  This is the default, preferred codec """

    def __init__(self, transport, value_encoding, value_errors):
        super(BserCodec, self).__init__(transport)
        self._value_encoding = value_encoding
        self._value_errors = value_errors

    def _loads(self, response):
        return bser.loads(
            response,
            value_encoding=self._value_encoding,
            value_errors=self._value_errors,
        )

    def receive(self):
        buf = [self.transport.readBytes(sniff_len)]
        if not buf[0]:
            raise WatchmanError('empty watchman response')

        _1, _2, elen = bser.pdu_info(buf[0])

        rlen = len(buf[0])
        while elen > rlen:
            buf.append(self.transport.readBytes(elen - rlen))
            rlen += len(buf[-1])

        response = b''.join(buf)
        try:
            res = self._loads(response)
            return res
        except ValueError as e:
            raise WatchmanError('watchman response decode error: %s' % e)

    def send(self, *args):
        cmd = bser.dumps(*args) # Defaults to BSER v1
        self.transport.write(cmd)


class ImmutableBserCodec(BserCodec):
    """ use the BSER encoding, decoding values using the newer
        immutable object support """

    def _loads(self, response):
        return bser.loads(
            response,
            False,
            value_encoding=self._value_encoding,
            value_errors=self._value_errors,
        )

class Bser2WithFallbackCodec(BserCodec):
    """ use BSER v2 encoding """

    def __init__(self, transport, value_encoding, value_errors):
        super(Bser2WithFallbackCodec, self).__init__(
            transport,
            value_encoding,
            value_errors,
        )
        if compat.PYTHON3:
            bserv2_key = 'required'
        else:
            bserv2_key = 'optional'

        self.send(["version", {bserv2_key: ["bser-v2"]}])

        capabilities = self.receive()

        if 'error' in capabilities:
            raise BSERv1Unsupported(
                'The watchman server version does not support Python 3. Please '
                'upgrade your watchman server.'
            )

        if capabilities['capabilities']['bser-v2']:
            self.bser_version = 2
            self.bser_capabilities = 0
        else:
            self.bser_version = 1
            self.bser_capabilities = 0

    def receive(self):
        buf = [self.transport.readBytes(sniff_len)]
        if not buf[0]:
            raise WatchmanError('empty watchman response')

        recv_bser_version, recv_bser_capabilities, elen = bser.pdu_info(buf[0])

        if hasattr(self, 'bser_version'):
            # Readjust BSER version and capabilities if necessary
            self.bser_version = max(self.bser_version, recv_bser_version)
            self.capabilities = self.bser_capabilities & recv_bser_capabilities

        rlen = len(buf[0])
        while elen > rlen:
            buf.append(self.transport.readBytes(elen - rlen))
            rlen += len(buf[-1])

        response = b''.join(buf)
        try:
            res = self._loads(response)
            return res
        except ValueError as e:
            raise WatchmanError('watchman response decode error: %s' % e)

    def send(self, *args):
        if hasattr(self, 'bser_version'):
            cmd = bser.dumps(*args, version=self.bser_version,
                capabilities=self.bser_capabilities)
        else:
            cmd = bser.dumps(*args)
        self.transport.write(cmd)


class ImmutableBser2Codec(Bser2WithFallbackCodec, ImmutableBserCodec):
    """ use the BSER encoding, decoding values using the newer
        immutable object support """
    pass


class JsonCodec(Codec):
    """ Use json codec.  This is here primarily for testing purposes """
    json = None

    def __init__(self, transport):
        super(JsonCodec, self).__init__(transport)
        # optional dep on json, only if JsonCodec is used
        import json
        self.json = json

    def receive(self):
        line = self.transport.readLine()
        try:
            # In Python 3, json.loads is a transformation from Unicode string to
            # objects possibly containing Unicode strings. We typically expect
            # the JSON blob to be ASCII-only with non-ASCII characters escaped,
            # but it's possible we might get non-ASCII bytes that are valid
            # UTF-8.
            if compat.PYTHON3:
                line = line.decode('utf-8')
            return self.json.loads(line)
        except Exception as e:
            print(e, line)
            raise

    def send(self, *args):
        cmd = self.json.dumps(*args)
        # In Python 3, json.dumps is a transformation from objects possibly
        # containing Unicode strings to Unicode string. Even with (the default)
        # ensure_ascii=True, dumps returns a Unicode string.
        if compat.PYTHON3:
            cmd = cmd.encode('ascii')
        self.transport.write(cmd + b"\n")


class client(object):
    """ Handles the communication with the watchman service """
    sockpath = None
    transport = None
    sendCodec = None
    recvCodec = None
    sendConn = None
    recvConn = None
    subs = {}  # Keyed by subscription name
    sub_by_root = {}  # Keyed by root, then by subscription name
    logs = []  # When log level is raised
    unilateral = ['log', 'subscription']
    tport = None
    useImmutableBser = None

    def __init__(self,
                 sockpath=None,
                 timeout=1.0,
                 transport=None,
                 sendEncoding=None,
                 recvEncoding=None,
                 useImmutableBser=False,
                 # use False for these two because None has a special
                 # meaning
                 valueEncoding=False,
                 valueErrors=False,
                 binpath='watchman'):
        self.sockpath = sockpath
        self.timeout = timeout
        self.useImmutableBser = useImmutableBser
        self.binpath = binpath

        if inspect.isclass(transport) and issubclass(transport, Transport):
            self.transport = transport
        else:
            transport = transport or os.getenv('WATCHMAN_TRANSPORT') or 'local'
            if transport == 'local' and os.name == 'nt':
                self.transport = WindowsNamedPipeTransport
            elif transport == 'local':
                self.transport = UnixSocketTransport
            elif transport == 'cli':
                self.transport = CLIProcessTransport
                if sendEncoding is None:
                    sendEncoding = 'json'
                if recvEncoding is None:
                    recvEncoding = sendEncoding
            else:
                raise WatchmanError('invalid transport %s' % transport)

        sendEncoding = str(sendEncoding or os.getenv('WATCHMAN_ENCODING') or
                           'bser')
        recvEncoding = str(recvEncoding or os.getenv('WATCHMAN_ENCODING') or
                           'bser')

        self.recvCodec = self._parseEncoding(recvEncoding)
        self.sendCodec = self._parseEncoding(sendEncoding)

        # We want to act like the native OS methods as much as possible. This
        # means returning bytestrings on Python 2 by default and Unicode
        # strings on Python 3. However we take an optional argument that lets
        # users override this.
        if valueEncoding is False:
            if compat.PYTHON3:
                self.valueEncoding = encoding.get_local_encoding()
                self.valueErrors = encoding.default_local_errors
            else:
                self.valueEncoding = None
                self.valueErrors = None
        else:
            self.valueEncoding = valueEncoding
            if valueErrors is False:
                self.valueErrors = encoding.default_local_errors
            else:
                self.valueErrors = valueErrors

    def _makeBSERCodec(self, codec):
        def make_codec(transport):
            return codec(transport, self.valueEncoding, self.valueErrors)
        return make_codec

    def _parseEncoding(self, enc):
        if enc == 'bser':
            if self.useImmutableBser:
                return self._makeBSERCodec(ImmutableBser2Codec)
            return self._makeBSERCodec(Bser2WithFallbackCodec)
        elif enc == 'bser-v1':
            if compat.PYTHON3:
                raise BSERv1Unsupported(
                    'Python 3 does not support the BSER v1 encoding: specify '
                    '"bser" or omit the sendEncoding and recvEncoding '
                    'arguments')
            if self.useImmutableBser:
                return self._makeBSERCodec(ImmutableBserCodec)
            return self._makeBSERCodec(BserCodec)
        elif enc == 'json':
            return JsonCodec
        else:
            raise WatchmanError('invalid encoding %s' % enc)

    def _hasprop(self, result, name):
        if self.useImmutableBser:
            return hasattr(result, name)
        return name in result

    def _resolvesockname(self):
        # if invoked via a trigger, watchman will set this env var; we
        # should use it unless explicitly set otherwise
        path = os.getenv('WATCHMAN_SOCK')
        if path:
            return path

        cmd = [self.binpath, '--output-encoding=bser', 'get-sockname']
        try:
            args = dict(stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        close_fds=os.name != 'nt')

            if os.name == 'nt':
                # if invoked via an application with graphical user interface,
                # this call will cause a brief command window pop-up.
                # Using the flag STARTF_USESHOWWINDOW to avoid this behavior.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                args['startupinfo'] = startupinfo

            p = subprocess.Popen(cmd, **args)

        except OSError as e:
            raise WatchmanError('"watchman" executable not in PATH (%s)', e)

        stdout, stderr = p.communicate()
        exitcode = p.poll()

        if exitcode:
            raise WatchmanError("watchman exited with code %d" % exitcode)

        result = bser.loads(stdout)
        if 'error' in result:
            raise WatchmanError('get-sockname error: %s' % result['error'])

        return result['sockname']

    def _connect(self):
        """ establish transport connection """

        if self.recvConn:
            return

        if self.sockpath is None:
            self.sockpath = self._resolvesockname()

        kwargs = {}
        if self.transport == CLIProcessTransport:
            kwargs['binpath'] = self.binpath

        self.tport = self.transport(self.sockpath, self.timeout, **kwargs)
        self.sendConn = self.sendCodec(self.tport)
        self.recvConn = self.recvCodec(self.tport)

    def __del__(self):
        self.close()

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def close(self):
        if self.tport:
            self.tport.close()
            self.tport = None
            self.recvConn = None
            self.sendConn = None

    def receive(self):
        """ receive the next PDU from the watchman service

        If the client has activated subscriptions or logs then
        this PDU may be a unilateral PDU sent by the service to
        inform the client of a log event or subscription change.

        It may also simply be the response portion of a request
        initiated by query.

        There are clients in production that subscribe and call
        this in a loop to retrieve all subscription responses,
        so care should be taken when making changes here.
        """

        self._connect()
        result = self.recvConn.receive()
        if self._hasprop(result, 'error'):
            raise CommandError(result['error'])

        if self._hasprop(result, 'log'):
            self.logs.append(result['log'])

        if self._hasprop(result, 'subscription'):
            sub = result['subscription']
            if not (sub in self.subs):
                self.subs[sub] = []
            self.subs[sub].append(result)

            # also accumulate in {root,sub} keyed store
            root = os.path.normpath(os.path.normcase(result['root']))
            if not root in self.sub_by_root:
                self.sub_by_root[root] = {}
            if not sub in self.sub_by_root[root]:
                self.sub_by_root[root][sub] = []
            self.sub_by_root[root][sub].append(result)

        return result

    def isUnilateralResponse(self, res):
        if 'unilateral' in res and res['unilateral']:
            return True
        # Fall back to checking for known unilateral responses
        for k in self.unilateral:
            if k in res:
                return True
        return False

    def getLog(self, remove=True):
        """ Retrieve buffered log data

        If remove is true the data will be removed from the buffer.
        Otherwise it will be left in the buffer
        """
        res = self.logs
        if remove:
            self.logs = []
        return res

    def getSubscription(self, name, remove=True, root=None):
        """ Retrieve the data associated with a named subscription

        If remove is True (the default), the subscription data is removed
        from the buffer.  Otherwise the data is returned but left in
        the buffer.

        Returns None if there is no data associated with `name`

        If root is not None, then only return the subscription
        data that matches both root and name.  When used in this way,
        remove processing impacts both the unscoped and scoped stores
        for the subscription data.
        """
        if root is not None:
            root = os.path.normpath(os.path.normcase(root))
            if root not in self.sub_by_root:
                return None
            if name not in self.sub_by_root[root]:
                return None
            sub = self.sub_by_root[root][name]
            if remove:
                del self.sub_by_root[root][name]
                # don't let this grow unbounded
                if name in self.subs:
                    del self.subs[name]
            return sub

        if name not in self.subs:
            return None
        sub = self.subs[name]
        if remove:
            del self.subs[name]
        return sub

    def query(self, *args):
        """ Send a query to the watchman service and return the response

        This call will block until the response is returned.
        If any unilateral responses are sent by the service in between
        the request-response they will be buffered up in the client object
        and NOT returned via this method.
        """

        log('calling client.query')
        self._connect()
        try:
            self.sendConn.send(args)

            res = self.receive()
            while self.isUnilateralResponse(res):
                res = self.receive()

            return res
        except EnvironmentError as ee:
            # When we can depend on Python 3, we can use PEP 3134
            # exception chaining here.
            raise WatchmanEnvironmentError(
                'I/O error communicating with watchman daemon',
                ee.errno,
                ee.strerror,
                args)
        except WatchmanError as ex:
            ex.setCommand(args)
            raise

    def capabilityCheck(self, optional=None, required=None):
        """ Perform a server capability check """
        res = self.query('version', {
            'optional': optional or [],
            'required': required or []
        })

        if not self._hasprop(res, 'capabilities'):
            # Server doesn't support capabilities, so we need to
            # synthesize the results based on the version
            capabilities.synthesize(res, optional)
            if 'error' in res:
                raise CommandError(res['error'])

        return res

    def setTimeout(self, value):
        self.recvConn.setTimeout(value)
        self.sendConn.setTimeout(value)
