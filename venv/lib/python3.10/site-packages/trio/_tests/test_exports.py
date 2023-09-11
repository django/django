import enum
import functools
import importlib
import inspect
import json
import socket as stdlib_socket
import sys
from pathlib import Path
from types import ModuleType

import attrs
import pytest

import trio
import trio.testing

from .. import _core, _util
from .._core._tests.tutil import slow
from .pytest_plugin import RUN_SLOW

mypy_cache_updated = False


def _ensure_mypy_cache_updated():
    # This pollutes the `empty` dir. Should this be changed?
    from mypy.api import run

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


def test_core_is_properly_reexported():
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


def public_modules(module):
    yield module
    for name, class_ in module.__dict__.items():
        if name.startswith("_"):  # pragma: no cover
            continue
        if not isinstance(class_, ModuleType):
            continue
        if not class_.__name__.startswith(module.__name__):  # pragma: no cover
            continue
        if class_ is module:  # pragma: no cover
            continue
        yield from public_modules(class_)


PUBLIC_MODULES = list(public_modules(trio))
PUBLIC_MODULE_NAMES = [m.__name__ for m in PUBLIC_MODULES]


# It doesn't make sense for downstream redistributors to run this test, since
# they might be using a newer version of Python with additional symbols which
# won't be reflected in trio.socket, and this shouldn't cause downstream test
# runs to start failing.
@pytest.mark.redistributors_should_skip
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
def test_static_tool_sees_all_symbols(tool, modname, tmpdir):
    module = importlib.import_module(modname)

    def no_underscores(symbols):
        return {symbol for symbol in symbols if not symbol.startswith("_")}

    runtime_names = no_underscores(dir(module))

    # ignore deprecated module `tests` being invisible
    if modname == "trio":
        runtime_names.discard("tests")

    if tool in ("mypy", "pyright_verifytypes"):
        # create py.typed file
        py_typed_path = Path(trio.__file__).parent / "py.typed"
        py_typed_exists = py_typed_path.exists()
        if not py_typed_exists:  # pragma: no branch
            py_typed_path.write_text("")

    if tool == "pylint":
        from pylint.lint import PyLinter

        linter = PyLinter()
        ast = linter.get_ast(module.__file__, modname)
        static_names = no_underscores(ast)
    elif tool == "jedi":
        import jedi

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
        if mod_cache.is_dir():
            mod_cache = mod_cache / "__init__.data.json"
        else:
            mod_cache = trio_cache / (modname + ".data.json")

        assert mod_cache.exists() and mod_cache.is_file()
        with mod_cache.open() as cache_file:
            cache_json = json.loads(cache_file.read())
            static_names = no_underscores(
                key
                for key, value in cache_json["names"].items()
                if not key.startswith(".") and value["kind"] == "Gdef"
            )
    elif tool == "pyright_verifytypes":
        if not RUN_SLOW:  # pragma: no cover
            pytest.skip("use --run-slow to check against mypy")
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

        # pyright ignores the symbol defined behind `if False`
        if modname == "trio":
            static_names.add("testing")

        # these are hidden behind `if sys.plaftorm != "win32" or not TYPE_CHECKING`
        # so presumably pyright is parsing that if statement, in which case we don't
        # care about them being missing.
        if modname == "trio.socket" and sys.platform == "win32":
            ignored_missing_names = {"if_indextoname", "if_nameindex", "if_nametoindex"}
            assert static_names.isdisjoint(ignored_missing_names)
            static_names.update(ignored_missing_names)

    else:  # pragma: no cover
        assert False

    # remove py.typed file
    if tool in ("mypy", "pyright_verifytypes") and not py_typed_exists:
        py_typed_path.unlink()

    # mypy handles errors with an `assert` in its branch
    if tool == "mypy":
        return

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
        assert False


# this could be sped up by only invoking mypy once per module, or even once for all
# modules, instead of once per class.
@slow
# see comment on test_static_tool_sees_all_symbols
@pytest.mark.redistributors_should_skip
# Static analysis tools often have trouble with alpha releases, where Python's
# internals are in flux, grammar may not have settled down, etc.
@pytest.mark.skipif(
    sys.version_info.releaselevel == "alpha",
    reason="skip static introspection tools on Python dev/alpha releases",
)
@pytest.mark.parametrize("module_name", PUBLIC_MODULE_NAMES)
@pytest.mark.parametrize("tool", ["jedi", "mypy"])
def test_static_tool_sees_class_members(tool, module_name, tmpdir) -> None:
    module = PUBLIC_MODULES[PUBLIC_MODULE_NAMES.index(module_name)]

    # ignore hidden, but not dunder, symbols
    def no_hidden(symbols):
        return {
            symbol
            for symbol in symbols
            if (not symbol.startswith("_")) or symbol.startswith("__")
        }

    py_typed_path = Path(trio.__file__).parent / "py.typed"
    py_typed_exists = py_typed_path.exists()

    if tool == "mypy":
        if sys.implementation.name != "cpython":
            pytest.skip("mypy not installed in tests on pypy")
        # create py.typed file
        # remove this logic when trio is marked with py.typed proper
        if not py_typed_exists:  # pragma: no branch
            py_typed_path.write_text("")

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

        assert mod_cache.exists() and mod_cache.is_file()
        with mod_cache.open() as cache_file:
            cache_json = json.loads(cache_file.read())

        # skip a bunch of file-system activity (probably can un-memoize?)
        @functools.lru_cache()
        def lookup_symbol(symbol):
            topname, *modname, name = symbol.split(".")
            version = next(cache.glob("3.*/"))
            mod_cache = version / topname
            if not mod_cache.is_dir():
                mod_cache = version / (topname + ".data.json")

            if modname:
                for piece in modname[:-1]:
                    mod_cache /= piece
                next_cache = mod_cache / modname[-1]
                if next_cache.is_dir():
                    mod_cache = next_cache / "__init__.data.json"
                else:
                    mod_cache = mod_cache / (modname[-1] + ".data.json")

            with mod_cache.open() as f:
                return json.loads(f.read())["names"][name]

    errors: dict[str, object] = {}
    for class_name, class_ in module.__dict__.items():
        if not isinstance(class_, type):
            continue
        if module_name == "trio.socket" and class_name in dir(stdlib_socket):
            continue
        # Deprecated classes are exported with a leading underscore
        # We don't care about errors in _MultiError as that's on its way out anyway
        if class_name.startswith("_"):  # pragma: no cover
            continue

        # dir() and inspect.getmembers doesn't display properties from the metaclass
        # also ignore some dunder methods that tend to differ but are of no consequence
        ignore_names = set(dir(type(class_))) | {
            "__annotations__",
            "__attrs_attrs__",
            "__attrs_own_setattr__",
            "__class_getitem__",
            "__getstate__",
            "__match_args__",
            "__order__",
            "__orig_bases__",
            "__parameters__",
            "__setstate__",
            "__slots__",
            "__weakref__",
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
            import jedi

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
            assert False, "unknown tool"

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

        # TODO: this *should* be visible via `dir`!!
        if tool == "mypy" and class_ == trio.Nursery:
            extra.remove("cancel_scope")

        # TODO: I'm not so sure about these, but should still be looked at.
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

        # intentionally hidden behind type guard
        if class_ == trio.Path:
            missing.remove("__getattr__")

        if missing or extra:  # pragma: no cover
            errors[f"{module_name}.{class_name}"] = {
                "missing": missing,
                "extra": extra,
            }

    # clean up created py.typed file
    if tool == "mypy" and not py_typed_exists:
        py_typed_path.unlink()

    # `assert not errors` will not print the full content of errors, even with
    # `--verbose`, so we manually print it
    if errors:  # pragma: no cover
        from pprint import pprint

        print(f"\n{tool} can't see the following symbols in {module_name}:")
        pprint(errors)
    assert not errors


def test_classes_are_final():
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
            # Exceptions are allowed to be subclassed, because exception
            # subclassing isn't used to inherit behavior.
            if issubclass(class_, BaseException):
                continue
            # These are classes that are conceptually abstract, but
            # inspect.isabstract returns False for boring reasons.
            if class_ in {trio.abc.Instrument, trio.socket.SocketType}:
                continue
            # Enums have their own metaclass, so we can't use our metaclasses.
            # And I don't think there's a lot of risk from people subclassing
            # enums...
            if issubclass(class_, enum.Enum):
                continue
            # ... insert other special cases here ...

            assert isinstance(class_, _util.Final)
