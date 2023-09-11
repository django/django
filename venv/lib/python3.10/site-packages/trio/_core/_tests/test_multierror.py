import gc
import os
import pickle
import re
import subprocess
import sys
import warnings
from pathlib import Path
from traceback import extract_tb, print_exception

import pytest

from ... import TrioDeprecationWarning
from ..._core import open_nursery
from .._multierror import MultiError, NonBaseMultiError, concat_tb
from .tutil import slow

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


class NotHashableException(Exception):
    code = None

    def __init__(self, code):
        super().__init__()
        self.code = code

    def __eq__(self, other):
        if not isinstance(other, NotHashableException):
            return False
        return self.code == other.code


async def raise_nothashable(code):
    raise NotHashableException(code)


def raiser1():
    raiser1_2()


def raiser1_2():
    raiser1_3()


def raiser1_3():
    raise ValueError("raiser1_string")


def raiser2():
    raiser2_2()


def raiser2_2():
    raise KeyError("raiser2_string")


def raiser3():
    raise NameError


def get_exc(raiser):
    try:
        raiser()
    except Exception as exc:
        return exc


def get_tb(raiser):
    return get_exc(raiser).__traceback__


def test_concat_tb():
    tb1 = get_tb(raiser1)
    tb2 = get_tb(raiser2)

    # These return a list of (filename, lineno, fn name, text) tuples
    # https://docs.python.org/3/library/traceback.html#traceback.extract_tb
    entries1 = extract_tb(tb1)
    entries2 = extract_tb(tb2)

    tb12 = concat_tb(tb1, tb2)
    assert extract_tb(tb12) == entries1 + entries2

    tb21 = concat_tb(tb2, tb1)
    assert extract_tb(tb21) == entries2 + entries1

    # Check degenerate cases
    assert extract_tb(concat_tb(None, tb1)) == entries1
    assert extract_tb(concat_tb(tb1, None)) == entries1
    assert concat_tb(None, None) is None

    # Make sure the original tracebacks didn't get mutated by mistake
    assert extract_tb(get_tb(raiser1)) == entries1
    assert extract_tb(get_tb(raiser2)) == entries2


def test_MultiError():
    exc1 = get_exc(raiser1)
    exc2 = get_exc(raiser2)

    assert MultiError([exc1]) is exc1
    m = MultiError([exc1, exc2])
    assert m.exceptions == (exc1, exc2)
    assert "ValueError" in str(m)
    assert "ValueError" in repr(m)

    with pytest.raises(TypeError):
        MultiError(object())
    with pytest.raises(TypeError):
        MultiError([KeyError(), ValueError])


def test_MultiErrorOfSingleMultiError():
    # For MultiError([MultiError]), ensure there is no bad recursion by the
    # constructor where __init__ is called if __new__ returns a bare MultiError.
    exceptions = (KeyError(), ValueError())
    a = MultiError(exceptions)
    b = MultiError([a])
    assert b == a
    assert b.exceptions == exceptions


async def test_MultiErrorNotHashable():
    exc1 = NotHashableException(42)
    exc2 = NotHashableException(4242)
    exc3 = ValueError()
    assert exc1 != exc2
    assert exc1 != exc3

    with pytest.raises(MultiError):
        async with open_nursery() as nursery:
            nursery.start_soon(raise_nothashable, 42)
            nursery.start_soon(raise_nothashable, 4242)


def test_MultiError_filter_NotHashable():
    excs = MultiError([NotHashableException(42), ValueError()])

    def handle_ValueError(exc):
        if isinstance(exc, ValueError):
            return None
        else:
            return exc

    with pytest.warns(TrioDeprecationWarning):
        filtered_excs = MultiError.filter(handle_ValueError, excs)

    assert isinstance(filtered_excs, NotHashableException)


def make_tree():
    # Returns an object like:
    #   MultiError([
    #     MultiError([
    #       ValueError,
    #       KeyError,
    #     ]),
    #     NameError,
    #   ])
    # where all exceptions except the root have a non-trivial traceback.
    exc1 = get_exc(raiser1)
    exc2 = get_exc(raiser2)
    exc3 = get_exc(raiser3)

    # Give m12 a non-trivial traceback
    try:
        raise MultiError([exc1, exc2])
    except BaseException as m12:
        return MultiError([m12, exc3])


def assert_tree_eq(m1, m2):
    if m1 is None or m2 is None:
        assert m1 is m2
        return
    assert type(m1) is type(m2)
    assert extract_tb(m1.__traceback__) == extract_tb(m2.__traceback__)
    assert_tree_eq(m1.__cause__, m2.__cause__)
    assert_tree_eq(m1.__context__, m2.__context__)
    if isinstance(m1, MultiError):
        assert len(m1.exceptions) == len(m2.exceptions)
        for e1, e2 in zip(m1.exceptions, m2.exceptions):
            assert_tree_eq(e1, e2)


def test_MultiError_filter():
    def null_handler(exc):
        return exc

    m = make_tree()
    assert_tree_eq(m, m)
    with pytest.warns(TrioDeprecationWarning):
        assert MultiError.filter(null_handler, m) is m

    assert_tree_eq(m, make_tree())

    # Make sure we don't pick up any detritus if run in a context where
    # implicit exception chaining would like to kick in
    m = make_tree()
    try:
        raise ValueError
    except ValueError:
        with pytest.warns(TrioDeprecationWarning):
            assert MultiError.filter(null_handler, m) is m
    assert_tree_eq(m, make_tree())

    def simple_filter(exc):
        if isinstance(exc, ValueError):
            return None
        if isinstance(exc, KeyError):
            return RuntimeError()
        return exc

    with pytest.warns(TrioDeprecationWarning):
        new_m = MultiError.filter(simple_filter, make_tree())

    assert isinstance(new_m, MultiError)
    assert len(new_m.exceptions) == 2
    # was: [[ValueError, KeyError], NameError]
    # ValueError disappeared & KeyError became RuntimeError, so now:
    assert isinstance(new_m.exceptions[0], RuntimeError)
    assert isinstance(new_m.exceptions[1], NameError)

    # implicit chaining:
    assert isinstance(new_m.exceptions[0].__context__, KeyError)

    # also, the traceback on the KeyError incorporates what used to be the
    # traceback on its parent MultiError
    orig = make_tree()
    # make sure we have the right path
    assert isinstance(orig.exceptions[0].exceptions[1], KeyError)
    # get original traceback summary
    orig_extracted = (
        extract_tb(orig.__traceback__)
        + extract_tb(orig.exceptions[0].__traceback__)
        + extract_tb(orig.exceptions[0].exceptions[1].__traceback__)
    )

    def p(exc):
        print_exception(type(exc), exc, exc.__traceback__)

    p(orig)
    p(orig.exceptions[0])
    p(orig.exceptions[0].exceptions[1])
    p(new_m.exceptions[0].__context__)
    # compare to the new path
    assert new_m.__traceback__ is None
    new_extracted = extract_tb(new_m.exceptions[0].__context__.__traceback__)
    assert orig_extracted == new_extracted

    # check preserving partial tree
    def filter_NameError(exc):
        if isinstance(exc, NameError):
            return None
        return exc

    m = make_tree()
    with pytest.warns(TrioDeprecationWarning):
        new_m = MultiError.filter(filter_NameError, m)
    # with the NameError gone, the other branch gets promoted
    assert new_m is m.exceptions[0]

    # check fully handling everything
    def filter_all(exc):
        return None

    with pytest.warns(TrioDeprecationWarning):
        assert MultiError.filter(filter_all, make_tree()) is None


def test_MultiError_catch():
    # No exception to catch

    def noop(_):
        pass  # pragma: no cover

    with pytest.warns(TrioDeprecationWarning), MultiError.catch(noop):
        pass

    # Simple pass-through of all exceptions
    m = make_tree()
    with pytest.raises(MultiError) as excinfo:
        with pytest.warns(TrioDeprecationWarning), MultiError.catch(lambda exc: exc):
            raise m
    assert excinfo.value is m
    # Should be unchanged, except that we added a traceback frame by raising
    # it here
    assert m.__traceback__ is not None
    assert m.__traceback__.tb_frame.f_code.co_name == "test_MultiError_catch"
    assert m.__traceback__.tb_next is None
    m.__traceback__ = None
    assert_tree_eq(m, make_tree())

    # Swallows everything
    with pytest.warns(TrioDeprecationWarning), MultiError.catch(lambda _: None):
        raise make_tree()

    def simple_filter(exc):
        if isinstance(exc, ValueError):
            return None
        if isinstance(exc, KeyError):
            return RuntimeError()
        return exc

    with pytest.raises(MultiError) as excinfo:
        with pytest.warns(TrioDeprecationWarning), MultiError.catch(simple_filter):
            raise make_tree()
    new_m = excinfo.value
    assert isinstance(new_m, MultiError)
    assert len(new_m.exceptions) == 2
    # was: [[ValueError, KeyError], NameError]
    # ValueError disappeared & KeyError became RuntimeError, so now:
    assert isinstance(new_m.exceptions[0], RuntimeError)
    assert isinstance(new_m.exceptions[1], NameError)
    # Make sure that Python did not successfully attach the old MultiError to
    # our new MultiError's __context__
    assert not new_m.__suppress_context__
    assert new_m.__context__ is None

    # check preservation of __cause__ and __context__
    v = ValueError()
    v.__cause__ = KeyError()
    with pytest.raises(ValueError) as excinfo:
        with pytest.warns(TrioDeprecationWarning), MultiError.catch(lambda exc: exc):
            raise v
    assert isinstance(excinfo.value.__cause__, KeyError)

    v = ValueError()
    context = KeyError()
    v.__context__ = context
    with pytest.raises(ValueError) as excinfo:
        with pytest.warns(TrioDeprecationWarning), MultiError.catch(lambda exc: exc):
            raise v
    assert excinfo.value.__context__ is context
    assert not excinfo.value.__suppress_context__

    for suppress_context in [True, False]:
        v = ValueError()
        context = KeyError()
        v.__context__ = context
        v.__suppress_context__ = suppress_context
        distractor = RuntimeError()
        with pytest.raises(ValueError) as excinfo:

            def catch_RuntimeError(exc):
                if isinstance(exc, RuntimeError):
                    return None
                else:
                    return exc

            with pytest.warns(TrioDeprecationWarning):
                with MultiError.catch(catch_RuntimeError):
                    raise MultiError([v, distractor])
        assert excinfo.value.__context__ is context
        assert excinfo.value.__suppress_context__ == suppress_context


@pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Only makes sense with refcounting GC"
)
def test_MultiError_catch_doesnt_create_cyclic_garbage():
    # https://github.com/python-trio/trio/pull/2063
    gc.collect()
    old_flags = gc.get_debug()

    def make_multi():
        # make_tree creates cycles itself, so a simple
        raise MultiError([get_exc(raiser1), get_exc(raiser2)])

    def simple_filter(exc):
        if isinstance(exc, ValueError):
            return Exception()
        if isinstance(exc, KeyError):
            return RuntimeError()
        assert False, "only ValueError and KeyError should exist"  # pragma: no cover

    try:
        gc.set_debug(gc.DEBUG_SAVEALL)
        with pytest.raises(MultiError):
            # covers MultiErrorCatcher.__exit__ and _multierror.copy_tb
            with pytest.warns(TrioDeprecationWarning), MultiError.catch(simple_filter):
                raise make_multi()
        gc.collect()
        assert not gc.garbage
    finally:
        gc.set_debug(old_flags)
        gc.garbage.clear()


def assert_match_in_seq(pattern_list, string):
    offset = 0
    print("looking for pattern matches...")
    for pattern in pattern_list:
        print("checking pattern:", pattern)
        reobj = re.compile(pattern)
        match = reobj.search(string, offset)
        assert match is not None
        offset = match.end()


def test_assert_match_in_seq():
    assert_match_in_seq(["a", "b"], "xx a xx b xx")
    assert_match_in_seq(["b", "a"], "xx b xx a xx")
    with pytest.raises(AssertionError):
        assert_match_in_seq(["a", "b"], "xx b xx a xx")


def test_base_multierror():
    """
    Test that MultiError() with at least one base exception will return a MultiError
    object.
    """

    exc = MultiError([ZeroDivisionError(), KeyboardInterrupt()])
    assert type(exc) is MultiError


def test_non_base_multierror():
    """
    Test that MultiError() without base exceptions will return a NonBaseMultiError
    object.
    """

    exc = MultiError([ZeroDivisionError(), ValueError()])
    assert type(exc) is NonBaseMultiError
    assert isinstance(exc, ExceptionGroup)


def run_script(name, use_ipython=False):
    import trio

    trio_path = Path(trio.__file__).parent.parent
    script_path = Path(__file__).parent / "test_multierror_scripts" / name

    env = dict(os.environ)
    print("parent PYTHONPATH:", env.get("PYTHONPATH"))
    if "PYTHONPATH" in env:  # pragma: no cover
        pp = env["PYTHONPATH"].split(os.pathsep)
    else:
        pp = []
    pp.insert(0, str(trio_path))
    pp.insert(0, str(script_path.parent))
    env["PYTHONPATH"] = os.pathsep.join(pp)
    print("subprocess PYTHONPATH:", env.get("PYTHONPATH"))

    if use_ipython:
        lines = [
            "import runpy",
            f"runpy.run_path(r'{script_path}', run_name='trio.fake')",
            "exit()",
        ]

        cmd = [
            sys.executable,
            "-u",
            "-m",
            "IPython",
            # no startup files
            "--quick",
            "--TerminalIPythonApp.code_to_run=" + "\n".join(lines),
        ]
    else:
        cmd = [sys.executable, "-u", str(script_path)]
    print("running:", cmd)
    completed = subprocess.run(
        cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    print("process output:")
    print(completed.stdout.decode("utf-8"))
    return completed


def check_simple_excepthook(completed, uses_ipython):
    assert_match_in_seq(
        [
            "in <cell line: "
            if uses_ipython and sys.version_info >= (3, 8)
            else "in <module>",
            "MultiError",
            "--- 1 ---",
            "in exc1_fn",
            "ValueError",
            "--- 2 ---",
            "in exc2_fn",
            "KeyError",
        ],
        completed.stdout.decode("utf-8"),
    )


try:
    import IPython  # noqa: F401
except ImportError:  # pragma: no cover
    have_ipython = False
else:
    have_ipython = True

need_ipython = pytest.mark.skipif(not have_ipython, reason="need IPython")


@slow
@need_ipython
def test_ipython_exc_handler():
    completed = run_script("simple_excepthook.py", use_ipython=True)
    check_simple_excepthook(completed, True)


@slow
@need_ipython
def test_ipython_imported_but_unused():
    completed = run_script("simple_excepthook_IPython.py")
    check_simple_excepthook(completed, False)


@slow
@need_ipython
def test_ipython_custom_exc_handler():
    # Check we get a nice warning (but only one!) if the user is using IPython
    # and already has some other set_custom_exc handler installed.
    completed = run_script("ipython_custom_exc.py", use_ipython=True)
    assert_match_in_seq(
        [
            # The warning
            "RuntimeWarning",
            "IPython detected",
            "skip installing Trio",
            # The MultiError
            "MultiError",
            "ValueError",
            "KeyError",
        ],
        completed.stdout.decode("utf-8"),
    )
    # Make sure our other warning doesn't show up
    assert "custom sys.excepthook" not in completed.stdout.decode("utf-8")


@slow
@pytest.mark.skipif(
    not Path("/usr/lib/python3/dist-packages/apport_python_hook.py").exists(),
    reason="need Ubuntu with python3-apport installed",
)
def test_apport_excepthook_monkeypatch_interaction():
    completed = run_script("apport_excepthook.py")
    stdout = completed.stdout.decode("utf-8")

    # No warning
    assert "custom sys.excepthook" not in stdout

    # Proper traceback
    assert_match_in_seq(
        ["--- 1 ---", "KeyError", "--- 2 ---", "ValueError"],
        stdout,
    )


@pytest.mark.parametrize("protocol", range(0, pickle.HIGHEST_PROTOCOL + 1))
def test_pickle_multierror(protocol) -> None:
    # use trio.MultiError to make sure that pickle works through the deprecation layer
    import trio

    my_except = ZeroDivisionError()

    try:
        1 / 0
    except ZeroDivisionError as e:
        my_except = e

    # MultiError will collapse into different classes depending on the errors
    for cls, errors in (
        (ZeroDivisionError, [my_except]),
        (NonBaseMultiError, [my_except, ValueError()]),
        (MultiError, [BaseException(), my_except]),
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", TrioDeprecationWarning)
            me = trio.MultiError(errors)  # type: ignore[attr-defined]
            dump = pickle.dumps(me, protocol=protocol)
            load = pickle.loads(dump)
        assert repr(me) == repr(load)
        assert me.__class__ == load.__class__ == cls

        assert me.__dict__.keys() == load.__dict__.keys()
        for me_val, load_val in zip(me.__dict__.values(), load.__dict__.values()):
            # tracebacks etc are not preserved through pickling for the default
            # exceptions, so we only check that the repr stays the same
            assert repr(me_val) == repr(load_val)
