import importlib
import io
import os
import pathlib
import re
from typing import List, Tuple
from unittest import mock
from unittest.mock import sentinel

import pytest

import trio
from trio import _core, _file_io
from trio._file_io import _FILE_ASYNC_METHODS, _FILE_SYNC_ATTRS, AsyncIOWrapper


@pytest.fixture
def path(tmp_path: pathlib.Path) -> str:
    return os.fspath(tmp_path / "test")


@pytest.fixture
def wrapped() -> mock.Mock:
    return mock.Mock(spec_set=io.StringIO)


@pytest.fixture
def async_file(wrapped: mock.Mock) -> AsyncIOWrapper[mock.Mock]:
    return trio.wrap_file(wrapped)


def test_wrap_invalid() -> None:
    with pytest.raises(TypeError):
        trio.wrap_file("")


def test_wrap_non_iobase() -> None:
    class FakeFile:
        def close(self) -> None:  # pragma: no cover
            pass

        def write(self) -> None:  # pragma: no cover
            pass

    wrapped = FakeFile()
    assert not isinstance(wrapped, io.IOBase)

    async_file = trio.wrap_file(wrapped)
    assert isinstance(async_file, AsyncIOWrapper)

    del FakeFile.write

    with pytest.raises(TypeError):
        trio.wrap_file(FakeFile())


def test_wrapped_property(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    assert async_file.wrapped is wrapped


def test_dir_matches_wrapped(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    attrs = _FILE_SYNC_ATTRS.union(_FILE_ASYNC_METHODS)

    # all supported attrs in wrapped should be available in async_file
    assert all(attr in dir(async_file) for attr in attrs if attr in dir(wrapped))
    # all supported attrs not in wrapped should not be available in async_file
    assert not any(
        attr in dir(async_file) for attr in attrs if attr not in dir(wrapped)
    )


def test_unsupported_not_forwarded() -> None:
    class FakeFile(io.RawIOBase):
        def unsupported_attr(self) -> None:  # pragma: no cover
            pass

    async_file = trio.wrap_file(FakeFile())

    assert hasattr(async_file.wrapped, "unsupported_attr")

    with pytest.raises(AttributeError):
        # B018 "useless expression"
        async_file.unsupported_attr  # type: ignore[attr-defined] # noqa: B018


def test_type_stubs_match_lists() -> None:
    """Check the manual stubs match the list of wrapped methods."""
    # Fetch the module's source code.
    assert _file_io.__spec__ is not None
    loader = _file_io.__spec__.loader
    assert isinstance(loader, importlib.abc.SourceLoader)
    source = io.StringIO(loader.get_source("trio._file_io"))

    # Find the class, then find the TYPE_CHECKING block.
    for line in source:
        if "class AsyncIOWrapper" in line:
            break
    else:  # pragma: no cover - should always find this
        pytest.fail("No class definition line?")

    for line in source:
        if "if TYPE_CHECKING" in line:
            break
    else:  # pragma: no cover - should always find this
        pytest.fail("No TYPE CHECKING line?")

    # Now we should be at the type checking block.
    found: List[Tuple[str, str]] = []
    for line in source:  # pragma: no branch - expected to break early
        if line.strip() and not line.startswith(" " * 8):
            break  # Dedented out of the if TYPE_CHECKING block.
        match = re.match(r"\s*(async )?def ([a-zA-Z0-9_]+)\(", line)
        if match is not None:
            kind = "async" if match.group(1) is not None else "sync"
            found.append((match.group(2), kind))

    # Compare two lists so that we can easily see duplicates, and see what is different overall.
    expected = [(fname, "async") for fname in _FILE_ASYNC_METHODS]
    expected += [(fname, "sync") for fname in _FILE_SYNC_ATTRS]
    # Ignore order, error if duplicates are present.
    found.sort()
    expected.sort()
    assert found == expected


def test_sync_attrs_forwarded(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    for attr_name in _FILE_SYNC_ATTRS:
        if attr_name not in dir(async_file):
            continue

        assert getattr(async_file, attr_name) is getattr(wrapped, attr_name)


def test_sync_attrs_match_wrapper(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    for attr_name in _FILE_SYNC_ATTRS:
        if attr_name in dir(async_file):
            continue

        with pytest.raises(AttributeError):
            getattr(async_file, attr_name)

        with pytest.raises(AttributeError):
            getattr(wrapped, attr_name)


def test_async_methods_generated_once(async_file: AsyncIOWrapper[mock.Mock]) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name not in dir(async_file):
            continue

        assert getattr(async_file, meth_name) is getattr(async_file, meth_name)


# I gave up on typing this one
def test_async_methods_signature(async_file: AsyncIOWrapper[mock.Mock]) -> None:
    # use read as a representative of all async methods
    assert async_file.read.__name__ == "read"
    assert async_file.read.__qualname__ == "AsyncIOWrapper.read"

    assert async_file.read.__doc__ is not None
    assert "io.StringIO.read" in async_file.read.__doc__


async def test_async_methods_wrap(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name not in dir(async_file):
            continue

        meth = getattr(async_file, meth_name)
        wrapped_meth = getattr(wrapped, meth_name)

        value = await meth(sentinel.argument, keyword=sentinel.keyword)

        wrapped_meth.assert_called_once_with(
            sentinel.argument, keyword=sentinel.keyword
        )
        assert value == wrapped_meth()

        wrapped.reset_mock()


async def test_async_methods_match_wrapper(
    async_file: AsyncIOWrapper[mock.Mock], wrapped: mock.Mock
) -> None:
    for meth_name in _FILE_ASYNC_METHODS:
        if meth_name in dir(async_file):
            continue

        with pytest.raises(AttributeError):
            getattr(async_file, meth_name)

        with pytest.raises(AttributeError):
            getattr(wrapped, meth_name)


async def test_open(path: pathlib.Path) -> None:
    f = await trio.open_file(path, "w")

    assert isinstance(f, AsyncIOWrapper)

    await f.aclose()


async def test_open_context_manager(path: pathlib.Path) -> None:
    async with await trio.open_file(path, "w") as f:
        assert isinstance(f, AsyncIOWrapper)
        assert not f.closed

    assert f.closed


async def test_async_iter() -> None:
    async_file = trio.wrap_file(io.StringIO("test\nfoo\nbar"))
    expected = list(async_file.wrapped)
    result = []
    async_file.wrapped.seek(0)

    async for line in async_file:
        result.append(line)

    assert result == expected


async def test_aclose_cancelled(path: pathlib.Path) -> None:
    with _core.CancelScope() as cscope:
        f = await trio.open_file(path, "w")
        cscope.cancel()

        with pytest.raises(_core.Cancelled):
            await f.write("a")

        with pytest.raises(_core.Cancelled):
            await f.aclose()

    assert f.closed


async def test_detach_rewraps_asynciobase(tmp_path: pathlib.Path) -> None:
    tmp_file = tmp_path / "filename"
    tmp_file.touch()
    # flake8-async does not like opening files in async mode
    with open(tmp_file, mode="rb", buffering=0) as raw:  # noqa: ASYNC101
        buffered = io.BufferedReader(raw)

        async_file = trio.wrap_file(buffered)

        detached = await async_file.detach()

        assert isinstance(detached, AsyncIOWrapper)
        assert detached.wrapped is raw
