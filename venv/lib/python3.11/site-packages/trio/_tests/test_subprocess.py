from __future__ import annotations

import gc
import os
import random
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path as SyncPath
from signal import Signals
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    AsyncIterator,
    Callable,
    NoReturn,
)

import pytest

from .. import (
    Event,
    Process,
    _core,
    fail_after,
    move_on_after,
    run_process,
    sleep,
    sleep_forever,
)
from .._core._tests.tutil import skip_if_fbsd_pipes_broken, slow
from ..lowlevel import open_process
from ..testing import MockClock, assert_no_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from types import FrameType

    from typing_extensions import TypeAlias

    from .._abc import ReceiveStream

if sys.platform == "win32":
    SignalType: TypeAlias = None
else:
    SignalType: TypeAlias = Signals

SIGKILL: SignalType
SIGTERM: SignalType
SIGUSR1: SignalType

posix = os.name == "posix"
if (not TYPE_CHECKING and posix) or sys.platform != "win32":
    from signal import SIGKILL, SIGTERM, SIGUSR1
else:
    SIGKILL, SIGTERM, SIGUSR1 = None, None, None


# Since Windows has very few command-line utilities generally available,
# all of our subprocesses are Python processes running short bits of
# (mostly) cross-platform code.
def python(code: str) -> list[str]:
    return [sys.executable, "-u", "-c", "import sys; " + code]


EXIT_TRUE = python("sys.exit(0)")
EXIT_FALSE = python("sys.exit(1)")
CAT = python("sys.stdout.buffer.write(sys.stdin.buffer.read())")

if posix:

    def SLEEP(seconds: int) -> list[str]:
        return ["sleep", str(seconds)]

else:

    def SLEEP(seconds: int) -> list[str]:
        return python(f"import time; time.sleep({seconds})")


def got_signal(proc: Process, sig: SignalType) -> bool:
    if (not TYPE_CHECKING and posix) or sys.platform != "win32":
        return proc.returncode == -sig
    else:
        return proc.returncode != 0


@asynccontextmanager  # type: ignore[misc]  # Any in decorator
async def open_process_then_kill(*args: Any, **kwargs: Any) -> AsyncIterator[Process]:
    proc = await open_process(*args, **kwargs)
    try:
        yield proc
    finally:
        proc.kill()
        await proc.wait()


@asynccontextmanager  # type: ignore[misc]  # Any in decorator
async def run_process_in_nursery(*args: Any, **kwargs: Any) -> AsyncIterator[Process]:
    async with _core.open_nursery() as nursery:
        kwargs.setdefault("check", False)
        proc: Process = await nursery.start(partial(run_process, *args, **kwargs))
        yield proc
        nursery.cancel_scope.cancel()


background_process_param = pytest.mark.parametrize(
    "background_process",
    [open_process_then_kill, run_process_in_nursery],
    ids=["open_process", "run_process in nursery"],
)

BackgroundProcessType: TypeAlias = Callable[..., AsyncContextManager[Process]]


@background_process_param
async def test_basic(background_process: BackgroundProcessType) -> None:
    async with background_process(EXIT_TRUE) as proc:
        await proc.wait()
    assert isinstance(proc, Process)
    assert proc._pidfd is None
    assert proc.returncode == 0
    assert repr(proc) == f"<trio.Process {EXIT_TRUE}: exited with status 0>"

    async with background_process(EXIT_FALSE) as proc:
        await proc.wait()
    assert proc.returncode == 1
    assert repr(proc) == "<trio.Process {!r}: {}>".format(
        EXIT_FALSE, "exited with status 1"
    )


@background_process_param
async def test_auto_update_returncode(
    background_process: BackgroundProcessType,
) -> None:
    async with background_process(SLEEP(9999)) as p:
        assert p.returncode is None
        assert "running" in repr(p)
        p.kill()
        p._proc.wait()
        assert p.returncode is not None
        assert "exited" in repr(p)
        assert p._pidfd is None
        assert p.returncode is not None


@background_process_param
async def test_multi_wait(background_process: BackgroundProcessType) -> None:
    async with background_process(SLEEP(10)) as proc:
        # Check that wait (including multi-wait) tolerates being cancelled
        async with _core.open_nursery() as nursery:
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

        # Now try waiting for real
        async with _core.open_nursery() as nursery:
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            nursery.start_soon(proc.wait)
            await wait_all_tasks_blocked()
            proc.kill()


COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR = python(
    "data = sys.stdin.buffer.read(); "
    "sys.stdout.buffer.write(data); "
    "sys.stderr.buffer.write(data[::-1])"
)


@background_process_param
async def test_pipes(background_process: BackgroundProcessType) -> None:
    async with background_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        msg = b"the quick brown fox jumps over the lazy dog"

        async def feed_input() -> None:
            assert proc.stdin is not None
            await proc.stdin.send_all(msg)
            await proc.stdin.aclose()

        async def check_output(stream: ReceiveStream, expected: bytes) -> None:
            seen = bytearray()
            async for chunk in stream:
                seen += chunk
            assert seen == expected

        assert proc.stdout is not None
        assert proc.stderr is not None

        async with _core.open_nursery() as nursery:
            # fail eventually if something is broken
            nursery.cancel_scope.deadline = _core.current_time() + 30.0
            nursery.start_soon(feed_input)
            nursery.start_soon(check_output, proc.stdout, msg)
            nursery.start_soon(check_output, proc.stderr, msg[::-1])

        assert not nursery.cancel_scope.cancelled_caught
        assert await proc.wait() == 0


@background_process_param
async def test_interactive(background_process: BackgroundProcessType) -> None:
    # Test some back-and-forth with a subprocess. This one works like so:
    # in: 32\n
    # out: 0000...0000\n (32 zeroes)
    # err: 1111...1111\n (64 ones)
    # in: 10\n
    # out: 2222222222\n (10 twos)
    # err: 3333....3333\n (20 threes)
    # in: EOF
    # out: EOF
    # err: EOF

    async with background_process(
        python(
            "idx = 0\n"
            "while True:\n"
            "    line = sys.stdin.readline()\n"
            "    if line == '': break\n"
            "    request = int(line.strip())\n"
            "    print(str(idx * 2) * request)\n"
            "    print(str(idx * 2 + 1) * request * 2, file=sys.stderr)\n"
            "    idx += 1\n"
        ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        newline = b"\n" if posix else b"\r\n"

        async def expect(idx: int, request: int) -> None:
            async with _core.open_nursery() as nursery:

                async def drain_one(
                    stream: ReceiveStream, count: int, digit: int
                ) -> None:
                    while count > 0:
                        result = await stream.receive_some(count)
                        assert result == (f"{digit}".encode() * len(result))
                        count -= len(result)
                    assert count == 0
                    assert await stream.receive_some(len(newline)) == newline

                assert proc.stdout is not None
                assert proc.stderr is not None
                nursery.start_soon(drain_one, proc.stdout, request, idx * 2)
                nursery.start_soon(drain_one, proc.stderr, request * 2, idx * 2 + 1)

        assert proc.stdin is not None
        assert proc.stdout is not None
        assert proc.stderr is not None
        with fail_after(5):
            await proc.stdin.send_all(b"12")
            await sleep(0.1)
            await proc.stdin.send_all(b"345" + newline)
            await expect(0, 12345)
            await proc.stdin.send_all(b"100" + newline + b"200" + newline)
            await expect(1, 100)
            await expect(2, 200)
            await proc.stdin.send_all(b"0" + newline)
            await expect(3, 0)
            await proc.stdin.send_all(b"999999")
            with move_on_after(0.1) as scope:
                await expect(4, 0)
            assert scope.cancelled_caught
            await proc.stdin.send_all(newline)
            await expect(4, 999999)
            await proc.stdin.aclose()
            assert await proc.stdout.receive_some(1) == b""
            assert await proc.stderr.receive_some(1) == b""
            await proc.wait()

    assert proc.returncode == 0


async def test_run() -> None:
    data = bytes(random.randint(0, 255) for _ in range(2**18))

    result = await run_process(
        CAT, stdin=data, capture_stdout=True, capture_stderr=True
    )
    assert result.args == CAT
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == b""

    result = await run_process(CAT, capture_stdout=True)
    assert result.args == CAT
    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr is None

    result = await run_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=data,
        capture_stdout=True,
        capture_stderr=True,
    )
    assert result.args == COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == data[::-1]

    # invalid combinations
    with pytest.raises(UnicodeError):
        await run_process(CAT, stdin="oh no, it's text")

    pipe_stdout_error = r"^stdout=subprocess\.PIPE is only valid with nursery\.start, since that's the only way to access the pipe(; use nursery\.start or pass the data you want to write directly)*$"
    with pytest.raises(ValueError, match=pipe_stdout_error):
        await run_process(CAT, stdin=subprocess.PIPE)
    with pytest.raises(ValueError, match=pipe_stdout_error):
        await run_process(CAT, stdout=subprocess.PIPE)
    with pytest.raises(
        ValueError, match=pipe_stdout_error.replace("stdout", "stderr", 1)
    ):
        await run_process(CAT, stderr=subprocess.PIPE)
    with pytest.raises(
        ValueError,
        match="^can't specify both stdout and capture_stdout$",
    ):
        await run_process(CAT, capture_stdout=True, stdout=subprocess.DEVNULL)
    with pytest.raises(
        ValueError,
        match="^can't specify both stderr and capture_stderr$",
    ):
        await run_process(CAT, capture_stderr=True, stderr=None)


async def test_run_check() -> None:
    cmd = python("sys.stderr.buffer.write(b'test\\n'); sys.exit(1)")
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        await run_process(cmd, stdin=subprocess.DEVNULL, capture_stderr=True)
    assert excinfo.value.cmd == cmd
    assert excinfo.value.returncode == 1
    assert excinfo.value.stderr == b"test\n"
    assert excinfo.value.stdout is None

    result = await run_process(
        cmd, capture_stdout=True, capture_stderr=True, check=False
    )
    assert result.args == cmd
    assert result.stdout == b""
    assert result.stderr == b"test\n"
    assert result.returncode == 1


@skip_if_fbsd_pipes_broken
async def test_run_with_broken_pipe() -> None:
    result = await run_process(
        [sys.executable, "-c", "import sys; sys.stdin.close()"], stdin=b"x" * 131072
    )
    assert result.returncode == 0
    assert result.stdout is result.stderr is None


@background_process_param
async def test_stderr_stdout(background_process: BackgroundProcessType) -> None:
    async with background_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        assert proc.stdio is not None
        assert proc.stdout is not None
        assert proc.stderr is None
        await proc.stdio.send_all(b"1234")
        await proc.stdio.send_eof()

        output = []
        while True:
            chunk = await proc.stdio.receive_some(16)
            if chunk == b"":
                break
            output.append(chunk)
        assert b"".join(output) == b"12344321"
    assert proc.returncode == 0

    # equivalent test with run_process()
    result = await run_process(
        COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
        stdin=b"1234",
        capture_stdout=True,
        stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0
    assert result.stdout == b"12344321"
    assert result.stderr is None

    # this one hits the branch where stderr=STDOUT but stdout
    # is not redirected
    async with background_process(
        CAT, stdin=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as proc:
        assert proc.stdout is None
        assert proc.stderr is None
        await proc.stdin.aclose()
        await proc.wait()
    assert proc.returncode == 0

    if posix:
        try:
            r, w = os.pipe()

            async with background_process(
                COPY_STDIN_TO_STDOUT_AND_BACKWARD_TO_STDERR,
                stdin=subprocess.PIPE,
                stdout=w,
                stderr=subprocess.STDOUT,
            ) as proc:
                os.close(w)
                assert proc.stdio is None
                assert proc.stdout is None
                assert proc.stderr is None
                await proc.stdin.send_all(b"1234")
                await proc.stdin.aclose()
                assert await proc.wait() == 0
                assert os.read(r, 4096) == b"12344321"
                assert os.read(r, 4096) == b""
        finally:
            os.close(r)


async def test_errors() -> None:
    with pytest.raises(TypeError) as excinfo:
        # call-overload on unix, call-arg on windows
        await open_process(["ls"], encoding="utf-8")  # type: ignore
    assert "unbuffered byte streams" in str(excinfo.value)
    assert "the 'encoding' option is not supported" in str(excinfo.value)

    if posix:
        with pytest.raises(TypeError) as excinfo:
            await open_process(["ls"], shell=True)
        with pytest.raises(TypeError) as excinfo:
            await open_process("ls", shell=False)


@background_process_param
async def test_signals(background_process: BackgroundProcessType) -> None:
    async def test_one_signal(
        send_it: Callable[[Process], None], signum: signal.Signals | None
    ) -> None:
        with move_on_after(1.0) as scope:
            async with background_process(SLEEP(3600)) as proc:
                send_it(proc)
                await proc.wait()
        assert not scope.cancelled_caught
        if posix:
            assert signum is not None
            assert proc.returncode == -signum
        else:
            assert proc.returncode != 0

    await test_one_signal(Process.kill, SIGKILL)
    await test_one_signal(Process.terminate, SIGTERM)
    # Test that we can send arbitrary signals.
    #
    # We used to use SIGINT here, but it turns out that the Python interpreter
    # has race conditions that can cause it to explode in weird ways if it
    # tries to handle SIGINT during startup. SIGUSR1's default disposition is
    # to terminate the target process, and Python doesn't try to do anything
    # clever to handle it.
    if (not TYPE_CHECKING and posix) or sys.platform != "win32":
        await test_one_signal(lambda proc: proc.send_signal(SIGUSR1), SIGUSR1)


@pytest.mark.skipif(not posix, reason="POSIX specific")
@background_process_param
async def test_wait_reapable_fails(background_process: BackgroundProcessType) -> None:
    if TYPE_CHECKING and sys.platform == "win32":
        return
    old_sigchld = signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    try:
        # With SIGCHLD disabled, the wait() syscall will wait for the
        # process to exit but then fail with ECHILD. Make sure we
        # support this case as the stdlib subprocess module does.
        async with background_process(SLEEP(3600)) as proc:
            async with _core.open_nursery() as nursery:
                nursery.start_soon(proc.wait)
                await wait_all_tasks_blocked()
                proc.kill()
                nursery.cancel_scope.deadline = _core.current_time() + 1.0
            assert not nursery.cancel_scope.cancelled_caught
            assert proc.returncode == 0  # exit status unknowable, so...
    finally:
        signal.signal(signal.SIGCHLD, old_sigchld)


@slow
def test_waitid_eintr() -> None:
    # This only matters on PyPy (where we're coding EINTR handling
    # ourselves) but the test works on all waitid platforms.
    from .._subprocess_platform import wait_child_exiting

    if TYPE_CHECKING and (sys.platform == "win32" or sys.platform == "darwin"):
        return

    if not wait_child_exiting.__module__.endswith("waitid"):
        pytest.skip("waitid only")

    # despite the TYPE_CHECKING early return silencing warnings about signal.SIGALRM etc
    # this import is still checked on win32&darwin and raises [attr-defined].
    # Linux doesn't raise [attr-defined] though, so we need [unused-ignore]
    from .._subprocess_platform.waitid import (  # type: ignore[attr-defined, unused-ignore]
        sync_wait_reapable,
    )

    got_alarm = False
    sleeper = subprocess.Popen(["sleep", "3600"])

    def on_alarm(sig: int, frame: FrameType | None) -> None:
        nonlocal got_alarm
        got_alarm = True
        sleeper.kill()

    old_sigalrm = signal.signal(signal.SIGALRM, on_alarm)
    try:
        signal.alarm(1)
        sync_wait_reapable(sleeper.pid)
        assert sleeper.wait(timeout=1) == -9
    finally:
        if sleeper.returncode is None:  # pragma: no cover
            # We only get here if something fails in the above;
            # if the test passes, wait() will reap the process
            sleeper.kill()
            sleeper.wait()
        signal.signal(signal.SIGALRM, old_sigalrm)


async def test_custom_deliver_cancel() -> None:
    custom_deliver_cancel_called = False

    async def custom_deliver_cancel(proc: Process) -> None:
        nonlocal custom_deliver_cancel_called
        custom_deliver_cancel_called = True
        proc.terminate()
        # Make sure this does get cancelled when the process exits, and that
        # the process really exited.
        try:
            await sleep_forever()
        finally:
            assert proc.returncode is not None

    async with _core.open_nursery() as nursery:
        nursery.start_soon(
            partial(run_process, SLEEP(9999), deliver_cancel=custom_deliver_cancel)
        )
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()

    assert custom_deliver_cancel_called


async def test_warn_on_failed_cancel_terminate(monkeypatch: pytest.MonkeyPatch) -> None:
    original_terminate = Process.terminate

    def broken_terminate(self: Process) -> NoReturn:
        original_terminate(self)
        raise OSError("whoops")

    monkeypatch.setattr(Process, "terminate", broken_terminate)

    with pytest.warns(RuntimeWarning, match=".*whoops.*"):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(run_process, SLEEP(9999))
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()


@pytest.mark.skipif(not posix, reason="posix only")
async def test_warn_on_cancel_SIGKILL_escalation(
    autojump_clock: MockClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Process, "terminate", lambda *args: None)

    with pytest.warns(RuntimeWarning, match=".*ignored SIGTERM.*"):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(run_process, SLEEP(9999))
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()


# the background_process_param exercises a lot of run_process cases, but it uses
# check=False, so lets have a test that uses check=True as well
async def test_run_process_background_fail() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        async with _core.open_nursery() as nursery:
            proc: Process = await nursery.start(run_process, EXIT_FALSE)
    assert proc.returncode == 1


@pytest.mark.skipif(
    not SyncPath("/dev/fd").exists(),
    reason="requires a way to iterate through open files",
)
async def test_for_leaking_fds() -> None:
    gc.collect()  # address possible flakiness on PyPy

    starting_fds = set(SyncPath("/dev/fd").iterdir())
    await run_process(EXIT_TRUE)
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds

    with pytest.raises(subprocess.CalledProcessError):
        await run_process(EXIT_FALSE)
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds

    with pytest.raises(PermissionError):
        await run_process(["/dev/fd/0"])
    assert set(SyncPath("/dev/fd").iterdir()) == starting_fds


# regression test for #2209
async def test_subprocess_pidfd_unnotified() -> None:
    noticed_exit = None

    async def wait_and_tell(proc: Process) -> None:
        nonlocal noticed_exit
        noticed_exit = Event()
        await proc.wait()
        noticed_exit.set()

    proc = await open_process(SLEEP(9999))
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_and_tell, proc)
        await wait_all_tasks_blocked()
        assert isinstance(noticed_exit, Event)
        proc.terminate()
        # without giving trio a chance to do so,
        with assert_no_checkpoints():
            # wait until the process has actually exited;
            proc._proc.wait()
            # force a call to poll (that closes the pidfd on linux)
            proc.poll()
        with move_on_after(5):
            # Some platforms use threads to wait for exit, so it might take a bit
            # for everything to notice
            await noticed_exit.wait()
        assert noticed_exit.is_set(), "child task wasn't woken after poll, DEADLOCK"
