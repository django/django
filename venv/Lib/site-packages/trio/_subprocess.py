from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import warnings
from contextlib import ExitStack
from functools import partial
from typing import (
    TYPE_CHECKING,
    Final,
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
    overload,
)

import trio

from ._core import ClosedResourceError, TaskStatus
from ._highlevel_generic import StapledStream
from ._subprocess_platform import (
    create_pipe_from_child_output,
    create_pipe_to_child_stdin,
    wait_child_exiting,
)
from ._sync import Lock
from ._util import NoPublicConstructor, final

if TYPE_CHECKING:
    import signal
    from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
    from io import TextIOWrapper

    from typing_extensions import Unpack

    from ._abc import ReceiveStream, SendStream


# Sphinx cannot parse the stringified version
StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]


# Linux-specific, but has complex lifetime management stuff so we hard-code it
# here instead of hiding it behind the _subprocess_platform abstraction
can_try_pidfd_open: bool
if TYPE_CHECKING:

    def pidfd_open(fd: int, flags: int) -> int: ...

    from ._subprocess_platform import ClosableReceiveStream, ClosableSendStream

else:
    can_try_pidfd_open = True
    try:
        from os import pidfd_open
    except ImportError:
        if sys.platform == "linux":
            # this workaround is needed on:
            #  - CPython <= 3.8
            #  - non-CPython (maybe?)
            #  - Anaconda's interpreter (as it is built to assume an older
            #    than current linux kernel)
            #
            # The last point implies that other custom builds might not work;
            # therefore, no assertion should be here.
            import ctypes

            _cdll_for_pidfd_open = ctypes.CDLL(None, use_errno=True)
            _cdll_for_pidfd_open.syscall.restype = ctypes.c_long
            # pid and flags are actually int-sized, but the syscall() function
            # always takes longs. (Except on x32 where long is 32-bits and syscall
            # takes 64-bit arguments. But in the unlikely case that anyone is
            # using x32, this will still work, b/c we only need to pass in 32 bits
            # of data, and the C ABI doesn't distinguish between passing 32-bit vs
            # 64-bit integers; our 32-bit values will get loaded into 64-bit
            # registers where syscall() will find them.)
            _cdll_for_pidfd_open.syscall.argtypes = [
                ctypes.c_long,  # syscall number
                ctypes.c_long,  # pid
                ctypes.c_long,  # flags
            ]
            __NR_pidfd_open = 434

            def pidfd_open(fd: int, flags: int) -> int:
                result = _cdll_for_pidfd_open.syscall(__NR_pidfd_open, fd, flags)
                if result < 0:  # pragma: no cover
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                return result

        else:
            can_try_pidfd_open = False


class HasFileno(Protocol):
    """Represents any file-like object that has a file descriptor."""

    def fileno(self) -> int: ...


@final
class Process(metaclass=NoPublicConstructor):
    r"""A child process. Like :class:`subprocess.Popen`, but async.

    This class has no public constructor. The most common way to get a
    `Process` object is to combine `Nursery.start` with `run_process`::

       process_object = await nursery.start(run_process, ...)

    This way, `run_process` supervises the process and makes sure that it is
    cleaned up properly, while optionally checking the return value, feeding
    it input, and so on.

    If you need more control – for example, because you want to spawn a child
    process that outlives your program – then another option is to use
    `trio.lowlevel.open_process`::

       process_object = await trio.lowlevel.open_process(...)

    Attributes:
      args (str or list): The ``command`` passed at construction time,
          specifying the process to execute and its arguments.
      pid (int): The process ID of the child process managed by this object.
      stdin (trio.abc.SendStream or None): A stream connected to the child's
          standard input stream: when you write bytes here, they become available
          for the child to read. Only available if the :class:`Process`
          was constructed using ``stdin=PIPE``; otherwise this will be None.
      stdout (trio.abc.ReceiveStream or None): A stream connected to
          the child's standard output stream: when the child writes to
          standard output, the written bytes become available for you
          to read here. Only available if the :class:`Process` was
          constructed using ``stdout=PIPE``; otherwise this will be None.
      stderr (trio.abc.ReceiveStream or None): A stream connected to
          the child's standard error stream: when the child writes to
          standard error, the written bytes become available for you
          to read here. Only available if the :class:`Process` was
          constructed using ``stderr=PIPE``; otherwise this will be None.
      stdio (trio.StapledStream or None): A stream that sends data to
          the child's standard input and receives from the child's standard
          output. Only available if both :attr:`stdin` and :attr:`stdout` are
          available; otherwise this will be None.

    """

    # We're always in binary mode.
    universal_newlines: Final = False
    encoding: Final = None
    errors: Final = None

    # Available for the per-platform wait_child_exiting() implementations
    # to stash some state; waitid platforms use this to avoid spawning
    # arbitrarily many threads if wait() keeps getting cancelled.
    _wait_for_exit_data: object = None

    def __init__(
        self,
        popen: subprocess.Popen[bytes],
        stdin: SendStream | None,
        stdout: ReceiveStream | None,
        stderr: ReceiveStream | None,
    ) -> None:
        self._proc = popen
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.stdio: StapledStream[SendStream, ReceiveStream] | None = None
        if self.stdin is not None and self.stdout is not None:
            self.stdio = StapledStream(self.stdin, self.stdout)

        self._wait_lock: Lock = Lock()

        self._pidfd: TextIOWrapper | None = None
        if can_try_pidfd_open:
            try:
                fd: int = pidfd_open(self._proc.pid, 0)
            except OSError:  # pragma: no cover
                # Well, we tried, but it didn't work (probably because we're
                # running on an older kernel, or in an older sandbox, that
                # hasn't been updated to support pidfd_open). We'll fall back
                # on waitid instead.
                pass
            else:
                # It worked! Wrap the raw fd up in a Python file object to
                # make sure it'll get closed.
                # SIM115: open-file-with-context-handler
                self._pidfd = open(fd)  # noqa: SIM115

        self.args: StrOrBytesPath | Sequence[StrOrBytesPath] = self._proc.args
        self.pid: int = self._proc.pid

    def __repr__(self) -> str:
        returncode = self.returncode
        if returncode is None:
            status = f"running with PID {self.pid}"
        else:
            if returncode < 0:
                status = f"exited with signal {-returncode}"
            else:
                status = f"exited with status {returncode}"
        return f"<trio.Process {self.args!r}: {status}>"

    @property
    def returncode(self) -> int | None:
        """The exit status of the process (an integer), or ``None`` if it's
        still running.

        By convention, a return code of zero indicates success.  On
        UNIX, negative values indicate termination due to a signal,
        e.g., -11 if terminated by signal 11 (``SIGSEGV``).  On
        Windows, a process that exits due to a call to
        :meth:`Process.terminate` will have an exit status of 1.

        Unlike the standard library `subprocess.Popen.returncode`, you don't
        have to call `poll` or `wait` to update this attribute; it's
        automatically updated as needed, and will always give you the latest
        information.

        """
        result = self._proc.poll()
        if result is not None:
            self._close_pidfd()
        return result

    def _close_pidfd(self) -> None:
        if self._pidfd is not None:
            trio.lowlevel.notify_closing(self._pidfd.fileno())
            self._pidfd.close()
            self._pidfd = None

    async def wait(self) -> int:
        """Block until the process exits.

        Returns:
          The exit status of the process; see :attr:`returncode`.
        """
        async with self._wait_lock:
            if self.poll() is None:
                if self._pidfd is not None:
                    with contextlib.suppress(
                        ClosedResourceError,
                    ):  # something else (probably a call to poll) already closed the pidfd
                        await trio.lowlevel.wait_readable(self._pidfd.fileno())
                else:
                    await wait_child_exiting(self)
                # We have to use .wait() here, not .poll(), because on macOS
                # (and maybe other systems, who knows), there's a race
                # condition inside the kernel that creates a tiny window where
                # kqueue reports that the process has exited, but
                # waitpid(WNOHANG) can't yet reap it. So this .wait() may
                # actually block for a tiny fraction of a second.
                self._proc.wait()
                self._close_pidfd()
        assert self._proc.returncode is not None
        return self._proc.returncode

    def poll(self) -> int | None:
        """Returns the exit status of the process (an integer), or ``None`` if
        it's still running.

        Note that on Trio (unlike the standard library `subprocess.Popen`),
        ``process.poll()`` and ``process.returncode`` always give the same
        result. See `returncode` for more details. This method is only
        included to make it easier to port code from `subprocess`.

        """
        return self.returncode

    def send_signal(self, sig: signal.Signals | int) -> None:
        """Send signal ``sig`` to the process.

        On UNIX, ``sig`` may be any signal defined in the
        :mod:`signal` module, such as ``signal.SIGINT`` or
        ``signal.SIGTERM``. On Windows, it may be anything accepted by
        the standard library :meth:`subprocess.Popen.send_signal`.
        """
        self._proc.send_signal(sig)

    def terminate(self) -> None:
        """Terminate the process, politely if possible.

        On UNIX, this is equivalent to
        ``send_signal(signal.SIGTERM)``; by convention this requests
        graceful termination, but a misbehaving or buggy process might
        ignore it. On Windows, :meth:`terminate` forcibly terminates the
        process in the same manner as :meth:`kill`.
        """
        self._proc.terminate()

    def kill(self) -> None:
        """Immediately terminate the process.

        On UNIX, this is equivalent to
        ``send_signal(signal.SIGKILL)``.  On Windows, it calls
        ``TerminateProcess``. In both cases, the process cannot
        prevent itself from being killed, but the termination will be
        delivered asynchronously; use :meth:`wait` if you want to
        ensure the process is actually dead before proceeding.
        """
        self._proc.kill()


async def _open_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    stdin: int | HasFileno | None = None,
    stdout: int | HasFileno | None = None,
    stderr: int | HasFileno | None = None,
    **options: object,
) -> Process:
    r"""Execute a child program in a new process.

    After construction, you can interact with the child process by writing data to its
    `~trio.Process.stdin` stream (a `~trio.abc.SendStream`), reading data from its
    `~trio.Process.stdout` and/or `~trio.Process.stderr` streams (both
    `~trio.abc.ReceiveStream`\s), sending it signals using `~trio.Process.terminate`,
    `~trio.Process.kill`, or `~trio.Process.send_signal`, and waiting for it to exit
    using `~trio.Process.wait`. See `trio.Process` for details.

    Each standard stream is only available if you specify that a pipe should be created
    for it. For example, if you pass ``stdin=subprocess.PIPE``, you can write to the
    `~trio.Process.stdin` stream, else `~trio.Process.stdin` will be ``None``.

    Unlike `trio.run_process`, this function doesn't do any kind of automatic
    management of the child process. It's up to you to implement whatever semantics you
    want.

    Args:
      command: The command to run. Typically this is a sequence of strings or
          bytes such as ``['ls', '-l', 'directory with spaces']``, where the
          first element names the executable to invoke and the other elements
          specify its arguments. With ``shell=True`` in the ``**options``, or on
          Windows, ``command`` can be a string or bytes, which will be parsed
          following platform-dependent :ref:`quoting rules
          <subprocess-quoting>`. In all cases ``command`` can be a path or a
          sequence of paths.
      stdin: Specifies what the child process's standard input
          stream should connect to: output written by the parent
          (``subprocess.PIPE``), nothing (``subprocess.DEVNULL``),
          or an open file (pass a file descriptor or something whose
          ``fileno`` method returns one). If ``stdin`` is unspecified,
          the child process will have the same standard input stream
          as its parent.
      stdout: Like ``stdin``, but for the child process's standard output
          stream.
      stderr: Like ``stdin``, but for the child process's standard error
          stream. An additional value ``subprocess.STDOUT`` is supported,
          which causes the child's standard output and standard error
          messages to be intermixed on a single standard output stream,
          attached to whatever the ``stdout`` option says to attach it to.
      **options: Other :ref:`general subprocess options <subprocess-options>`
          are also accepted.

    Returns:
      A new `trio.Process` object.

    Raises:
      OSError: if the process spawning fails, for example because the
         specified command could not be found.

    """
    for key in ("universal_newlines", "text", "encoding", "errors", "bufsize"):
        if options.get(key):
            raise TypeError(
                "trio.Process only supports communicating over "
                f"unbuffered byte streams; the '{key}' option is not supported",
            )

    if os.name == "posix":
        # TODO: how do paths and sequences thereof play with `shell=True`?
        if isinstance(command, (str, bytes)) and not options.get("shell"):
            raise TypeError(
                "command must be a sequence (not a string or bytes) if "
                "shell=False on UNIX systems",
            )
        if not isinstance(command, (str, bytes)) and options.get("shell"):
            raise TypeError(
                "command must be a string or bytes (not a sequence) if "
                "shell=True on UNIX systems",
            )

    trio_stdin: ClosableSendStream | None = None
    trio_stdout: ClosableReceiveStream | None = None
    trio_stderr: ClosableReceiveStream | None = None
    # Close the parent's handle for each child side of a pipe; we want the child to
    # have the only copy, so that when it exits we can read EOF on our side. The
    # trio ends of pipes will be transferred to the Process object, which will be
    # responsible for their lifetime. If process spawning fails, though, we still
    # want to close them before letting the failure bubble out
    with ExitStack() as always_cleanup, ExitStack() as cleanup_on_fail:
        if stdin == subprocess.PIPE:
            trio_stdin, stdin = create_pipe_to_child_stdin()
            always_cleanup.callback(os.close, stdin)
            cleanup_on_fail.callback(trio_stdin.close)
        if stdout == subprocess.PIPE:
            trio_stdout, stdout = create_pipe_from_child_output()
            always_cleanup.callback(os.close, stdout)
            cleanup_on_fail.callback(trio_stdout.close)
        if stderr == subprocess.STDOUT:
            # If we created a pipe for stdout, pass the same pipe for
            # stderr.  If stdout was some non-pipe thing (DEVNULL or a
            # given FD), pass the same thing. If stdout was passed as
            # None, keep stderr as STDOUT to allow subprocess to dup
            # our stdout. Regardless of which of these is applicable,
            # don't create a new Trio stream for stderr -- if stdout
            # is piped, stderr will be intermixed on the stdout stream.
            if stdout is not None:
                stderr = stdout
        elif stderr == subprocess.PIPE:
            trio_stderr, stderr = create_pipe_from_child_output()
            always_cleanup.callback(os.close, stderr)
            cleanup_on_fail.callback(trio_stderr.close)

        popen = await trio.to_thread.run_sync(
            partial(
                subprocess.Popen,
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                **options,
            ),
        )
        # We did not fail, so dismiss the stack for the trio ends
        cleanup_on_fail.pop_all()

    return Process._create(popen, trio_stdin, trio_stdout, trio_stderr)


# async function missing await
async def _windows_deliver_cancel(p: Process) -> None:  # noqa: RUF029
    try:
        p.terminate()
    except OSError as exc:
        warnings.warn(
            RuntimeWarning(f"TerminateProcess on {p!r} failed with: {exc!r}"),
            stacklevel=1,
        )


async def _posix_deliver_cancel(p: Process) -> None:
    try:
        p.terminate()
        await trio.sleep(5)
        warnings.warn(
            RuntimeWarning(
                f"process {p!r} ignored SIGTERM for 5 seconds. "
                "(Maybe you should pass a custom deliver_cancel?) "
                "Trying SIGKILL.",
            ),
            stacklevel=1,
        )
        p.kill()
    except OSError as exc:
        warnings.warn(
            RuntimeWarning(f"tried to kill process {p!r}, but failed with: {exc!r}"),
            stacklevel=1,
        )


# Use a private name, so we can declare platform-specific stubs below.
# This is also the signature read by Sphinx
async def _run_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    stdin: bytes | bytearray | memoryview | int | HasFileno | None = b"",
    capture_stdout: bool = False,
    capture_stderr: bool = False,
    check: bool = True,
    deliver_cancel: Callable[[Process], Awaitable[object]] | None = None,
    task_status: TaskStatus[Process] = trio.TASK_STATUS_IGNORED,
    **options: object,
) -> subprocess.CompletedProcess[bytes]:
    """Run ``command`` in a subprocess and wait for it to complete.

    This function can be called in two different ways.

    One option is a direct call, like::

        completed_process_info = await trio.run_process(...)

    In this case, it returns a :class:`subprocess.CompletedProcess` instance
    describing the results. Use this if you want to treat a process like a
    function call.

    The other option is to run it as a task using `Nursery.start` – the enhanced version
    of `~Nursery.start_soon` that lets a task pass back a value during startup::

        process = await nursery.start(trio.run_process, ...)

    In this case, `~Nursery.start` returns a `Process` object that you can use
    to interact with the process while it's running. Use this if you want to
    treat a process like a background task.

    Either way, `run_process` makes sure that the process has exited before
    returning, handles cancellation, optionally checks for errors, and
    provides some convenient shorthands for dealing with the child's
    input/output.

    **Input:** `run_process` supports all the same ``stdin=`` arguments as
    `subprocess.Popen`. In addition, if you simply want to pass in some fixed
    data, you can pass a plain `bytes` object, and `run_process` will take
    care of setting up a pipe, feeding in the data you gave, and then sending
    end-of-file. The default is ``b""``, which means that the child will receive
    an empty stdin. If you want the child to instead read from the parent's
    stdin, use ``stdin=None``.

    **Output:** By default, any output produced by the subprocess is
    passed through to the standard output and error streams of the
    parent Trio process.

    When calling `run_process` directly, you can capture the subprocess's output by
    passing ``capture_stdout=True`` to capture the subprocess's standard output, and/or
    ``capture_stderr=True`` to capture its standard error. Captured data is collected up
    by Trio into an in-memory buffer, and then provided as the
    :attr:`~subprocess.CompletedProcess.stdout` and/or
    :attr:`~subprocess.CompletedProcess.stderr` attributes of the returned
    :class:`~subprocess.CompletedProcess` object. The value for any stream that was not
    captured will be ``None``.

    If you want to capture both stdout and stderr while keeping them
    separate, pass ``capture_stdout=True, capture_stderr=True``.

    If you want to capture both stdout and stderr but mixed together
    in the order they were printed, use: ``capture_stdout=True, stderr=subprocess.STDOUT``.
    This directs the child's stderr into its stdout, so the combined
    output will be available in the `~subprocess.CompletedProcess.stdout`
    attribute.

    If you're using ``await nursery.start(trio.run_process, ...)`` and want to capture
    the subprocess's output for further processing, then use ``stdout=subprocess.PIPE``
    and then make sure to read the data out of the `Process.stdout` stream. If you want
    to capture stderr separately, use ``stderr=subprocess.PIPE``. If you want to capture
    both, but mixed together in the correct order, use ``stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT``.

    **Error checking:** If the subprocess exits with a nonzero status
    code, indicating failure, :func:`run_process` raises a
    :exc:`subprocess.CalledProcessError` exception rather than
    returning normally. The captured outputs are still available as
    the :attr:`~subprocess.CalledProcessError.stdout` and
    :attr:`~subprocess.CalledProcessError.stderr` attributes of that
    exception.  To disable this behavior, so that :func:`run_process`
    returns normally even if the subprocess exits abnormally, pass ``check=False``.

    Note that this can make the ``capture_stdout`` and ``capture_stderr``
    arguments useful even when starting `run_process` as a task: if you only
    care about the output if the process fails, then you can enable capturing
    and then read the output off of the `~subprocess.CalledProcessError`.

    **Cancellation:** If cancelled, `run_process` sends a termination
    request to the subprocess, then waits for it to fully exit. The
    ``deliver_cancel`` argument lets you control how the process is terminated.

    .. note:: `run_process` is intentionally similar to the standard library
       `subprocess.run`, but some of the defaults are different. Specifically, we
       default to:

       - ``check=True``, because `"errors should never pass silently / unless
         explicitly silenced" <https://www.python.org/dev/peps/pep-0020/>`__.

       - ``stdin=b""``, because it produces less-confusing results if a subprocess
         unexpectedly tries to read from stdin.

       To get the `subprocess.run` semantics, use ``check=False, stdin=None``.

    Args:
      command (list or str): The command to run. Typically this is a
          sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
          where the first element names the executable to invoke and the other
          elements specify its arguments. With ``shell=True`` in the
          ``**options``, or on Windows, ``command`` may alternatively
          be a string, which will be parsed following platform-dependent
          :ref:`quoting rules <subprocess-quoting>`.

      stdin (:obj:`bytes`, subprocess.PIPE, file descriptor, or None): The
          bytes to provide to the subprocess on its standard input stream, or
          ``None`` if the subprocess's standard input should come from the
          same place as the parent Trio process's standard input. As is the
          case with the :mod:`subprocess` module, you can also pass a file
          descriptor or an object with a ``fileno()`` method, in which case
          the subprocess's standard input will come from that file.

          When starting `run_process` as a background task, you can also use
          ``stdin=subprocess.PIPE``, in which case `Process.stdin` will be a
          `~trio.abc.SendStream` that you can use to send data to the child.

      capture_stdout (bool): If true, capture the bytes that the subprocess
          writes to its standard output stream and return them in the
          `~subprocess.CompletedProcess.stdout` attribute of the returned
          `subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

      capture_stderr (bool): If true, capture the bytes that the subprocess
          writes to its standard error stream and return them in the
          `~subprocess.CompletedProcess.stderr` attribute of the returned
          `~subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

      check (bool): If false, don't validate that the subprocess exits
          successfully. You should be sure to check the
          ``returncode`` attribute of the returned object if you pass
          ``check=False``, so that errors don't pass silently.

      deliver_cancel (async function or None): If `run_process` is cancelled,
          then it needs to kill the child process. There are multiple ways to
          do this, so we let you customize it.

          If you pass None (the default), then the behavior depends on the
          platform:

          - On Windows, Trio calls ``TerminateProcess``, which should kill the
            process immediately.

          - On Unix-likes, the default behavior is to send a ``SIGTERM``, wait
            5 seconds, and send a ``SIGKILL``.

          Alternatively, you can customize this behavior by passing in an
          arbitrary async function, which will be called with the `Process`
          object as an argument. For example, the default Unix behavior could
          be implemented like this::

             async def my_deliver_cancel(process):
                 process.send_signal(signal.SIGTERM)
                 await trio.sleep(5)
                 process.send_signal(signal.SIGKILL)

          When the process actually exits, the ``deliver_cancel`` function
          will automatically be cancelled – so if the process exits after
          ``SIGTERM``, then we'll never reach the ``SIGKILL``.

          In any case, `run_process` will always wait for the child process to
          exit before raising `Cancelled`.

      **options: :func:`run_process` also accepts any :ref:`general subprocess
          options <subprocess-options>` and passes them on to the
          :class:`~trio.Process` constructor. This includes the
          ``stdout`` and ``stderr`` options, which provide additional
          redirection possibilities such as ``stderr=subprocess.STDOUT``,
          ``stdout=subprocess.DEVNULL``, or file descriptors.

    Returns:

      When called normally – a `subprocess.CompletedProcess` instance
      describing the return code and outputs.

      When called via `Nursery.start` – a `trio.Process` instance.

    Raises:
      UnicodeError: if ``stdin`` is specified as a Unicode string, rather
          than bytes
      ValueError: if multiple redirections are specified for the same
          stream, e.g., both ``capture_stdout=True`` and
          ``stdout=subprocess.DEVNULL``
      subprocess.CalledProcessError: if ``check=False`` is not passed
          and the process exits with a nonzero exit status
      OSError: if an error is encountered starting or communicating with
          the process
      ExceptionGroup: if exceptions occur in ``deliver_cancel``,
          or when exceptions occur when communicating with the subprocess.
          If strict_exception_groups is set to false in the global context,
          which is deprecated, then single exceptions will be collapsed.

    .. note:: The child process runs in the same process group as the parent
       Trio process, so a Ctrl+C will be delivered simultaneously to both
       parent and child. If you don't want this behavior, consult your
       platform's documentation for starting child processes in a different
       process group.

    """

    if isinstance(stdin, str):
        raise UnicodeError("process stdin must be bytes, not str")
    if task_status is trio.TASK_STATUS_IGNORED:
        if stdin is subprocess.PIPE:
            raise ValueError(
                "stdout=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe; use nursery.start "
                "or pass the data you want to write directly",
            )
        if options.get("stdout") is subprocess.PIPE:
            raise ValueError(
                "stdout=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe",
            )
        if options.get("stderr") is subprocess.PIPE:
            raise ValueError(
                "stderr=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe",
            )
    if isinstance(stdin, (bytes, bytearray, memoryview)):
        input_ = stdin
        options["stdin"] = subprocess.PIPE
    else:
        # stdin should be something acceptable to Process
        # (None, DEVNULL, a file descriptor, etc) and Process
        # will raise if it's not
        input_ = None
        options["stdin"] = stdin

    if capture_stdout:
        if "stdout" in options:
            raise ValueError("can't specify both stdout and capture_stdout")
        options["stdout"] = subprocess.PIPE
    if capture_stderr:
        if "stderr" in options:
            raise ValueError("can't specify both stderr and capture_stderr")
        options["stderr"] = subprocess.PIPE

    if deliver_cancel is None:
        if os.name == "nt":
            deliver_cancel = _windows_deliver_cancel
        else:
            assert os.name == "posix"
            deliver_cancel = _posix_deliver_cancel

    stdout_chunks: list[bytes | bytearray] = []
    stderr_chunks: list[bytes | bytearray] = []

    async def feed_input(stream: SendStream) -> None:
        async with stream:
            try:
                assert input_ is not None
                await stream.send_all(input_)
            except trio.BrokenResourceError:
                pass

    async def read_output(
        stream: ReceiveStream,
        chunks: list[bytes | bytearray],
    ) -> None:
        async with stream:
            async for chunk in stream:
                chunks.append(chunk)  # noqa: PERF401

    # Opening the process does not need to be inside the nursery, so we put it outside
    # so any exceptions get directly seen by users.
    proc = await _open_process(command, **options)  # type: ignore[arg-type]
    async with trio.open_nursery() as nursery:
        try:
            if input_ is not None:
                assert proc.stdin is not None
                nursery.start_soon(feed_input, proc.stdin)
                proc.stdin = None
                proc.stdio = None
            if capture_stdout:
                assert proc.stdout is not None
                nursery.start_soon(read_output, proc.stdout, stdout_chunks)
                proc.stdout = None
                proc.stdio = None
            if capture_stderr:
                assert proc.stderr is not None
                nursery.start_soon(read_output, proc.stderr, stderr_chunks)
                proc.stderr = None
            task_status.started(proc)
            await proc.wait()
        except BaseException:
            with trio.CancelScope(shield=True):
                killer_cscope = trio.CancelScope(shield=True)

                async def killer() -> None:
                    with killer_cscope:
                        await deliver_cancel(proc)

                nursery.start_soon(killer)
                await proc.wait()
                killer_cscope.cancel(reason="trio internal implementation detail")
                raise

    stdout = b"".join(stdout_chunks) if capture_stdout else None
    stderr = b"".join(stderr_chunks) if capture_stderr else None

    if proc.returncode and check:
        raise subprocess.CalledProcessError(
            proc.returncode,
            proc.args,
            output=stdout,
            stderr=stderr,
        )
    else:
        assert proc.returncode is not None
        return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


# There's a lot of duplication here because type checkers don't
# have a good way to represent overloads that differ only
# slightly. A cheat sheet:
#
# - on Windows, command is Union[str, Sequence[str]];
#   on Unix, command is str if shell=True and Sequence[str] otherwise
#
# - on Windows, there are startupinfo and creationflags options;
#   on Unix, there are preexec_fn, restore_signals, start_new_session,
#            pass_fds, group (3.9+), extra_groups (3.9+), user (3.9+),
#            umask (3.9+), pipesize (3.10+), process_group (3.11+)
#
# - run_process() has the signature of open_process() plus arguments
#   capture_stdout, capture_stderr, check, deliver_cancel, the ability
#   to pass bytes as stdin, and the ability to run in `nursery.start`


class GeneralProcessArgs(TypedDict, total=False):
    """Arguments shared between all runs."""

    stdout: int | HasFileno | None
    stderr: int | HasFileno | None
    close_fds: bool
    cwd: StrOrBytesPath | None
    env: Mapping[str, str] | None
    executable: StrOrBytesPath | None


if TYPE_CHECKING:
    if sys.platform == "win32":

        class WindowsProcessArgs(GeneralProcessArgs, total=False):
            """Arguments shared between all Windows runs."""

            shell: bool
            startupinfo: subprocess.STARTUPINFO | None
            creationflags: int

        async def open_process(
            command: StrOrBytesPath | Sequence[StrOrBytesPath],
            *,
            stdin: int | HasFileno | None = None,
            **kwargs: Unpack[WindowsProcessArgs],
        ) -> trio.Process:
            r"""Execute a child program in a new process.

            After construction, you can interact with the child process by writing data to its
            `~trio.Process.stdin` stream (a `~trio.abc.SendStream`), reading data from its
            `~trio.Process.stdout` and/or `~trio.Process.stderr` streams (both
            `~trio.abc.ReceiveStream`\s), sending it signals using `~trio.Process.terminate`,
            `~trio.Process.kill`, or `~trio.Process.send_signal`, and waiting for it to exit
            using `~trio.Process.wait`. See `trio.Process` for details.

            Each standard stream is only available if you specify that a pipe should be created
            for it. For example, if you pass ``stdin=subprocess.PIPE``, you can write to the
            `~trio.Process.stdin` stream, else `~trio.Process.stdin` will be ``None``.

            Unlike `trio.run_process`, this function doesn't do any kind of automatic
            management of the child process. It's up to you to implement whatever semantics you
            want.

            Args:
              command (list or str): The command to run. Typically this is a
                  sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
                  where the first element names the executable to invoke and the other
                  elements specify its arguments. With ``shell=True`` in the
                  ``**options``, or on Windows, ``command`` may alternatively
                  be a string, which will be parsed following platform-dependent
                  :ref:`quoting rules <subprocess-quoting>`.
              stdin: Specifies what the child process's standard input
                  stream should connect to: output written by the parent
                  (``subprocess.PIPE``), nothing (``subprocess.DEVNULL``),
                  or an open file (pass a file descriptor or something whose
                  ``fileno`` method returns one). If ``stdin`` is unspecified,
                  the child process will have the same standard input stream
                  as its parent.
              stdout: Like ``stdin``, but for the child process's standard output
                  stream.
              stderr: Like ``stdin``, but for the child process's standard error
                  stream. An additional value ``subprocess.STDOUT`` is supported,
                  which causes the child's standard output and standard error
                  messages to be intermixed on a single standard output stream,
                  attached to whatever the ``stdout`` option says to attach it to.
              **options: Other :ref:`general subprocess options <subprocess-options>`
                  are also accepted.

            Returns:
              A new `trio.Process` object.

            Raises:
              OSError: if the process spawning fails, for example because the
                 specified command could not be found.

            """
            ...

        async def run_process(
            command: StrOrBytesPath | Sequence[StrOrBytesPath],
            *,
            task_status: TaskStatus[Process] = trio.TASK_STATUS_IGNORED,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = None,
            capture_stdout: bool = False,
            capture_stderr: bool = False,
            check: bool = True,
            deliver_cancel: Callable[[Process], Awaitable[object]] | None = None,
            **kwargs: Unpack[WindowsProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]:
            """Run ``command`` in a subprocess and wait for it to complete.

            This function can be called in two different ways.

            One option is a direct call, like::

                completed_process_info = await trio.run_process(...)

            In this case, it returns a :class:`subprocess.CompletedProcess` instance
            describing the results. Use this if you want to treat a process like a
            function call.

            The other option is to run it as a task using `Nursery.start` – the enhanced version
            of `~Nursery.start_soon` that lets a task pass back a value during startup::

                process = await nursery.start(trio.run_process, ...)

            In this case, `~Nursery.start` returns a `Process` object that you can use
            to interact with the process while it's running. Use this if you want to
            treat a process like a background task.

            Either way, `run_process` makes sure that the process has exited before
            returning, handles cancellation, optionally checks for errors, and
            provides some convenient shorthands for dealing with the child's
            input/output.

            **Input:** `run_process` supports all the same ``stdin=`` arguments as
            `subprocess.Popen`. In addition, if you simply want to pass in some fixed
            data, you can pass a plain `bytes` object, and `run_process` will take
            care of setting up a pipe, feeding in the data you gave, and then sending
            end-of-file. The default is ``b""``, which means that the child will receive
            an empty stdin. If you want the child to instead read from the parent's
            stdin, use ``stdin=None``.

            **Output:** By default, any output produced by the subprocess is
            passed through to the standard output and error streams of the
            parent Trio process.

            When calling `run_process` directly, you can capture the subprocess's output by
            passing ``capture_stdout=True`` to capture the subprocess's standard output, and/or
            ``capture_stderr=True`` to capture its standard error. Captured data is collected up
            by Trio into an in-memory buffer, and then provided as the
            :attr:`~subprocess.CompletedProcess.stdout` and/or
            :attr:`~subprocess.CompletedProcess.stderr` attributes of the returned
            :class:`~subprocess.CompletedProcess` object. The value for any stream that was not
            captured will be ``None``.

            If you want to capture both stdout and stderr while keeping them
            separate, pass ``capture_stdout=True, capture_stderr=True``.

            If you want to capture both stdout and stderr but mixed together
            in the order they were printed, use: ``capture_stdout=True, stderr=subprocess.STDOUT``.
            This directs the child's stderr into its stdout, so the combined
            output will be available in the `~subprocess.CompletedProcess.stdout`
            attribute.

            If you're using ``await nursery.start(trio.run_process, ...)`` and want to capture
            the subprocess's output for further processing, then use ``stdout=subprocess.PIPE``
            and then make sure to read the data out of the `Process.stdout` stream. If you want
            to capture stderr separately, use ``stderr=subprocess.PIPE``. If you want to capture
            both, but mixed together in the correct order, use ``stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT``.

            **Error checking:** If the subprocess exits with a nonzero status
            code, indicating failure, :func:`run_process` raises a
            :exc:`subprocess.CalledProcessError` exception rather than
            returning normally. The captured outputs are still available as
            the :attr:`~subprocess.CalledProcessError.stdout` and
            :attr:`~subprocess.CalledProcessError.stderr` attributes of that
            exception.  To disable this behavior, so that :func:`run_process`
            returns normally even if the subprocess exits abnormally, pass ``check=False``.

            Note that this can make the ``capture_stdout`` and ``capture_stderr``
            arguments useful even when starting `run_process` as a task: if you only
            care about the output if the process fails, then you can enable capturing
            and then read the output off of the `~subprocess.CalledProcessError`.

            **Cancellation:** If cancelled, `run_process` sends a termination
            request to the subprocess, then waits for it to fully exit. The
            ``deliver_cancel`` argument lets you control how the process is terminated.

            .. note:: `run_process` is intentionally similar to the standard library
               `subprocess.run`, but some of the defaults are different. Specifically, we
               default to:

               - ``check=True``, because `"errors should never pass silently / unless
                 explicitly silenced" <https://www.python.org/dev/peps/pep-0020/>`__.

               - ``stdin=b""``, because it produces less-confusing results if a subprocess
                 unexpectedly tries to read from stdin.

               To get the `subprocess.run` semantics, use ``check=False, stdin=None``.

            Args:
              command (list or str): The command to run. Typically this is a
                  sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
                  where the first element names the executable to invoke and the other
                  elements specify its arguments. With ``shell=True`` in the
                  ``**options``, or on Windows, ``command`` may alternatively
                  be a string, which will be parsed following platform-dependent
                  :ref:`quoting rules <subprocess-quoting>`.

              stdin (:obj:`bytes`, subprocess.PIPE, file descriptor, or None): The
                  bytes to provide to the subprocess on its standard input stream, or
                  ``None`` if the subprocess's standard input should come from the
                  same place as the parent Trio process's standard input. As is the
                  case with the :mod:`subprocess` module, you can also pass a file
                  descriptor or an object with a ``fileno()`` method, in which case
                  the subprocess's standard input will come from that file.

                  When starting `run_process` as a background task, you can also use
                  ``stdin=subprocess.PIPE``, in which case `Process.stdin` will be a
                  `~trio.abc.SendStream` that you can use to send data to the child.

              capture_stdout (bool): If true, capture the bytes that the subprocess
                  writes to its standard output stream and return them in the
                  `~subprocess.CompletedProcess.stdout` attribute of the returned
                  `subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

              capture_stderr (bool): If true, capture the bytes that the subprocess
                  writes to its standard error stream and return them in the
                  `~subprocess.CompletedProcess.stderr` attribute of the returned
                  `~subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

              check (bool): If false, don't validate that the subprocess exits
                  successfully. You should be sure to check the
                  ``returncode`` attribute of the returned object if you pass
                  ``check=False``, so that errors don't pass silently.

              deliver_cancel (async function or None): If `run_process` is cancelled,
                  then it needs to kill the child process. There are multiple ways to
                  do this, so we let you customize it.

                  If you pass None (the default), then the behavior depends on the
                  platform:

                  - On Windows, Trio calls ``TerminateProcess``, which should kill the
                    process immediately.

                  - On Unix-likes, the default behavior is to send a ``SIGTERM``, wait
                    5 seconds, and send a ``SIGKILL``.

                  Alternatively, you can customize this behavior by passing in an
                  arbitrary async function, which will be called with the `Process`
                  object as an argument. For example, the default Unix behavior could
                  be implemented like this::

                     async def my_deliver_cancel(process):
                         process.send_signal(signal.SIGTERM)
                         await trio.sleep(5)
                         process.send_signal(signal.SIGKILL)

                  When the process actually exits, the ``deliver_cancel`` function
                  will automatically be cancelled – so if the process exits after
                  ``SIGTERM``, then we'll never reach the ``SIGKILL``.

                  In any case, `run_process` will always wait for the child process to
                  exit before raising `Cancelled`.

              **options: :func:`run_process` also accepts any :ref:`general subprocess
                  options <subprocess-options>` and passes them on to the
                  :class:`~trio.Process` constructor. This includes the
                  ``stdout`` and ``stderr`` options, which provide additional
                  redirection possibilities such as ``stderr=subprocess.STDOUT``,
                  ``stdout=subprocess.DEVNULL``, or file descriptors.

            Returns:

              When called normally – a `subprocess.CompletedProcess` instance
              describing the return code and outputs.

              When called via `Nursery.start` – a `trio.Process` instance.

            Raises:
              UnicodeError: if ``stdin`` is specified as a Unicode string, rather
                  than bytes
              ValueError: if multiple redirections are specified for the same
                  stream, e.g., both ``capture_stdout=True`` and
                  ``stdout=subprocess.DEVNULL``
              subprocess.CalledProcessError: if ``check=False`` is not passed
                  and the process exits with a nonzero exit status
              OSError: if an error is encountered starting or communicating with
                  the process

            .. note:: The child process runs in the same process group as the parent
               Trio process, so a Ctrl+C will be delivered simultaneously to both
               parent and child. If you don't want this behavior, consult your
               platform's documentation for starting child processes in a different
               process group.

            """
            ...

    else:  # Unix
        # pyright doesn't give any error about overloads missing docstrings as they're
        # overloads. But might still be a problem for other static analyzers / docstring
        # readers (?)

        class UnixProcessArgs3_10(GeneralProcessArgs, total=False):
            """Arguments shared between all Unix runs."""

            preexec_fn: Callable[[], object] | None
            restore_signals: bool
            start_new_session: bool
            pass_fds: Sequence[int]

            # 3.9+
            group: str | int | None
            extra_groups: Iterable[str | int] | None
            user: str | int | None
            umask: int

            # 3.10+
            pipesize: int

        class UnixProcessArgs3_11(UnixProcessArgs3_10, total=False):
            """Arguments shared between all Unix runs on 3.11+."""

            process_group: int | None

        class UnixRunProcessMixin(TypedDict, total=False):
            """Arguments unique to run_process on Unix."""

            task_status: TaskStatus[Process]
            capture_stdout: bool
            capture_stderr: bool
            check: bool
            deliver_cancel: Callable[[Process], Awaitable[None]] | None

        # TODO: once https://github.com/python/mypy/issues/18692 is
        #       fixed, move the `UnixRunProcessArgs` definition down.
        if sys.version_info >= (3, 11):
            UnixProcessArgs = UnixProcessArgs3_11

            class UnixRunProcessArgs(UnixProcessArgs3_11, UnixRunProcessMixin):
                """Arguments for run_process on Unix with 3.11+"""

        else:
            UnixProcessArgs = UnixProcessArgs3_10

            class UnixRunProcessArgs(UnixProcessArgs3_10, UnixRunProcessMixin):
                """Arguments for run_process on Unix with 3.10+"""

        @overload  # type: ignore[no-overload-impl]
        async def open_process(
            command: StrOrBytesPath,
            *,
            stdin: int | HasFileno | None = None,
            shell: Literal[True],
            **kwargs: Unpack[UnixProcessArgs],
        ) -> trio.Process: ...

        @overload
        async def open_process(
            command: Sequence[StrOrBytesPath],
            *,
            stdin: int | HasFileno | None = None,
            shell: bool = False,
            **kwargs: Unpack[UnixProcessArgs],
        ) -> trio.Process: ...

        @overload  # type: ignore[no-overload-impl]
        async def run_process(
            command: StrOrBytesPath,
            *,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = b"",
            shell: Literal[True],
            **kwargs: Unpack[UnixRunProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]: ...

        @overload
        async def run_process(
            command: Sequence[StrOrBytesPath],
            *,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = b"",
            shell: bool = False,
            **kwargs: Unpack[UnixRunProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]: ...

else:
    # At runtime, use the actual implementations.
    open_process = _open_process
    open_process.__name__ = open_process.__qualname__ = "open_process"

    run_process = _run_process
    run_process.__name__ = run_process.__qualname__ = "run_process"
