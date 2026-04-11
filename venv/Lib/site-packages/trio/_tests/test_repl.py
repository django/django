from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
from functools import partial
from typing import Protocol

import pytest

import trio._repl


class RawInput(Protocol):
    def __call__(self, prompt: str = "") -> str: ...


def build_raw_input(cmds: list[str]) -> RawInput:
    """
    Pass in a list of strings.
    Returns a callable that returns each string, each time its called
    When there are not more strings to return, raise EOFError
    """
    cmds_iter = iter(cmds)
    prompts = []

    def _raw_helper(prompt: str = "") -> str:
        prompts.append(prompt)
        try:
            return next(cmds_iter)
        except StopIteration:
            raise EOFError from None

    return _raw_helper


def test_build_raw_input() -> None:
    """Quick test of our helper function."""
    raw_input = build_raw_input(["cmd1"])
    assert raw_input() == "cmd1"
    with pytest.raises(EOFError):
        raw_input()


async def test_basic_interaction(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Run some basic commands through the interpreter while capturing stdout.
    Ensure that the interpreted prints the expected results.
    """
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            # evaluate simple expression and recall the value
            "x = 1",
            "print(f'{x=}')",
            # Literal gets printed
            "'hello'",
            # define and call sync function
            "def func():",
            "  print(x + 1)",
            "",
            "func()",
            # define and call async function
            "async def afunc():",
            "  return 4",
            "",
            "await afunc()",
            # import works
            "import sys",
            "sys.stdout.write('hello stdout\\n')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert out.splitlines() == ["x=1", "'hello'", "2", "4", "hello stdout", "13"]


async def test_system_exits_quit_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            "raise SystemExit",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    with pytest.raises(SystemExit):
        await trio._repl.run_repl(console)


async def test_KI_interrupts(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            "import signal, trio, trio.lowlevel",
            "async def f():",
            "  trio.lowlevel.spawn_system_task("
            "    trio.to_thread.run_sync,"
            "    signal.raise_signal, signal.SIGINT,"
            "  )",  # just awaiting this kills the test runner?!
            "  await trio.sleep_forever()",
            "  print('should not see this')",
            "",
            "await f()",
            "print('AFTER KeyboardInterrupt')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "KeyboardInterrupt" in err
    assert "should" not in out
    assert "AFTER KeyboardInterrupt" in out


async def test_system_exits_in_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup('', [RuntimeError(), SystemExit()])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_system_exits_in_nested_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup(",
            "  '', [BaseExceptionGroup('', [RuntimeError(), SystemExit()])])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_base_exception_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise BaseException",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


async def test_exc_group_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise ExceptionGroup('', [KeyError()])",
            "print('AFTER ExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert "AFTER ExceptionGroup" in out


async def test_base_exception_capture_from_coroutine(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole()
    raw_input = build_raw_input(
        [
            "async def async_func_raises_base_exception():",
            "  raise BaseException",
            "",
            # This will raise, but the statement after should still
            # be executed
            "await async_func_raises_base_exception()",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


def test_main_entrypoint() -> None:
    """
    Basic smoke test when running via the package __main__ entrypoint.
    """
    repl = subprocess.run([sys.executable, "-m", "trio"], input=b"exit()")
    assert repl.returncode == 0


def should_try_newline_injection() -> bool:
    if sys.platform != "linux":
        return False

    sysctl = pathlib.Path("/proc/sys/dev/tty/legacy_tiocsti")
    if not sysctl.exists():  # pragma: no cover
        return True

    else:
        return sysctl.read_text() == "1"


@pytest.mark.skipif(
    not should_try_newline_injection(),
    reason="the ioctl we use is disabled in CI",
)
def test_ki_newline_injection() -> None:  # TODO: test this line
    # TODO: we want to remove this functionality, eg by using vendored
    #       pyrepls.
    assert sys.platform != "win32"

    import pty

    # NOTE: this cannot be subprocess.Popen because pty.fork
    #       does some magic to set the controlling terminal.
    # (which I don't know how to replicate... so I copied this
    # structure from pty.spawn...)
    pid, pty_fd = pty.fork()  # type: ignore[attr-defined,unused-ignore]
    if pid == 0:
        os.execlp(sys.executable, *[sys.executable, "-u", "-m", "trio"])

    # setup:
    buffer = b""
    while not buffer.endswith(b"import trio\r\n>>> "):
        buffer += os.read(pty_fd, 4096)

    # sanity check:
    print(buffer.decode())
    buffer = b""
    os.write(pty_fd, b'print("hello!")\n')
    while not buffer.endswith(b">>> "):
        buffer += os.read(pty_fd, 4096)

    assert buffer.count(b"hello!") == 2

    # press ctrl+c
    print(buffer.decode())
    buffer = b""
    os.kill(pid, signal.SIGINT)
    while not buffer.endswith(b">>> "):
        buffer += os.read(pty_fd, 4096)

    assert b"KeyboardInterrupt" in buffer

    # press ctrl+c later
    print(buffer.decode())
    buffer = b""
    os.write(pty_fd, b'print("hello!")')
    os.kill(pid, signal.SIGINT)
    while not buffer.endswith(b">>> "):
        buffer += os.read(pty_fd, 4096)

    assert b"KeyboardInterrupt" in buffer
    print(buffer.decode())
    os.close(pty_fd)
    os.waitpid(pid, 0)[1]


async def test_ki_in_repl() -> None:
    async with trio.open_nursery() as nursery:
        proc = await nursery.start(
            partial(
                trio.run_process,
                [sys.executable, "-u", "-m", "trio"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,  # type: ignore[attr-defined,unused-ignore]
            )
        )

        async with proc.stdout:
            # setup
            buffer = b""
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                # TODO: consider making run_process stdout have some universal newlines thing
                if buffer.replace(b"\r\n", b"\n").endswith(b"import trio\n>>> "):
                    break

            # ensure things work
            print(buffer.decode())
            buffer = b""
            await proc.stdin.send_all(b'print("hello!")\n')
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                if buffer.endswith(b">>> "):
                    break

            assert b"hello!" in buffer
            print(buffer.decode())

            # this seems to be necessary on Windows for reasons
            # (the parents of process groups ignore ctrl+c by default...)
            if sys.platform == "win32":
                buffer = b""
                await proc.stdin.send_all(
                    b"import ctypes; ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)\n"
                )
                async for part in proc.stdout:  # pragma: no branch
                    buffer += part
                    if buffer.endswith(b">>> "):
                        break

                print(buffer.decode())

            # try to decrease flakiness...
            buffer = b""
            await proc.stdin.send_all(
                b"import coverage; trio.lowlevel.enable_ki_protection(coverage.pytracer.PyTracer._trace)\n"
            )
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                if buffer.endswith(b">>> "):
                    break

            print(buffer.decode())

            # ensure that ctrl+c on a prompt works
            # NOTE: for some reason, signal.SIGINT doesn't work for this test.
            # Using CTRL_C_EVENT is also why we need subprocess.CREATE_NEW_PROCESS_GROUP
            signal_sent = signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT  # type: ignore[attr-defined,unused-ignore]
            os.kill(proc.pid, signal_sent)
            if sys.platform == "win32":
                # we rely on EOFError which... doesn't happen with pipes.
                # I'm not sure how to fix it...
                await proc.stdin.send_all(b"\n")
            else:
                # we test injection separately
                await proc.stdin.send_all(b"\n")

            buffer = b""
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                if buffer.endswith(b">>> "):
                    break

            assert b"KeyboardInterrupt" in buffer

            # ensure ctrl+c while a command runs works
            print(buffer.decode())
            await proc.stdin.send_all(b'print("READY"); await trio.sleep_forever()\n')
            killed = False
            buffer = b""
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                if buffer.replace(b"\r\n", b"\n").endswith(b"READY\n") and not killed:
                    os.kill(proc.pid, signal_sent)
                    killed = True
                if buffer.endswith(b">>> "):
                    break

            assert b"trio" in buffer
            assert b"KeyboardInterrupt" in buffer

            # make sure it works for sync commands too
            # (though this would be hard to break)
            print(buffer.decode())
            await proc.stdin.send_all(
                b'import time; print("READY"); time.sleep(99999)\n'
            )
            killed = False
            buffer = b""
            async for part in proc.stdout:  # pragma: no branch
                buffer += part
                if buffer.replace(b"\r\n", b"\n").endswith(b"READY\n") and not killed:
                    os.kill(proc.pid, signal_sent)
                    killed = True
                if buffer.endswith(b">>> "):
                    break

            assert b"Traceback" in buffer
            assert b"KeyboardInterrupt" in buffer

            print(buffer.decode())

        # kill the process
        nursery.cancel_scope.cancel()
