"""Path wrapping is quite complex, ensure all methods are understood as wrapped correctly."""

import io
import os
import pathlib
import sys
from typing import IO, Any, BinaryIO

import trio
from trio._file_io import AsyncIOWrapper
from typing_extensions import assert_type


def operator_checks(text: str, tpath: trio.Path, ppath: pathlib.Path) -> None:
    """Verify operators produce the right results."""
    assert_type(tpath / ppath, trio.Path)
    assert_type(tpath / tpath, trio.Path)
    assert_type(tpath / text, trio.Path)
    assert_type(text / tpath, trio.Path)

    assert_type(tpath > tpath, bool)
    assert_type(tpath >= tpath, bool)
    assert_type(tpath < tpath, bool)
    assert_type(tpath <= tpath, bool)

    assert_type(tpath > ppath, bool)
    assert_type(tpath >= ppath, bool)
    assert_type(tpath < ppath, bool)
    assert_type(tpath <= ppath, bool)

    assert_type(ppath > tpath, bool)
    assert_type(ppath >= tpath, bool)
    assert_type(ppath < tpath, bool)
    assert_type(ppath <= tpath, bool)


def sync_attrs(path: trio.Path) -> None:
    assert_type(path.parts, tuple[str, ...])
    assert_type(path.drive, str)
    assert_type(path.root, str)
    assert_type(path.anchor, str)
    assert_type(path.parents[3], trio.Path)
    assert_type(path.parent, trio.Path)
    assert_type(path.name, str)
    assert_type(path.suffix, str)
    assert_type(path.suffixes, list[str])
    assert_type(path.stem, str)
    assert_type(path.as_posix(), str)
    assert_type(path.as_uri(), str)
    assert_type(path.is_absolute(), bool)
    assert_type(path.is_relative_to(path), bool)
    assert_type(path.is_reserved(), bool)
    assert_type(path.joinpath(path, "folder"), trio.Path)
    assert_type(path.match("*.py"), bool)
    assert_type(path.relative_to("/usr"), trio.Path)
    if sys.version_info >= (3, 12):
        assert_type(path.relative_to("/", walk_up=True), trio.Path)
    assert_type(path.with_name("filename.txt"), trio.Path)
    assert_type(path.with_stem("readme"), trio.Path)
    assert_type(path.with_suffix(".log"), trio.Path)


async def async_attrs(path: trio.Path) -> None:
    assert_type(await trio.Path.cwd(), trio.Path)
    assert_type(await trio.Path.home(), trio.Path)
    assert_type(await path.stat(), os.stat_result)
    assert_type(await path.chmod(0o777), None)
    assert_type(await path.exists(), bool)
    assert_type(await path.expanduser(), trio.Path)
    for result in await path.glob("*.py"):
        assert_type(result, trio.Path)
    if sys.platform != "win32":
        assert_type(await path.group(), str)
    assert_type(await path.is_dir(), bool)
    assert_type(await path.is_file(), bool)
    if sys.version_info >= (3, 12):
        assert_type(await path.is_junction(), bool)
    if sys.platform != "win32":
        assert_type(await path.is_mount(), bool)
    assert_type(await path.is_symlink(), bool)
    assert_type(await path.is_socket(), bool)
    assert_type(await path.is_fifo(), bool)
    assert_type(await path.is_block_device(), bool)
    assert_type(await path.is_char_device(), bool)
    for child_iter in await path.iterdir():
        assert_type(child_iter, trio.Path)
    # TODO: Path.walk() in 3.12
    assert_type(await path.lchmod(0o111), None)
    assert_type(await path.lstat(), os.stat_result)
    assert_type(await path.mkdir(mode=0o777, parents=True, exist_ok=False), None)
    # Open done separately.
    if sys.platform != "win32":
        assert_type(await path.owner(), str)
    assert_type(await path.read_bytes(), bytes)
    assert_type(await path.read_text(encoding="utf16", errors="replace"), str)
    assert_type(await path.readlink(), trio.Path)
    assert_type(await path.rename("another"), trio.Path)
    assert_type(await path.replace(path), trio.Path)
    assert_type(await path.resolve(), trio.Path)
    for child_glob in await path.glob("*.py"):
        assert_type(child_glob, trio.Path)
    for child_rglob in await path.rglob("*.py"):
        assert_type(child_rglob, trio.Path)
    assert_type(await path.rmdir(), None)
    assert_type(await path.samefile("something_else"), bool)
    assert_type(await path.symlink_to("somewhere"), None)
    assert_type(await path.hardlink_to("elsewhere"), None)
    assert_type(await path.touch(), None)
    assert_type(await path.unlink(missing_ok=True), None)
    assert_type(await path.write_bytes(b"123"), int)
    assert_type(
        await path.write_text("hello", encoding="utf32le", errors="ignore"),
        int,
    )


async def open_results(path: trio.Path, some_int: int, some_str: str) -> None:
    # Check the overloads.
    assert_type(await path.open(), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("r"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("r+"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("w"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("rb", buffering=0), AsyncIOWrapper[io.FileIO])
    assert_type(await path.open("rb+"), AsyncIOWrapper[io.BufferedRandom])
    assert_type(await path.open("wb"), AsyncIOWrapper[io.BufferedWriter])
    assert_type(await path.open("rb"), AsyncIOWrapper[io.BufferedReader])
    assert_type(await path.open("rb", buffering=some_int), AsyncIOWrapper[BinaryIO])
    assert_type(await path.open(some_str), AsyncIOWrapper[IO[Any]])

    # Check they produce the right types.
    file_bin = await path.open("rb+")
    assert_type(await file_bin.read(), bytes)
    assert_type(await file_bin.write(b"test"), int)
    assert_type(await file_bin.seek(32), int)

    file_text = await path.open("r+t")
    assert_type(await file_text.read(), str)
    assert_type(await file_text.write("test"), int)
    # TODO: report mypy bug: equiv to https://github.com/microsoft/pyright/issues/6833
    assert_type(await file_text.readlines(), list[str])
