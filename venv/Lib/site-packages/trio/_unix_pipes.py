from __future__ import annotations

import errno
import os
import sys
from typing import TYPE_CHECKING, Final as FinalType

import trio

from ._abc import Stream
from ._util import ConflictDetector, final

assert not TYPE_CHECKING or sys.platform != "win32"

# XX TODO: is this a good number? who knows... it does match the default Linux
# pipe capacity though.
DEFAULT_RECEIVE_SIZE: FinalType = 65536


class _FdHolder:
    # This class holds onto a raw file descriptor, in non-blocking mode, and
    # is responsible for managing its lifecycle. In particular, it's
    # responsible for making sure it gets closed, and also for tracking
    # whether it's been closed.
    #
    # The way we track closure is to set the .fd field to -1, discarding the
    # original value. You might think that this is a strange idea, since it
    # overloads the same field to do two different things. Wouldn't it be more
    # natural to have a dedicated .closed field? But that would be more
    # error-prone. Fds are represented by small integers, and once an fd is
    # closed, its integer value may be reused immediately. If we accidentally
    # used the old fd after being closed, we might end up doing something to
    # another unrelated fd that happened to get assigned the same integer
    # value. By throwing away the integer value immediately, it becomes
    # impossible to make this mistake – we'll just get an EBADF.
    #
    # (This trick was copied from the stdlib socket module.)
    fd: int

    def __init__(self, fd: int) -> None:
        # make sure self.fd is always initialized to *something*, because even
        # if we error out here then __del__ will run and access it.
        self.fd = -1
        if not isinstance(fd, int):
            raise TypeError("file descriptor must be an int")
        self.fd = fd
        # Store original state, and ensure non-blocking mode is enabled
        self._original_is_blocking = os.get_blocking(fd)
        os.set_blocking(fd, False)

    @property
    def closed(self) -> bool:
        return self.fd == -1

    def _raw_close(self) -> None:
        # This doesn't assume it's in a Trio context, so it can be called from
        # __del__. You should never call it from Trio context, because it
        # skips calling notify_fd_close. But from __del__, skipping that is
        # OK, because notify_fd_close just wakes up other tasks that are
        # waiting on this fd, and those tasks hold a reference to this object.
        # So if __del__ is being called, we know there aren't any tasks that
        # need to be woken.
        if self.closed:
            return
        fd = self.fd
        self.fd = -1
        os.set_blocking(fd, self._original_is_blocking)
        os.close(fd)

    def __del__(self) -> None:
        self._raw_close()

    def close(self) -> None:
        if not self.closed:
            trio.lowlevel.notify_closing(self.fd)
            self._raw_close()


@final
class FdStream(Stream):
    """Represents a stream given the file descriptor to a pipe, TTY, etc.

    *fd* must refer to a file that is open for reading and/or writing and
    supports non-blocking I/O (pipes and TTYs will work, on-disk files probably
    not).  The returned stream takes ownership of the fd, so closing the stream
    will close the fd too.  As with `os.fdopen`, you should not directly use
    an fd after you have wrapped it in a stream using this function.

    To be used as a Trio stream, an open file must be placed in non-blocking
    mode.  Unfortunately, this impacts all I/O that goes through the
    underlying open file, including I/O that uses a different
    file descriptor than the one that was passed to Trio. If other threads
    or processes are using file descriptors that are related through `os.dup`
    or inheritance across `os.fork` to the one that Trio is using, they are
    unlikely to be prepared to have non-blocking I/O semantics suddenly
    thrust upon them.  For example, you can use
    ``FdStream(os.dup(sys.stdin.fileno()))`` to obtain a stream for reading
    from standard input, but it is only safe to do so with heavy caveats: your
    stdin must not be shared by any other processes, and you must not make any
    calls to synchronous methods of `sys.stdin` until the stream returned by
    `FdStream` is closed. See `issue #174
    <https://github.com/python-trio/trio/issues/174>`__ for a discussion of the
    challenges involved in relaxing this restriction.

    .. warning:: one specific consequence of non-blocking mode
      applying to the entire open file description is that when
      your program is run with multiple standard streams connected to
      a TTY (as in a terminal emulator), all of the streams become
      non-blocking when you construct an `FdStream` for any of them.
      For example, if you construct an `FdStream` for standard input,
      you might observe Python loggers begin to fail with
      `BlockingIOError`.

    Args:
      fd (int): The fd to be wrapped.

    Returns:
      A new `FdStream` object.
    """

    def __init__(self, fd: int) -> None:
        self._fd_holder = _FdHolder(fd)
        self._send_conflict_detector = ConflictDetector(
            "another task is using this stream for send",
        )
        self._receive_conflict_detector = ConflictDetector(
            "another task is using this stream for receive",
        )

    async def send_all(self, data: bytes) -> None:
        with self._send_conflict_detector:
            # have to check up front, because send_all(b"") on a closed pipe
            # should raise
            if self._fd_holder.closed:
                raise trio.ClosedResourceError("file was already closed")
            await trio.lowlevel.checkpoint()
            length = len(data)
            # adapted from the SocketStream code
            with memoryview(data) as view:
                sent = 0
                while sent < length:
                    with view[sent:] as remaining:
                        try:
                            sent += os.write(self._fd_holder.fd, remaining)
                        except BlockingIOError:
                            await trio.lowlevel.wait_writable(self._fd_holder.fd)
                        except OSError as e:
                            if e.errno == errno.EBADF:
                                raise trio.ClosedResourceError(
                                    "file was already closed",
                                ) from None
                            else:
                                raise trio.BrokenResourceError from e

    async def wait_send_all_might_not_block(self) -> None:
        with self._send_conflict_detector:
            if self._fd_holder.closed:
                raise trio.ClosedResourceError("file was already closed")
            await trio.lowlevel.wait_writable(self._fd_holder.fd)

    async def receive_some(self, max_bytes: int | None = None) -> bytes:
        with self._receive_conflict_detector:
            if max_bytes is None:
                max_bytes = DEFAULT_RECEIVE_SIZE
            else:
                if not isinstance(max_bytes, int):
                    raise TypeError("max_bytes must be integer >= 1")
                if max_bytes < 1:
                    raise ValueError("max_bytes must be integer >= 1")

            await trio.lowlevel.checkpoint()
            while True:
                try:
                    data = os.read(self._fd_holder.fd, max_bytes)
                except BlockingIOError:
                    await trio.lowlevel.wait_readable(self._fd_holder.fd)
                except OSError as exc:
                    if exc.errno == errno.EBADF:
                        raise trio.ClosedResourceError(
                            "file was already closed",
                        ) from None
                    else:
                        raise trio.BrokenResourceError from exc
                else:
                    break

            return data

    def close(self) -> None:
        self._fd_holder.close()

    async def aclose(self) -> None:
        self.close()
        await trio.lowlevel.checkpoint()

    def fileno(self) -> int:
        return self._fd_holder.fd
