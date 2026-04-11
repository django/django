from __future__ import annotations

import enum
from typing import TYPE_CHECKING, NewType, NoReturn, Protocol, TypeAlias, cast

if TYPE_CHECKING:
    import cffi

    CData: TypeAlias = cffi.api.FFI.CData
    CType: TypeAlias = cffi.api.FFI.CType

from ._generated_windows_ffi import ffi

################################################################
# Functions and types
################################################################

if not TYPE_CHECKING:
    CData: TypeAlias = ffi.CData
    CType: TypeAlias = ffi.CType

AlwaysNull: TypeAlias = CData  # We currently always pass ffi.NULL here.
Handle = NewType("Handle", CData)
HandleArray = NewType("HandleArray", CData)


class _Kernel32(Protocol):
    """Statically typed version of the kernel32.dll functions we use."""

    def CreateIoCompletionPort(
        self,
        FileHandle: Handle,
        ExistingCompletionPort: CData | AlwaysNull,
        CompletionKey: int,
        NumberOfConcurrentThreads: int,
        /,
    ) -> Handle: ...

    def CreateEventA(
        self,
        lpEventAttributes: AlwaysNull,
        bManualReset: bool,
        bInitialState: bool,
        lpName: AlwaysNull,
        /,
    ) -> Handle: ...

    def SetFileCompletionNotificationModes(
        self,
        handle: Handle,
        flags: CompletionModes,
        /,
    ) -> int: ...

    def PostQueuedCompletionStatus(
        self,
        CompletionPort: Handle,
        dwNumberOfBytesTransferred: int,
        dwCompletionKey: int,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool: ...

    def CancelIoEx(
        self,
        hFile: Handle,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool: ...

    def WriteFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToWrite: int,
        lpNumberOfBytesWritten: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool: ...

    def ReadFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToRead: int,
        lpNumberOfBytesRead: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool: ...

    def GetQueuedCompletionStatusEx(
        self,
        CompletionPort: Handle,
        lpCompletionPortEntries: CData,
        ulCount: int,
        ulNumEntriesRemoved: CData,
        dwMilliseconds: int,
        fAlertable: bool | int,
        /,
    ) -> CData: ...

    def CreateFileW(
        self,
        lpFileName: CData,
        dwDesiredAccess: FileFlags,
        dwShareMode: FileFlags,
        lpSecurityAttributes: AlwaysNull,
        dwCreationDisposition: FileFlags,
        dwFlagsAndAttributes: FileFlags,
        hTemplateFile: AlwaysNull,
        /,
    ) -> Handle: ...

    def WaitForSingleObject(self, hHandle: Handle, dwMilliseconds: int, /) -> CData: ...

    def WaitForMultipleObjects(
        self,
        nCount: int,
        lpHandles: HandleArray,
        bWaitAll: bool,
        dwMilliseconds: int,
        /,
    ) -> ErrorCodes: ...

    def SetEvent(self, handle: Handle, /) -> None: ...

    def CloseHandle(self, handle: Handle, /) -> bool: ...

    def DeviceIoControl(
        self,
        hDevice: Handle,
        dwIoControlCode: int,
        # this is wrong (it's not always null)
        lpInBuffer: AlwaysNull,
        nInBufferSize: int,
        # this is also wrong
        lpOutBuffer: AlwaysNull,
        nOutBufferSize: int,
        lpBytesReturned: AlwaysNull,
        lpOverlapped: CData,
        /,
    ) -> bool: ...


class _Nt(Protocol):
    """Statically typed version of the dtdll.dll functions we use."""

    def RtlNtStatusToDosError(self, status: int, /) -> ErrorCodes: ...


class _Ws2(Protocol):
    """Statically typed version of the ws2_32.dll functions we use."""

    def WSAGetLastError(self) -> int: ...

    def WSAIoctl(
        self,
        socket: CData,
        dwIoControlCode: WSAIoctls,
        lpvInBuffer: AlwaysNull,
        cbInBuffer: int,
        lpvOutBuffer: CData,
        cbOutBuffer: int,
        lpcbBytesReturned: CData,  # int*
        lpOverlapped: AlwaysNull,
        # actually LPWSAOVERLAPPED_COMPLETION_ROUTINE
        lpCompletionRoutine: AlwaysNull,
        /,
    ) -> int: ...


class _DummyStruct(Protocol):
    Offset: int
    OffsetHigh: int


class _DummyUnion(Protocol):
    DUMMYSTRUCTNAME: _DummyStruct
    Pointer: object


class _Overlapped(Protocol):
    Internal: int
    InternalHigh: int
    DUMMYUNIONNAME: _DummyUnion
    hEvent: Handle


kernel32 = cast("_Kernel32", ffi.dlopen("kernel32.dll"))
ntdll = cast("_Nt", ffi.dlopen("ntdll.dll"))
ws2_32 = cast("_Ws2", ffi.dlopen("ws2_32.dll"))

################################################################
# Magic numbers
################################################################

# Here's a great resource for looking these up:
#   https://www.magnumdb.com
# (Tip: check the box to see "Hex value")

INVALID_HANDLE_VALUE = Handle(ffi.cast("HANDLE", -1))


class ErrorCodes(enum.IntEnum):
    STATUS_TIMEOUT = 0x102
    WAIT_TIMEOUT = 0x102
    WAIT_ABANDONED = 0x80
    WAIT_OBJECT_0 = 0x00  # object is signaled
    WAIT_FAILED = 0xFFFFFFFF
    ERROR_IO_PENDING = 997
    ERROR_OPERATION_ABORTED = 995
    ERROR_ABANDONED_WAIT_0 = 735
    ERROR_INVALID_HANDLE = 6
    ERROR_INVALID_PARAMETER = 87
    ERROR_NOT_FOUND = 1168
    ERROR_NOT_SOCKET = 10038


class FileFlags(enum.IntFlag):
    GENERIC_READ = 0x80000000
    SYNCHRONIZE = 0x00100000
    FILE_FLAG_OVERLAPPED = 0x40000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    FILE_SHARE_DELETE = 4
    CREATE_NEW = 1
    CREATE_ALWAYS = 2
    OPEN_EXISTING = 3
    OPEN_ALWAYS = 4
    TRUNCATE_EXISTING = 5


class AFDPollFlags(enum.IntFlag):
    # These are drawn from a combination of:
    #   https://github.com/piscisaureus/wepoll/blob/master/src/afd.h
    #   https://github.com/reactos/reactos/blob/master/sdk/include/reactos/drivers/afd/shared.h
    AFD_POLL_RECEIVE = 0x0001
    AFD_POLL_RECEIVE_EXPEDITED = 0x0002  # OOB/urgent data
    AFD_POLL_SEND = 0x0004
    AFD_POLL_DISCONNECT = 0x0008  # received EOF (FIN)
    AFD_POLL_ABORT = 0x0010  # received RST
    AFD_POLL_LOCAL_CLOSE = 0x0020  # local socket object closed
    AFD_POLL_CONNECT = 0x0040  # socket is successfully connected
    AFD_POLL_ACCEPT = 0x0080  # you can call accept on this socket
    AFD_POLL_CONNECT_FAIL = 0x0100  # connect() terminated unsuccessfully
    # See WSAEventSelect docs for more details on these four:
    AFD_POLL_QOS = 0x0200
    AFD_POLL_GROUP_QOS = 0x0400
    AFD_POLL_ROUTING_INTERFACE_CHANGE = 0x0800
    AFD_POLL_EVENT_ADDRESS_LIST_CHANGE = 0x1000


class WSAIoctls(enum.IntEnum):
    SIO_BASE_HANDLE = 0x48000022
    SIO_BSP_HANDLE_SELECT = 0x4800001C
    SIO_BSP_HANDLE_POLL = 0x4800001D


class CompletionModes(enum.IntFlag):
    FILE_SKIP_COMPLETION_PORT_ON_SUCCESS = 0x1
    FILE_SKIP_SET_EVENT_ON_HANDLE = 0x2


class IoControlCodes(enum.IntEnum):
    IOCTL_AFD_POLL = 0x00012024


################################################################
# Generic helpers
################################################################


def _handle(obj: int | CData) -> Handle:
    # For now, represent handles as either cffi HANDLEs or as ints.  If you
    # try to pass in a file descriptor instead, it's not going to work
    # out. (For that msvcrt.get_osfhandle does the trick, but I don't know if
    # we'll actually need that for anything...) For sockets this doesn't
    # matter, Python never allocates an fd. So let's wait until we actually
    # encounter the problem before worrying about it.
    if isinstance(obj, int):
        return Handle(ffi.cast("HANDLE", obj))
    return Handle(obj)


def handle_array(count: int) -> HandleArray:
    """Make an array of handles."""
    return HandleArray(ffi.new(f"HANDLE[{count}]"))


def raise_winerror(
    winerror: int | None = None,
    *,
    filename: str | None = None,
    filename2: str | None = None,
) -> NoReturn:
    # assert sys.platform == "win32"  # TODO: make this work in MyPy
    # ... in the meanwhile, ffi.getwinerror() is undefined on non-Windows, necessitating the type
    # ignores.

    if winerror is None:
        err = ffi.getwinerror()  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        winerror, msg = err
    else:
        err = ffi.getwinerror(winerror)  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        _, msg = err
    # https://docs.python.org/3/library/exceptions.html#OSError
    raise OSError(0, msg, filename, winerror, filename2)
