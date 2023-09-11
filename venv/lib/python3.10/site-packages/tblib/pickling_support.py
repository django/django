import sys
from types import TracebackType

from . import Frame
from . import Traceback

if sys.version_info.major >= 3:
    import copyreg
else:
    import copy_reg as copyreg


def unpickle_traceback(tb_frame, tb_lineno, tb_next):
    ret = object.__new__(Traceback)
    ret.tb_frame = tb_frame
    ret.tb_lineno = tb_lineno
    ret.tb_next = tb_next
    return ret.as_traceback()


def pickle_traceback(tb):
    return unpickle_traceback, (Frame(tb.tb_frame), tb.tb_lineno, tb.tb_next and Traceback(tb.tb_next))


def unpickle_exception(func, args, cause, tb):
    inst = func(*args)
    inst.__cause__ = cause
    inst.__traceback__ = tb
    return inst


def pickle_exception(obj):
    # All exceptions, unlike generic Python objects, define __reduce_ex__
    # __reduce_ex__(4) should be no different from __reduce_ex__(3).
    # __reduce_ex__(5) could bring benefits in the unlikely case the exception
    # directly contains buffers, but PickleBuffer objects will cause a crash when
    # running on protocol=4, and there's no clean way to figure out the current
    # protocol from here. Note that any object returned by __reduce_ex__(3) will
    # still be pickled with protocol 5 if pickle.dump() is running with it.
    rv = obj.__reduce_ex__(3)
    if isinstance(rv, str):
        raise TypeError('str __reduce__ output is not supported')
    assert isinstance(rv, tuple)
    assert len(rv) >= 2

    return (unpickle_exception, rv[:2] + (obj.__cause__, obj.__traceback__)) + rv[2:]


def _get_subclasses(cls):
    # Depth-first traversal of all direct and indirect subclasses of cls
    to_visit = [cls]
    while to_visit:
        this = to_visit.pop()
        yield this
        to_visit += list(this.__subclasses__())


def install(*exc_classes_or_instances):
    copyreg.pickle(TracebackType, pickle_traceback)

    if sys.version_info.major < 3:
        # Dummy decorator?
        if len(exc_classes_or_instances) == 1:
            exc = exc_classes_or_instances[0]
            if isinstance(exc, type) and issubclass(exc, BaseException):
                return exc
        return

    if not exc_classes_or_instances:
        for exception_cls in _get_subclasses(BaseException):
            copyreg.pickle(exception_cls, pickle_exception)
        return

    for exc in exc_classes_or_instances:
        if isinstance(exc, BaseException):
            while exc is not None:
                copyreg.pickle(type(exc), pickle_exception)
                exc = exc.__cause__
        elif isinstance(exc, type) and issubclass(exc, BaseException):
            copyreg.pickle(exc, pickle_exception)
            # Allow using @install as a decorator for Exception classes
            if len(exc_classes_or_instances) == 1:
                return exc
        else:
            raise TypeError('Expected subclasses or instances of BaseException, got %s' % (type(exc)))
