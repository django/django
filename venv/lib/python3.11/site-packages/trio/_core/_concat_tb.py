from __future__ import annotations

from types import TracebackType
from typing import Any, ClassVar, cast

################################################################
# concat_tb
################################################################

# We need to compute a new traceback that is the concatenation of two existing
# tracebacks. This requires copying the entries in 'head' and then pointing
# the final tb_next to 'tail'.
#
# NB: 'tail' might be None, which requires some special handling in the ctypes
# version.
#
# The complication here is that Python doesn't actually support copying or
# modifying traceback objects, so we have to get creative...
#
# On CPython, we use ctypes. On PyPy, we use "transparent proxies".
#
# Jinja2 is a useful source of inspiration:
#   https://github.com/pallets/jinja/blob/main/src/jinja2/debug.py

try:
    import tputil
except ImportError:
    # ctypes it is
    import ctypes

    # How to handle refcounting? I don't want to use ctypes.py_object because
    # I don't understand or trust it, and I don't want to use
    # ctypes.pythonapi.Py_{Inc,Dec}Ref because we might clash with user code
    # that also tries to use them but with different types. So private _ctypes
    # APIs it is!
    import _ctypes

    class CTraceback(ctypes.Structure):
        _fields_: ClassVar = [
            ("PyObject_HEAD", ctypes.c_byte * object().__sizeof__()),
            ("tb_next", ctypes.c_void_p),
            ("tb_frame", ctypes.c_void_p),
            ("tb_lasti", ctypes.c_int),
            ("tb_lineno", ctypes.c_int),
        ]

    def copy_tb(base_tb: TracebackType, tb_next: TracebackType | None) -> TracebackType:
        # TracebackType has no public constructor, so allocate one the hard way
        try:
            raise ValueError
        except ValueError as exc:
            new_tb = exc.__traceback__
            assert new_tb is not None
        c_new_tb = CTraceback.from_address(id(new_tb))

        # At the C level, tb_next either points to the next traceback or is
        # NULL. c_void_p and the .tb_next accessor both convert NULL to None,
        # but we shouldn't DECREF None just because we assigned to a NULL
        # pointer! Here we know that our new traceback has only 1 frame in it,
        # so we can assume the tb_next field is NULL.
        assert c_new_tb.tb_next is None
        # If tb_next is None, then we want to set c_new_tb.tb_next to NULL,
        # which it already is, so we're done. Otherwise, we have to actually
        # do some work:
        if tb_next is not None:
            _ctypes.Py_INCREF(tb_next)  # type: ignore[attr-defined]
            c_new_tb.tb_next = id(tb_next)

        assert c_new_tb.tb_frame is not None
        _ctypes.Py_INCREF(base_tb.tb_frame)  # type: ignore[attr-defined]
        old_tb_frame = new_tb.tb_frame
        c_new_tb.tb_frame = id(base_tb.tb_frame)
        _ctypes.Py_DECREF(old_tb_frame)  # type: ignore[attr-defined]

        c_new_tb.tb_lasti = base_tb.tb_lasti
        c_new_tb.tb_lineno = base_tb.tb_lineno

        try:
            return new_tb
        finally:
            # delete references from locals to avoid creating cycles
            # see test_cancel_scope_exit_doesnt_create_cyclic_garbage
            del new_tb, old_tb_frame

else:
    # http://doc.pypy.org/en/latest/objspace-proxies.html
    def copy_tb(base_tb: TracebackType, tb_next: TracebackType | None) -> TracebackType:
        # tputil.ProxyOperation is PyPy-only, and there's no way to specify
        # cpython/pypy in current type checkers.
        def controller(operation: tputil.ProxyOperation) -> Any | None:  # type: ignore[no-any-unimported]
            # Rationale for pragma: I looked fairly carefully and tried a few
            # things, and AFAICT it's not actually possible to get any
            # 'opname' that isn't __getattr__ or __getattribute__. So there's
            # no missing test we could add, and no value in coverage nagging
            # us about adding one.
            if (
                operation.opname
                in {
                    "__getattribute__",
                    "__getattr__",
                }
                and operation.args[0] == "tb_next"
            ):  # pragma: no cover
                return tb_next
            return operation.delegate()  # Delegate is reverting to original behaviour

        return cast(
            TracebackType, tputil.make_proxy(controller, type(base_tb), base_tb)
        )  # Returns proxy to traceback


# this is used for collapsing single-exception ExceptionGroups when using
# `strict_exception_groups=False`. Once that is retired this function and its helper can
# be removed as well.
def concat_tb(
    head: TracebackType | None, tail: TracebackType | None
) -> TracebackType | None:
    # We have to use an iterative algorithm here, because in the worst case
    # this might be a RecursionError stack that is by definition too deep to
    # process by recursion!
    head_tbs = []
    pointer = head
    while pointer is not None:
        head_tbs.append(pointer)
        pointer = pointer.tb_next
    current_head = tail
    for head_tb in reversed(head_tbs):
        current_head = copy_tb(head_tb, tb_next=current_head)
    return current_head
