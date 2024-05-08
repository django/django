from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING, Type, Union

import pytest

import trio
from trio._file_io import AsyncIOWrapper

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@pytest.fixture
def path(tmp_path: pathlib.Path) -> trio.Path:
    return trio.Path(tmp_path / "test")


def method_pair(
    path: str,
    method_name: str,
) -> tuple[Callable[[], object], Callable[[], Awaitable[object]]]:
    sync_path = pathlib.Path(path)
    async_path = trio.Path(path)
    return getattr(sync_path, method_name), getattr(async_path, method_name)


@pytest.mark.skipif(os.name == "nt", reason="OS is not posix")
async def test_instantiate_posix() -> None:
    assert isinstance(trio.Path(), trio.PosixPath)


@pytest.mark.skipif(os.name != "nt", reason="OS is not Windows")
async def test_instantiate_windows() -> None:
    assert isinstance(trio.Path(), trio.WindowsPath)


async def test_open_is_async_context_manager(path: trio.Path) -> None:
    async with await path.open("w") as f:
        assert isinstance(f, AsyncIOWrapper)

    assert f.closed


async def test_magic() -> None:
    path = trio.Path("test")

    assert str(path) == "test"
    assert bytes(path) == b"test"


EitherPathType = Union[Type[trio.Path], Type[pathlib.Path]]
PathOrStrType = Union[EitherPathType, Type[str]]
cls_pairs: list[tuple[EitherPathType, EitherPathType]] = [
    (trio.Path, pathlib.Path),
    (pathlib.Path, trio.Path),
    (trio.Path, trio.Path),
]


@pytest.mark.parametrize(("cls_a", "cls_b"), cls_pairs)
async def test_cmp_magic(cls_a: EitherPathType, cls_b: EitherPathType) -> None:
    a, b = cls_a(""), cls_b("")
    assert a == b
    assert not a != b  # noqa: SIM202  # negate-not-equal-op

    a, b = cls_a("a"), cls_b("b")
    assert a < b
    assert b > a

    # this is intentionally testing equivalence with none, due to the
    # other=sentinel logic in _forward_magic
    assert not a == None  # noqa
    assert not b == None  # noqa


# upstream python3.8 bug: we should also test (pathlib.Path, trio.Path), but
# __*div__ does not properly raise NotImplementedError like the other comparison
# magic, so trio.Path's implementation does not get dispatched
cls_pairs_str: list[tuple[PathOrStrType, PathOrStrType]] = [
    (trio.Path, pathlib.Path),
    (trio.Path, trio.Path),
    (trio.Path, str),
    (str, trio.Path),
]


@pytest.mark.parametrize(("cls_a", "cls_b"), cls_pairs_str)
async def test_div_magic(cls_a: PathOrStrType, cls_b: PathOrStrType) -> None:
    a, b = cls_a("a"), cls_b("b")

    result = a / b  # type: ignore[operator]
    # Type checkers think str / str could happen. Check each combo manually in type_tests/.
    assert isinstance(result, trio.Path)
    assert str(result) == os.path.join("a", "b")


@pytest.mark.parametrize(
    ("cls_a", "cls_b"), [(trio.Path, pathlib.Path), (trio.Path, trio.Path)]
)
@pytest.mark.parametrize("path", ["foo", "foo/bar/baz", "./foo"])
async def test_hash_magic(
    cls_a: EitherPathType, cls_b: EitherPathType, path: str
) -> None:
    a, b = cls_a(path), cls_b(path)
    assert hash(a) == hash(b)


async def test_forwarded_properties(path: trio.Path) -> None:
    # use `name` as a representative of forwarded properties

    assert "name" in dir(path)
    assert path.name == "test"


async def test_async_method_signature(path: trio.Path) -> None:
    # use `resolve` as a representative of wrapped methods

    assert path.resolve.__name__ == "resolve"
    assert path.resolve.__qualname__ == "Path.resolve"

    assert path.resolve.__doc__ is not None
    assert "pathlib.Path.resolve" in path.resolve.__doc__


@pytest.mark.parametrize("method_name", ["is_dir", "is_file"])
async def test_compare_async_stat_methods(method_name: str) -> None:
    method, async_method = method_pair(".", method_name)

    result = method()
    async_result = await async_method()

    assert result == async_result


async def test_invalid_name_not_wrapped(path: trio.Path) -> None:
    with pytest.raises(AttributeError):
        getattr(path, "invalid_fake_attr")  # noqa: B009  # "get-attr-with-constant"


@pytest.mark.parametrize("method_name", ["absolute", "resolve"])
async def test_async_methods_rewrap(method_name: str) -> None:
    method, async_method = method_pair(".", method_name)

    result = method()
    async_result = await async_method()

    assert isinstance(async_result, trio.Path)
    assert str(result) == str(async_result)


async def test_forward_methods_rewrap(path: trio.Path, tmp_path: pathlib.Path) -> None:
    with_name = path.with_name("foo")
    with_suffix = path.with_suffix(".py")

    assert isinstance(with_name, trio.Path)
    assert with_name == tmp_path / "foo"
    assert isinstance(with_suffix, trio.Path)
    assert with_suffix == tmp_path / "test.py"


async def test_forward_properties_rewrap(path: trio.Path) -> None:
    assert isinstance(path.parent, trio.Path)


async def test_forward_methods_without_rewrap(path: trio.Path) -> None:
    path = await path.parent.resolve()

    assert path.as_uri().startswith("file:///")


async def test_repr() -> None:
    path = trio.Path(".")

    assert repr(path) == "trio.Path('.')"


@pytest.mark.parametrize("meth", [trio.Path.__init__, trio.Path.joinpath])
async def test_path_wraps_path(
    path: trio.Path,
    meth: Callable[[trio.Path, trio.Path], object],
) -> None:
    wrapped = await path.absolute()
    result = meth(path, wrapped)
    if result is None:
        result = path

    assert wrapped == result


async def test_path_nonpath() -> None:
    with pytest.raises(TypeError):
        trio.Path(1)  # type: ignore


async def test_open_file_can_open_path(path: trio.Path) -> None:
    async with await trio.open_file(path, "w") as f:
        assert f.name == os.fspath(path)


async def test_globmethods(path: trio.Path) -> None:
    # Populate a directory tree
    await path.mkdir()
    await (path / "foo").mkdir()
    await (path / "foo" / "_bar.txt").write_bytes(b"")
    await (path / "bar.txt").write_bytes(b"")
    await (path / "bar.dat").write_bytes(b"")

    # Path.glob
    for _pattern, _results in {
        "*.txt": {"bar.txt"},
        "**/*.txt": {"_bar.txt", "bar.txt"},
    }.items():
        entries = set()
        for entry in await path.glob(_pattern):
            assert isinstance(entry, trio.Path)
            entries.add(entry.name)

        assert entries == _results

    # Path.rglob
    entries = set()
    for entry in await path.rglob("*.txt"):
        assert isinstance(entry, trio.Path)
        entries.add(entry.name)

    assert entries == {"_bar.txt", "bar.txt"}


async def test_iterdir(path: trio.Path) -> None:
    # Populate a directory
    await path.mkdir()
    await (path / "foo").mkdir()
    await (path / "bar.txt").write_bytes(b"")

    entries = set()
    for entry in await path.iterdir():
        assert isinstance(entry, trio.Path)
        entries.add(entry.name)

    assert entries == {"bar.txt", "foo"}


async def test_classmethods() -> None:
    assert isinstance(await trio.Path.home(), trio.Path)

    # pathlib.Path has only two classmethods
    assert str(await trio.Path.home()) == os.path.expanduser("~")
    assert str(await trio.Path.cwd()) == os.getcwd()

    # Wrapped method has docstring
    assert trio.Path.home.__doc__
