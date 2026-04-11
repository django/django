import sys

import trio


async def test() -> None:
    # this could test more by using platform checks, but currently this
    # is just regression tests + sanity checks.
    await trio.run_process("python", executable="ls")
    await trio.lowlevel.open_process("python", executable="ls")

    # note: there's no error code on the type ignore as it varies
    # between platforms.
    await trio.run_process("python", capture_stdout=True)
    await trio.lowlevel.open_process("python", capture_stdout=True)  # type: ignore

    if sys.platform != "win32" and sys.version_info >= (3, 9):
        await trio.run_process("python", extra_groups=[5])
        await trio.lowlevel.open_process("python", extra_groups=[5])

        # 3.11+:
        await trio.run_process("python", process_group=5)  # type: ignore
        await trio.lowlevel.open_process("python", process_group=5)  # type: ignore
