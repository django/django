from __future__ import annotations

import inspect
import os
import pathlib
import sys
import types
from functools import partial
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    ClassVar,
    TypeVar,
    Union,
    cast,
    overload,
)

import trio
from trio._util import async_wraps, final, wraps

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Sequence
    from io import BufferedRandom, BufferedReader, BufferedWriter, FileIO, TextIOWrapper

    from _typeshed import (
        OpenBinaryMode,
        OpenBinaryModeReading,
        OpenBinaryModeUpdating,
        OpenBinaryModeWriting,
        OpenTextMode,
    )
    from typing_extensions import Concatenate, Literal, ParamSpec, TypeAlias

    from trio._file_io import AsyncIOWrapper as _AsyncIOWrapper

    P = ParamSpec("P")

T = TypeVar("T")
StrPath: TypeAlias = Union[str, "os.PathLike[str]"]  # Only subscriptable in 3.9+


# re-wrap return value from methods that return new instances of pathlib.Path
def rewrap_path(value: T) -> T | Path:
    if isinstance(value, pathlib.Path):
        return Path(value)
    else:
        return value


def _forward_factory(
    cls: AsyncAutoWrapperType,
    attr_name: str,
    attr: Callable[Concatenate[pathlib.Path, P], T],
) -> Callable[Concatenate[Path, P], T | Path]:
    @wraps(attr)
    def wrapper(self: Path, *args: P.args, **kwargs: P.kwargs) -> T | Path:
        attr = getattr(self._wrapped, attr_name)
        value = attr(*args, **kwargs)
        return rewrap_path(value)

    # Assigning this makes inspect and therefore Sphinx show the original parameters.
    # It's not defined on functions normally though, this is a custom attribute.
    assert isinstance(wrapper, types.FunctionType)
    wrapper.__signature__ = inspect.signature(attr)

    return wrapper


def _forward_magic(
    cls: AsyncAutoWrapperType, attr: Callable[..., T]
) -> Callable[..., Path | T]:
    sentinel = object()

    @wraps(attr)
    def wrapper(self: Path, other: object = sentinel) -> Path | T:
        if other is sentinel:
            return attr(self._wrapped)
        if isinstance(other, cls):
            other = cast(Path, other)._wrapped
        value = attr(self._wrapped, other)
        return rewrap_path(value)

    assert isinstance(wrapper, types.FunctionType)
    wrapper.__signature__ = inspect.signature(attr)
    return wrapper


def iter_wrapper_factory(
    cls: AsyncAutoWrapperType, meth_name: str
) -> Callable[Concatenate[Path, P], Awaitable[Iterable[Path]]]:
    @async_wraps(cls, cls._wraps, meth_name)
    async def wrapper(self: Path, *args: P.args, **kwargs: P.kwargs) -> Iterable[Path]:
        meth = getattr(self._wrapped, meth_name)
        func = partial(meth, *args, **kwargs)
        # Make sure that the full iteration is performed in the thread
        # by converting the generator produced by pathlib into a list
        items = await trio.to_thread.run_sync(lambda: list(func()))
        return (rewrap_path(item) for item in items)

    return wrapper


def thread_wrapper_factory(
    cls: AsyncAutoWrapperType, meth_name: str
) -> Callable[Concatenate[Path, P], Awaitable[Path]]:
    @async_wraps(cls, cls._wraps, meth_name)
    async def wrapper(self: Path, *args: P.args, **kwargs: P.kwargs) -> Path:
        meth = getattr(self._wrapped, meth_name)
        func = partial(meth, *args, **kwargs)
        value = await trio.to_thread.run_sync(func)
        return rewrap_path(value)

    return wrapper


def classmethod_wrapper_factory(
    cls: AsyncAutoWrapperType, meth_name: str
) -> classmethod:  # type: ignore[type-arg]
    @async_wraps(cls, cls._wraps, meth_name)
    async def wrapper(cls: type[Path], *args: Any, **kwargs: Any) -> Path:  # type: ignore[misc] # contains Any
        meth = getattr(cls._wraps, meth_name)
        func = partial(meth, *args, **kwargs)
        value = await trio.to_thread.run_sync(func)
        return rewrap_path(value)

    assert isinstance(wrapper, types.FunctionType)
    wrapper.__signature__ = inspect.signature(getattr(cls._wraps, meth_name))
    return classmethod(wrapper)


class AsyncAutoWrapperType(type):
    _forwards: type
    _wraps: type
    _forward_magic: list[str]
    _wrap_iter: list[str]
    _forward: list[str]

    def __init__(
        cls, name: str, bases: tuple[type, ...], attrs: dict[str, object]
    ) -> None:
        super().__init__(name, bases, attrs)

        cls._forward = []
        type(cls).generate_forwards(cls, attrs)
        type(cls).generate_wraps(cls, attrs)
        type(cls).generate_magic(cls, attrs)
        type(cls).generate_iter(cls, attrs)

    def generate_forwards(cls, attrs: dict[str, object]) -> None:
        # forward functions of _forwards
        for attr_name, attr in cls._forwards.__dict__.items():
            if attr_name.startswith("_") or attr_name in attrs:
                continue

            if isinstance(attr, property):
                cls._forward.append(attr_name)
            elif isinstance(attr, types.FunctionType):
                wrapper = _forward_factory(cls, attr_name, attr)
                setattr(cls, attr_name, wrapper)
            else:
                raise TypeError(attr_name, type(attr))

    def generate_wraps(cls, attrs: dict[str, object]) -> None:
        # generate wrappers for functions of _wraps
        wrapper: classmethod | Callable[..., object]  # type: ignore[type-arg]
        for attr_name, attr in cls._wraps.__dict__.items():
            # .z. exclude cls._wrap_iter
            if attr_name.startswith("_") or attr_name in attrs:
                continue
            if isinstance(attr, classmethod):
                wrapper = classmethod_wrapper_factory(cls, attr_name)
                setattr(cls, attr_name, wrapper)
            elif isinstance(attr, types.FunctionType):
                wrapper = thread_wrapper_factory(cls, attr_name)
                assert isinstance(wrapper, types.FunctionType)
                wrapper.__signature__ = inspect.signature(attr)
                setattr(cls, attr_name, wrapper)
            else:
                raise TypeError(attr_name, type(attr))

    def generate_magic(cls, attrs: dict[str, object]) -> None:
        # generate wrappers for magic
        for attr_name in cls._forward_magic:
            attr = getattr(cls._forwards, attr_name)
            wrapper = _forward_magic(cls, attr)
            setattr(cls, attr_name, wrapper)

    def generate_iter(cls, attrs: dict[str, object]) -> None:
        # generate wrappers for methods that return iterators
        wrapper: Callable[..., object]
        for attr_name, attr in cls._wraps.__dict__.items():
            if attr_name in cls._wrap_iter:
                wrapper = iter_wrapper_factory(cls, attr_name)
                assert isinstance(wrapper, types.FunctionType)
                wrapper.__signature__ = inspect.signature(attr)
                setattr(cls, attr_name, wrapper)


@final
class Path(metaclass=AsyncAutoWrapperType):
    """A :class:`pathlib.Path` wrapper that executes blocking methods in
    :meth:`trio.to_thread.run_sync`.

    """

    _forward: ClassVar[list[str]]
    _wraps: ClassVar[type] = pathlib.Path
    _forwards: ClassVar[type] = pathlib.PurePath
    _forward_magic: ClassVar[list[str]] = [
        "__str__",
        "__bytes__",
        "__truediv__",
        "__rtruediv__",
        "__eq__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__hash__",
    ]
    _wrap_iter: ClassVar[list[str]] = ["glob", "rglob", "iterdir"]

    def __init__(self, *args: StrPath) -> None:
        self._wrapped = pathlib.Path(*args)

    # type checkers allow accessing any attributes on class instances with `__getattr__`
    # so we hide it behind a type guard forcing it to rely on the hardcoded attribute
    # list below.
    if not TYPE_CHECKING:

        def __getattr__(self, name):
            if name in self._forward:
                value = getattr(self._wrapped, name)
                return rewrap_path(value)
            raise AttributeError(name)

    def __dir__(self) -> list[str]:
        return [*super().__dir__(), *self._forward]

    def __repr__(self) -> str:
        return f"trio.Path({str(self)!r})"

    def __fspath__(self) -> str:
        return os.fspath(self._wrapped)

    @overload
    async def open(
        self,
        mode: OpenTextMode = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> _AsyncIOWrapper[TextIOWrapper]:
        ...

    @overload
    async def open(
        self,
        mode: OpenBinaryMode,
        buffering: Literal[0],
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> _AsyncIOWrapper[FileIO]:
        ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeUpdating,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> _AsyncIOWrapper[BufferedRandom]:
        ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeWriting,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> _AsyncIOWrapper[BufferedWriter]:
        ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeReading,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> _AsyncIOWrapper[BufferedReader]:
        ...

    @overload
    async def open(
        self,
        mode: OpenBinaryMode,
        buffering: int = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> _AsyncIOWrapper[BinaryIO]:
        ...

    @overload
    async def open(  # type: ignore[misc]  # Any usage matches builtins.open().
        self,
        mode: str,
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> _AsyncIOWrapper[IO[Any]]:
        ...

    @wraps(pathlib.Path.open)  # type: ignore[misc]  # Overload return mismatch.
    async def open(self, *args: Any, **kwargs: Any) -> _AsyncIOWrapper[IO[Any]]:
        """Open the file pointed to by the path, like the :func:`trio.open_file`
        function does.

        """

        func = partial(self._wrapped.open, *args, **kwargs)
        value = await trio.to_thread.run_sync(func)
        return trio.wrap_file(value)

    if TYPE_CHECKING:
        # the dunders listed in _forward_magic that aren't seen otherwise
        # fmt: off
        def __bytes__(self) -> bytes: ...
        def __truediv__(self, other: StrPath) -> Path: ...
        def __rtruediv__(self, other: StrPath) -> Path: ...
        def __lt__(self, other: Path | pathlib.PurePath) -> bool: ...
        def __le__(self, other: Path | pathlib.PurePath) -> bool: ...
        def __gt__(self, other: Path | pathlib.PurePath) -> bool: ...
        def __ge__(self, other: Path | pathlib.PurePath) -> bool: ...

        # The following are ordered the same as in typeshed.

        # Properties produced by __getattr__() - all synchronous.
        @property
        def parts(self) -> tuple[str, ...]: ...
        @property
        def drive(self) -> str: ...
        @property
        def root(self) -> str: ...
        @property
        def anchor(self) -> str: ...
        @property
        def name(self) -> str: ...
        @property
        def suffix(self) -> str: ...
        @property
        def suffixes(self) -> list[str]: ...
        @property
        def stem(self) -> str: ...
        @property
        def parents(self) -> Sequence[pathlib.Path]: ...   # TODO: Convert these to trio Paths?
        @property
        def parent(self) -> Path: ...

        # PurePath methods - synchronous.
        def as_posix(self) -> str: ...
        def as_uri(self) -> str: ...
        def is_absolute(self) -> bool: ...
        def is_reserved(self) -> bool: ...
        def match(self, path_pattern: str) -> bool: ...
        def relative_to(self, *other: StrPath) -> Path: ...
        def with_name(self, name: str) -> Path: ...
        def with_suffix(self, suffix: str) -> Path: ...
        def joinpath(self, *other: StrPath) -> Path: ...

        if sys.version_info >= (3, 9):
            def is_relative_to(self, *other: StrPath) -> bool: ...
            def with_stem(self, stem: str) -> Path: ...

        # pathlib.Path methods and properties - async.
        @classmethod
        async def cwd(self) -> Path: ...

        if sys.version_info >= (3, 10):
            async def stat(self, *, follow_symlinks: bool = True) -> os.stat_result: ...
            async def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None: ...
        else:
            async def stat(self) -> os.stat_result: ...
            async def chmod(self, mode: int) -> None: ...

        async def exists(self) -> bool: ...
        async def glob(self, pattern: str) -> Iterable[Path]: ...
        async def is_dir(self) -> bool: ...
        async def is_file(self) -> bool: ...
        async def is_symlink(self) -> bool: ...
        async def is_socket(self) -> bool: ...
        async def is_fifo(self) -> bool: ...
        async def is_block_device(self) -> bool: ...
        async def is_char_device(self) -> bool: ...
        async def iterdir(self) -> Iterable[Path]: ...
        async def lchmod(self, mode: int) -> None: ...
        async def lstat(self) -> os.stat_result: ...
        async def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None: ...

        if sys.platform != "win32":
            async def owner(self) -> str: ...
            async def group(self) -> str: ...
            async def is_mount(self) -> bool: ...
        if sys.version_info >= (3, 9):
            async def readlink(self) -> Path: ...
        async def rename(self, target: StrPath) -> Path: ...
        async def replace(self, target: StrPath) -> Path: ...
        async def resolve(self, strict: bool = False) -> Path: ...
        async def rglob(self, pattern: str) -> Iterable[Path]: ...
        async def rmdir(self) -> None: ...
        async def symlink_to(self, target: StrPath, target_is_directory: bool = False) -> None: ...
        if sys.version_info >= (3, 10):
            async def hardlink_to(self, target: str | pathlib.Path) -> None: ...
        async def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None: ...
        async def unlink(self, missing_ok: bool = False) -> None: ...
        @classmethod
        async def home(self) -> Path: ...
        async def absolute(self) -> Path: ...
        async def expanduser(self) -> Path: ...
        async def read_bytes(self) -> bytes: ...
        async def read_text(self, encoding: str | None = None, errors: str | None = None) -> str: ...
        async def samefile(self, other_path: bytes | int | StrPath) -> bool: ...
        async def write_bytes(self, data: bytes) -> int: ...

        if sys.version_info >= (3, 10):
            async def write_text(
                self, data: str,
                encoding: str | None = None,
                errors: str | None = None,
                newline: str | None = None,
            ) -> int: ...
        else:
            async def write_text(
                self, data: str,
                encoding: str | None = None,
                errors: str | None = None,
            ) -> int: ...

        if sys.version_info < (3, 12):
            async def link_to(self, target: StrPath | bytes) -> None: ...
        if sys.version_info >= (3, 12):
            async def is_junction(self) -> bool: ...
            walk: Any  # TODO
            async def with_segments(self, *pathsegments: StrPath) -> Path: ...


Path.iterdir.__doc__ = """
    Like :meth:`~pathlib.Path.iterdir`, but async.

    This is an async method that returns a synchronous iterator, so you
    use it like::

       for subpath in await mypath.iterdir():
           ...

    Note that it actually loads the whole directory list into memory
    immediately, during the initial call. (See `issue #501
    <https://github.com/python-trio/trio/issues/501>`__ for discussion.)

"""

if sys.version_info < (3, 12):
    # Since we synthesise methods from the stdlib, this automatically will
    # have deprecation warnings, and disappear entirely in 3.12+.
    Path.link_to.__doc__ = """
    Like Python 3.8-3.11's :meth:`~pathlib.Path.link_to`, but async.

    :deprecated: This method was deprecated in Python 3.10 and entirely \
    removed in 3.12. Use :meth:`hardlink_to` instead which has \
    a more meaningful parameter order.
"""

# The value of Path.absolute.__doc__ makes a reference to
# :meth:~pathlib.Path.absolute, which does not exist. Removing this makes more
# sense than inventing our own special docstring for this.
del Path.absolute.__doc__

# TODO: This is likely not supported by all the static tools out there, see discussion in
# https://github.com/python-trio/trio/pull/2631#discussion_r1185612528
os.PathLike.register(Path)
