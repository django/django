from typing import TYPE_CHECKING

from .._wait_for_object import WaitForSingleObject

if TYPE_CHECKING:
    from .. import _subprocess


async def wait_child_exiting(process: "_subprocess.Process") -> None:
    # _handle is not in Popen stubs, though it is present on Windows.
    await WaitForSingleObject(int(process._proc._handle))  # type: ignore[attr-defined]
