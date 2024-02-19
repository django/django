from __future__ import annotations  # isort: split

import __future__  # Regular import, not special!

import enum
import functools
import importlib
import inspect
import json
import socket as stdlib_socket
import sys
import types
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Protocol

import attrs
import pytest

import trio
import trio.testing
from trio._tests.pytest_plugin import skip_if_optional_else_raise

from .. import _core, _util
from .._core._tests.tutil import slow
from .pytest_plugin import RUN_SLOW

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

mypy_cache_updated = False


try:  # If installed, check both versions of this class.
    from typing_extensions import Protocol as Protocol_ext
except ImportError:  # pragma: no cover
    Protocol_ext = Protocol  # type: ignore[assignment]


def _ensure_mypy_cache_updated() -> None:
    # This pollutes the `empty` dir. Should this be changed?
    try:
        from mypy.api import run
    except ImportError as error:
        skip_if_optional_else_raise(error)

    global mypy_cache_updated
    if not mypy_cache_updated:
        # mypy cache was *probably* already updated by the other tests,
        # but `pytest -k ...` might run just this test on its own
        result = run(
            [
                "--config-file=",
                "--cache-dir=./.mypy_cache",
                "--no-error-summary",
                "-c",
                "import trio",
            ]
        )
        assert not result[1]  # stderr
        assert not result[0]  # stdout
        mypy_cache_updated = True


def test_core_is_properly_reexported() -> None:
    # Each export from _core should be re-exported by exactly one of these
    # three modules:
    sources = [trio, trio.lowlevel, trio.testing]
    for symbol in dir(_core):
        if symbol.startswith("_"):
            continue
        found = 0
        for source in sources:
            if symbol in dir(source) and getattr(source, symbol) is getattr(
                _core, symbol
            ):
                found += 1
        print(symbol, found)
        assert found == 1


def class_is_final(cls: type) -> bool:
    """Check if a class cannot be subclassed."""
    try:
        # new_class() handles metaclasses properly, type(...) does not.
        types.new_class("SubclassTester", (cls,))
    except TypeError:
        return True
    else:
        return False


def iter_modules(
    module: types.ModuleType,
    only_public: bool,
) -> Iterator[types.ModuleType]:
    yield module
    for name, class_ in module.__dict__.items():
        if name.startswith("_") and only_public:
            continue
        if not isinstance(class_, ModuleType):
            continue
        if not class_.__name__.startswith(module.__name__):  # pragma: no cover
            continue
        if class_ is module:  # pragma: no cover
            continue
        yield from iter_modules(class_, only_public)


PUBLIC_MODULES = list(iter_modules(trio, only_public=True))
ALL_MODULES = list(iter_modules(trio, only_public=False))
PUBLIC_MODULE_NAMES = [m.__name__ for m in PUBLIC_MODULES]


# It doesn't make sense for downstream redistributors to run this test, since
# they might be using a newer version of Python with additional symbols which
# won't be reflected in trio.socket, and this shouldn't cause downstream test
# runs to start failing.
@pytest.mark.redistributors_should_skip()
# Static analysis tools often have trouble with alpha releases, where Python's
# internals are in flux, grammar may not have settled down, etc.
@pytest.mark.skipif(
    sys.version_info.releaselevel == "alpha",
    reason="skip static introspection tools on Python dev/alpha releases",
)
@pytest.mark.parametrize("modname", PUBLIC_MODULE_NAMES)
@pytest.mark.parametrize("tool", ["pylint", "jedi", "mypy", "pyright_verifytypes"])
@pytest.mark.filterwarnings(
    # https://github.com/pypa/setuptools/issues/3274
    "ignore:module 'sre_constants' is deprecated:DeprecationWarning",
)
def test_static_tool_sees_all_symbols(tool: str, modname: str, tmp_path: Path) -> None:
    module = importlib.import_module(modname)

    def no_underscores(symbols: Iterable[str]) -> set[str]:
        return {symbol for symbol in symbols if not symbol.startswith("_")}

    runtime_names = no_underscores(dir(module))

    # ignore deprecated module `tests` being invisible
    if modname == "trio":
        runtime_names.discard("tests")

    # Ignore any __future__ feature objects, if imported under that name.
    for name in __future__.all_feature_names:
        if getattr(module, name, None) is getattr(__future__, name):
            runtime_names.remove(name)

    if tool == "pylint":
        try:
            from pylint.lint import PyLinter
        except ImportError as error:
            skip_if_optional_else_raise(error)

        linter = PyLinter()
        assert module.__file__ is not None
        ast = linter.get_ast(module.__file__, modname)
        static_names = no_underscores(ast)  # type: ignore[arg-type]
    elif tool == "jedi":
        if sys.implementation.name != "cpython":
            pytest.skip("jedi does not support pypy")

        try:
            import jedi
        except ImportError as error:
            skip_if_optional_else_raise(error)

        # Simulate typing "import trio; trio.<TAB>"
        script = jedi.Script(f"import {modname}; {modname}.")
        completions = script.complete()
        static_names = no_underscores(c.name for c in completions)
    elif tool == "mypy":
        if not RUN_SLOW:  # pragma: no cover
            pytest.skip("use --run-slow to check against mypy")
        if sys.implementation.name != "cpython":
            pytest.skip("mypy not installed in tests on pypy")

        cache = Path.cwd() / ".mypy_cache"

        _ensure_mypy_cache_updated()

        trio_cache = next(cache.glob("*/trio"))
        _, modname = (modname + ".").split(".", 1)
        modname = modname[:-1]
        mod_cache = trio_cache / modname if modname else trio_cache
        if mod_cache.is_dir():  # pragma: no coverage
            mod_cache = mod_cache / "__init__.data.json"
        else:
            mod_cache = trio_cache / (modname + ".data.json")

        assert mod_cache.exists()
        assert mod_cache.is_file()
        with mod_cache.open() as cache_file:
            cache_json = json.loads(cache_file.read())
            static_names = no_underscores(
                key
                for key, value in cache_json["names"].items()
                if not key.startswith(".") and value["kind"] == "Gdef"
            )
    elif tool == "pyright_verifytypes":
        if not RUN_SLOW:  # pragma: no cover
            pytest.skip("use --run-slow to check against pyright")

        try:
            import pyright  # noqa: F401
        except ImportError as error:
            skip_if_optional_else_raise(error)
        import subprocess

        res = subprocess.run(
            ["pyright", f"--verifytypes={modname}", "--outputjson"],
            capture_output=True,
        )
        current_result = json.loads(res.stdout)

        static_names = {
            x["name"][len(modname) + 1 :]
            for x in current_result["typeCompleteness"]["symbols"]
            if x["name"].startswith(modname)
        }
    else:  # pragma: no cover
        raise AssertionError()

    # It's expected that the static set will contain more names than the
    # runtime set:
    # - static tools are sometimes sloppy and include deleted names
    # - some symbols are platform-specific at runtime, but always show up in
    #   static analysis (e.g. in trio.socket or trio.lowlevel)
    # So we check that the runtime names are a subset of the static names.
    missing_names = runtime_names - static_names

    # ignore warnings about deprecated module tests
    missing_names -= {"tests"}

    if missing_names:  # pragma: no cover
        print(f"{tool} can't see the following names in {modname}:")
        print()
        for name in sorted(missing_names):
            print(f"    {name}")
        raise AssertionError()


# this could be sped up by only invoking mypy once per module, or even once for all
# modules, instead of once per class.
@slow
# see comment on test_static_tool_sees_all_symbols
@pytest.mark.redistributors_should_skip()
# Static analysis tools often have trouble with alpha releases, where Python's
# internals are in flux, grammar may not have settled down, etc.
@pytest.mark.skipif(
    sys.version_info.releaselevel == "alpha",
    reason="skip static introspection tools on Python dev/alpha releases",
)
@pytest.mark.parametrize("module_name", PUBLIC_MODULE_NAMES)
@pytest.mark.parametrize("tool", ["jedi", "mypy"])
def test_static_tool_sees_class_members(
    tool: str, module_name: str, tmp_path: Path
) -> None:
    module = PUBLIC_MODULES[PUBLIC_MODULE_NAMES.index(module_name)]

    # ignore hidden, but not dunder, symbols
    def no_hidden(symbols: Iterable[str]) -> set[str]:
        return {
            symbol
            for symbol in symbols
            if (not symbol.startswith("_")) or symbol.startswith("__")
        }

    if tool == "mypy":
        if sys.implementation.name != "cpython":
            pytest.skip("mypy not installed in tests on pypy")

        cache = Path.cwd() / ".mypy_cache"

        _ensure_mypy_cache_updated()

        trio_cache = next(cache.glob("*/trio"))
        modname = module_name
        _, modname = (modname + ".").split(".", 1)
        modname = modname[:-1]
        mod_cache = trio_cache / modname if modname else trio_cache
        if mod_cache.is_dir():
            mod_cache = mod_cache / "__init__.data.json"
        else:
            mod_cache = trio_cache / (modname + ".data.json")

        assert mod_cache.exists()
        assert mod_cache.is_file()
        with mod_cache.open() as cache_file:
            cache_json = json.loads(cache_file.read())

        # skip a bunch of file-system activity (probably can un-memoize?)
        @functools.lru_cache
        def lookup_symbol(symbol: str) -> dict[str, str]:
            topname, *modname, name = symbol.split(".")
            version = next(cache.glob("3.*/"))
            mod_cache = version / topname
            if not mod_cache.is_dir():
                mod_cache = version / (topname + ".data.json")

            if modname:
                for piece in modname[:-1]:
                    mod_cache /= piece
                next_cache = mod_cache / modname[-1]
                if next_cache.is_dir():  # pragma: no coverage
                    mod_cache = next_cache / "__init__.data.json"
                else:
                    mod_cache = mod_cache / (modname[-1] + ".data.json")

            with mod_cache.open() as f:
                return json.loads(f.read())["names"][name]  # type: ignore[no-any-return]

    errors: dict[str, object] = {}
    for class_name, class_ in module.__dict__.items():
        if not isinstance(class_, type):
            continue
        if module_name == "trio.socket" and class_name in dir(stdlib_socket):
            continue

        # ignore class that does dirty tricks
        if class_ is trio.testing.RaisesGroup:
            continue

        # dir() and inspect.getmembers doesn't display properties from the metaclass
        # also ignore some dunder methods that tend to differ but are of no consequence
        ignore_names = set(dir(type(class_))) | {
            "__annotations__",
            "__attrs_attrs__",
            "__attrs_own_setattr__",
            "__callable_proto_members_only__",
            "__class_getitem__",
            "__final__",
            "__getstate__",
            "__match_args__",
            "__order__",
            "__orig_bases__",
            "__parameters__",
            "__protocol_attrs__",
            "__setstate__",
            "__slots__",
            "__weakref__",
            # ignore errors about dunders inherited from stdlib that tools might
            # not see
            "__copy__",
            "__deepcopy__",
        }

        # pypy seems to have some additional dunders that differ
        if sys.implementation.name == "pypy":
            ignore_names |= {
                "__basicsize__",
                "__dictoffset__",
                "__itemsize__",
                "__sizeof__",
                "__weakrefoffset__",
                "__unicode__",
            }

        # inspect.getmembers sees `name` and `value` in Enums, otherwise
        # it behaves the same way as `dir`
        # runtime_names = no_underscores(dir(class_))
        runtime_names = (
            no_hidden(x[0] for x in inspect.getmembers(class_)) - ignore_names
        )

        if tool == "jedi":
            try:
                import jedi
            except ImportError as error:
                skip_if_optional_else_raise(error)

            script = jedi.Script(
                f"from {module_name} import {class_name}; {class_name}."
            )
            completions = script.complete()
            static_names = no_hidden(c.name for c in completions) - ignore_names

        elif tool == "mypy":
            # load the cached type information
            cached_type_info = cache_json["names"][class_name]
            if "node" not in cached_type_info:
                cached_type_info = lookup_symbol(cached_type_info["cross_ref"])

            assert "node" in cached_type_info
            node = cached_type_info["node"]
            static_names = no_hidden(k for k in node["names"] if not k.startswith("."))
            for symbol in node["mro"][1:]:
                node = lookup_symbol(symbol)["node"]
                static_names |= no_hidden(
                    k for k in node["names"] if not k.startswith(".")
                )
            static_names -= ignore_names

        else:  # pragma: no cover
            raise AssertionError("unknown tool")

        missing = runtime_names - static_names
        extra = static_names - runtime_names

        # using .remove() instead of .delete() to get an error in case they start not
        # being missing

        if (
            tool == "jedi"
            and BaseException in class_.__mro__
            and sys.version_info >= (3, 11)
        ):
            missing.remove("add_note")

        if (
            tool == "mypy"
            and BaseException in class_.__mro__
            and sys.version_info >= (3, 11)
        ):
            extra.remove("__notes__")

        if tool == "mypy" and attrs.has(class_):
            # e.g. __trio__core__run_CancelScope_AttrsAttributes__
            before = len(extra)
            extra = {e for e in extra if not e.endswith("AttrsAttributes__")}
            assert len(extra) == before - 1

        # mypy does not see these attributes in Enum subclasses
        if (
            tool == "mypy"
            and enum.Enum in class_.__mro__
            and sys.version_info >= (3, 12)
        ):
            # Another attribute, in 3.12+ only.
            extra.remove("__signature__")

        # TODO: this *should* be visible via `dir`!!
        if tool == "mypy" and class_ == trio.Nursery:
            extra.remove("cancel_scope")

        # These are (mostly? solely?) *runtime* attributes, often set in
        # __init__, which doesn't show up with dir() or inspect.getmembers,
        # but we get them in the way we query mypy & jedi
        EXTRAS = {
            trio.DTLSChannel: {"peer_address", "endpoint"},
            trio.DTLSEndpoint: {"socket", "incoming_packets_buffer"},
            trio.Process: {"args", "pid", "stderr", "stdin", "stdio", "stdout"},
            trio.SSLListener: {"transport_listener"},
            trio.SSLStream: {"transport_stream"},
            trio.SocketListener: {"socket"},
            trio.SocketStream: {"socket"},
            trio.testing.MemoryReceiveStream: {"close_hook", "receive_some_hook"},
            trio.testing.MemorySendStream: {
                "close_hook",
                "send_all_hook",
                "wait_send_all_might_not_block_hook",
            },
            trio.testing.Matcher: {
                "exception_type",
                "match",
                "check",
            },
        }
        if tool == "mypy" and class_ in EXTRAS:
            before = len(extra)
            extra -= EXTRAS[class_]
            assert len(extra) == before - len(EXTRAS[class_])

        # probably an issue with mypy....
        if tool == "mypy" and class_ == trio.Path and sys.platform == "win32":
            before = len(missing)
            missing -= {"owner", "group", "is_mount"}
            assert len(missing) == before - 3

        # TODO: why is this? Is it a problem?
        # see https://github.com/python-trio/trio/pull/2631#discussion_r1185615916
        if class_ == trio.StapledStream:
            extra.remove("receive_stream")
            extra.remove("send_stream")

        # I have not researched why these are missing, should maybe create an issue
        # upstream with jedi
        if tool == "jedi" and sys.version_info >= (3, 11):
            if class_ in (
                trio.DTLSChannel,
                trio.MemoryReceiveChannel,
                trio.MemorySendChannel,
                trio.SSLListener,
                trio.SocketListener,
            ):
                missing.remove("__aenter__")
                missing.remove("__aexit__")
            if class_ in (trio.DTLSChannel, trio.MemoryReceiveChannel):
                missing.remove("__aiter__")
                missing.remove("__anext__")

        # __getattr__ is intentionally hidden behind type guard. That hook then
        # forwards property accesses to PurePath, meaning these names aren't directly on
        # the class.
        if class_ == trio.Path:
            missing.remove("__getattr__")
            before = len(extra)
            extra -= {
                "anchor",
                "drive",
                "name",
                "parent",
                "parents",
                "parts",
                "root",
                "stem",
                "suffix",
                "suffixes",
            }
            assert len(extra) == before - 10

        if missing or extra:  # pragma: no cover
            errors[f"{module_name}.{class_name}"] = {
                "missing": missing,
                "extra": extra,
            }

    # `assert not errors` will not print the full content of errors, even with
    # `--verbose`, so we manually print it
    if errors:  # pragma: no cover
        from pprint import pprint

        print(f"\n{tool} can't see the following symbols in {module_name}:")
        pprint(errors)
    assert not errors


def test_nopublic_is_final() -> None:
    """Check all NoPublicConstructor classes are also @final."""
    assert class_is_final(_util.NoPublicConstructor)  # This is itself final.

    for module in ALL_MODULES:
        for _name, class_ in module.__dict__.items():
            if isinstance(class_, _util.NoPublicConstructor):
                assert class_is_final(class_)


def test_classes_are_final() -> None:
    # Sanity checks.
    assert not class_is_final(object)
    assert class_is_final(bool)

    for module in PUBLIC_MODULES:
        for name, class_ in module.__dict__.items():
            if not isinstance(class_, type):
                continue
            # Deprecated classes are exported with a leading underscore
            if name.startswith("_"):  # pragma: no cover
                continue

            # Abstract classes can be subclassed, because that's the whole
            # point of ABCs
            if inspect.isabstract(class_):
                continue
            # Same with protocols, but only direct children.
            if Protocol in class_.__bases__ or Protocol_ext in class_.__bases__:
                continue
            # Exceptions are allowed to be subclassed, because exception
            # subclassing isn't used to inherit behavior.
            if issubclass(class_, BaseException):
                continue
            # These are classes that are conceptually abstract, but
            # inspect.isabstract returns False for boring reasons.
            if class_ is trio.abc.Instrument or class_ is trio.socket.SocketType:
                continue
            # ... insert other special cases here ...

            # don't care about the *Statistics classes
            if name.endswith("Statistics"):
                continue

            assert class_is_final(class_)
