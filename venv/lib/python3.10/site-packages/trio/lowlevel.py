"""
This namespace represents low-level functionality not intended for daily use,
but useful for extending Trio's functionality.
"""

import select as _select
import sys
import typing as _t

# Generally available symbols
from ._core import (
    Abort as Abort,
    ParkingLot as ParkingLot,
    RaiseCancelT as RaiseCancelT,
    RunVar as RunVar,
    Task as Task,
    TrioToken as TrioToken,
    UnboundedQueue as UnboundedQueue,
    add_instrument as add_instrument,
    cancel_shielded_checkpoint as cancel_shielded_checkpoint,
    checkpoint as checkpoint,
    checkpoint_if_cancelled as checkpoint_if_cancelled,
    current_clock as current_clock,
    current_root_task as current_root_task,
    current_statistics as current_statistics,
    current_task as current_task,
    current_trio_token as current_trio_token,
    currently_ki_protected as currently_ki_protected,
    disable_ki_protection as disable_ki_protection,
    enable_ki_protection as enable_ki_protection,
    notify_closing as notify_closing,
    permanently_detach_coroutine_object as permanently_detach_coroutine_object,
    reattach_detached_coroutine_object as reattach_detached_coroutine_object,
    remove_instrument as remove_instrument,
    reschedule as reschedule,
    spawn_system_task as spawn_system_task,
    start_guest_run as start_guest_run,
    start_thread_soon as start_thread_soon,
    temporarily_detach_coroutine_object as temporarily_detach_coroutine_object,
    wait_readable as wait_readable,
    wait_task_rescheduled as wait_task_rescheduled,
    wait_writable as wait_writable,
)
from ._subprocess import open_process as open_process

# This is the union of a subset of trio/_core/ and some things from trio/*.py.
# See comments in trio/__init__.py for details.

# Uses `from x import y as y` for compatibility with `pyright --verifytypes` (#2625)


if sys.platform == "win32":
    # Windows symbols
    from ._core import (
        current_iocp as current_iocp,
        monitor_completion_key as monitor_completion_key,
        readinto_overlapped as readinto_overlapped,
        register_with_iocp as register_with_iocp,
        wait_overlapped as wait_overlapped,
        write_overlapped as write_overlapped,
    )
    from ._wait_for_object import WaitForSingleObject as WaitForSingleObject
else:
    # Unix symbols
    from ._unix_pipes import FdStream as FdStream

    # Kqueue-specific symbols
    if sys.platform != "linux" and (_t.TYPE_CHECKING or not hasattr(_select, "epoll")):
        from ._core import (
            current_kqueue as current_kqueue,
            monitor_kevent as monitor_kevent,
            wait_kevent as wait_kevent,
        )

del sys
