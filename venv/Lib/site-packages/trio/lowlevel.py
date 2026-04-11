"""
This namespace represents low-level functionality not intended for daily use,
but useful for extending Trio's functionality.
"""

# imports are renamed with leading underscores to indicate they are not part of the public API
import select as _select

# static checkers don't understand if importing this as _sys, so it's deleted later
import sys
import typing as _t

# Generally available symbols
from ._core import (
    Abort as Abort,
    ParkingLot as ParkingLot,
    ParkingLotStatistics as ParkingLotStatistics,
    RaiseCancelT as RaiseCancelT,
    RunStatistics as RunStatistics,
    RunVar as RunVar,
    RunVarToken as RunVarToken,
    Task as Task,
    TrioToken as TrioToken,
    UnboundedQueue as UnboundedQueue,
    UnboundedQueueStatistics as UnboundedQueueStatistics,
    add_instrument as add_instrument,
    add_parking_lot_breaker as add_parking_lot_breaker,
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
    in_trio_run as in_trio_run,
    in_trio_task as in_trio_task,
    notify_closing as notify_closing,
    permanently_detach_coroutine_object as permanently_detach_coroutine_object,
    reattach_detached_coroutine_object as reattach_detached_coroutine_object,
    remove_instrument as remove_instrument,
    remove_parking_lot_breaker as remove_parking_lot_breaker,
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

if sys.platform == "win32" or (
    not _t.TYPE_CHECKING and "sphinx.ext.autodoc" in sys.modules
):
    # Windows symbols
    from ._core import (
        current_iocp as current_iocp,
        monitor_completion_key as monitor_completion_key,
        readinto_overlapped as readinto_overlapped,
        register_with_iocp as register_with_iocp,
        wait_overlapped as wait_overlapped,
        write_overlapped as write_overlapped,
    )

    # don't let documentation import the actual implementation
    if sys.platform == "win32":  # pragma: no branch
        from ._wait_for_object import WaitForSingleObject as WaitForSingleObject

if sys.platform != "win32" or (
    not _t.TYPE_CHECKING and "sphinx.ext.autodoc" in sys.modules
):
    # Unix symbols
    from ._unix_pipes import FdStream as FdStream

    # Kqueue-specific symbols
    if (
        sys.platform != "linux" and (_t.TYPE_CHECKING or not hasattr(_select, "epoll"))
    ) or (not _t.TYPE_CHECKING and "sphinx.ext.autodoc" in sys.modules):
        from ._core import (
            current_kqueue as current_kqueue,
            monitor_kevent as monitor_kevent,
            wait_kevent as wait_kevent,
        )

del sys
