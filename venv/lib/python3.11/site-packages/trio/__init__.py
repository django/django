"""Trio - A friendly Python library for async concurrency and I/O
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# General layout:
#
# trio/_core/... is the self-contained core library. It does various
# shenanigans to export a consistent "core API", but parts of the core API are
# too low-level to be recommended for regular use.
#
# trio/*.py define a set of more usable tools on top of this. They import from
# trio._core and from each other.
#
# This file pulls together the friendly public API, by re-exporting the more
# innocuous bits of the _core API + the higher-level tools from trio/*.py.
#
# Uses `from x import y as y` for compatibility with `pyright --verifytypes` (#2625)
#
# must be imported early to avoid circular import
from ._core import TASK_STATUS_IGNORED as TASK_STATUS_IGNORED  # isort: split

# Submodules imported by default
from . import abc, from_thread, lowlevel, socket, to_thread
from ._channel import (
    MemoryReceiveChannel as MemoryReceiveChannel,
    MemorySendChannel as MemorySendChannel,
    open_memory_channel as open_memory_channel,
)
from ._core import (
    BrokenResourceError as BrokenResourceError,
    BusyResourceError as BusyResourceError,
    Cancelled as Cancelled,
    CancelScope as CancelScope,
    ClosedResourceError as ClosedResourceError,
    EndOfChannel as EndOfChannel,
    Nursery as Nursery,
    RunFinishedError as RunFinishedError,
    TaskStatus as TaskStatus,
    TrioInternalError as TrioInternalError,
    WouldBlock as WouldBlock,
    current_effective_deadline as current_effective_deadline,
    current_time as current_time,
    open_nursery as open_nursery,
    run as run,
)
from ._deprecate import TrioDeprecationWarning as TrioDeprecationWarning
from ._dtls import (
    DTLSChannel as DTLSChannel,
    DTLSChannelStatistics as DTLSChannelStatistics,
    DTLSEndpoint as DTLSEndpoint,
)
from ._file_io import open_file as open_file, wrap_file as wrap_file
from ._highlevel_generic import (
    StapledStream as StapledStream,
    aclose_forcefully as aclose_forcefully,
)
from ._highlevel_open_tcp_listeners import (
    open_tcp_listeners as open_tcp_listeners,
    serve_tcp as serve_tcp,
)
from ._highlevel_open_tcp_stream import open_tcp_stream as open_tcp_stream
from ._highlevel_open_unix_stream import open_unix_socket as open_unix_socket
from ._highlevel_serve_listeners import serve_listeners as serve_listeners
from ._highlevel_socket import (
    SocketListener as SocketListener,
    SocketStream as SocketStream,
)
from ._highlevel_ssl_helpers import (
    open_ssl_over_tcp_listeners as open_ssl_over_tcp_listeners,
    open_ssl_over_tcp_stream as open_ssl_over_tcp_stream,
    serve_ssl_over_tcp as serve_ssl_over_tcp,
)
from ._path import Path as Path
from ._signals import open_signal_receiver as open_signal_receiver
from ._ssl import (
    NeedHandshakeError as NeedHandshakeError,
    SSLListener as SSLListener,
    SSLStream as SSLStream,
)
from ._subprocess import Process as Process, run_process as run_process
from ._sync import (
    CapacityLimiter as CapacityLimiter,
    CapacityLimiterStatistics as CapacityLimiterStatistics,
    Condition as Condition,
    ConditionStatistics as ConditionStatistics,
    Event as Event,
    EventStatistics as EventStatistics,
    Lock as Lock,
    LockStatistics as LockStatistics,
    Semaphore as Semaphore,
    StrictFIFOLock as StrictFIFOLock,
)
from ._timeouts import (
    TooSlowError as TooSlowError,
    fail_after as fail_after,
    fail_at as fail_at,
    move_on_after as move_on_after,
    move_on_at as move_on_at,
    sleep as sleep,
    sleep_forever as sleep_forever,
    sleep_until as sleep_until,
)

# pyright explicitly does not care about `__version__`
# see https://github.com/microsoft/pyright/blob/main/docs/typed-libraries.md#type-completeness
from ._version import __version__

# Not imported by default, but mentioned here so static analysis tools like
# pylint will know that it exists.
if TYPE_CHECKING:
    from . import testing

from . import _deprecate as _deprecate

_deprecate.enable_attribute_deprecations(__name__)

__deprecated_attributes__: dict[str, _deprecate.DeprecatedAttribute] = {}

# Having the public path in .__module__ attributes is important for:
# - exception names in printed tracebacks
# - sphinx :show-inheritance:
# - deprecation warnings
# - pickle
# - probably other stuff
from ._util import fixup_module_metadata

fixup_module_metadata(__name__, globals())
fixup_module_metadata(lowlevel.__name__, lowlevel.__dict__)
fixup_module_metadata(socket.__name__, socket.__dict__)
fixup_module_metadata(abc.__name__, abc.__dict__)
fixup_module_metadata(from_thread.__name__, from_thread.__dict__)
fixup_module_metadata(to_thread.__name__, to_thread.__dict__)
del fixup_module_metadata
del TYPE_CHECKING
