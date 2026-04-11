import copyreg
import sys
from functools import partial
from types import TracebackType

from . import Frame
from . import Traceback

if sys.version_info < (3, 11):
    ExceptionGroup = None


def unpickle_traceback(tb_frame, tb_lineno, tb_next):
    ret = object.__new__(Traceback)
    ret.tb_frame = tb_frame
    ret.tb_lineno = tb_lineno
    ret.tb_next = tb_next
    return ret.as_traceback()


def pickle_traceback(tb, *, get_locals=None):
    return unpickle_traceback, (
        Frame(tb.tb_frame, get_locals=get_locals),
        tb.tb_lineno,
        tb.tb_next and Traceback(tb.tb_next, get_locals=get_locals),
    )


def unpickle_exception_with_attrs(func, attrs, cause, tb, context, suppress_context, notes, args=()):
    inst = func.__new__(func, *args)
    for key, value in attrs.items():
        setattr(inst, key, value)
    inst.__cause__ = cause
    inst.__traceback__ = tb
    inst.__context__ = context
    inst.__suppress_context__ = suppress_context
    if notes is not None:
        inst.__notes__ = notes
    return inst


# Note: Older versions of tblib will generate pickle archives that call unpickle_exception() with
# fewer arguments. We assign default values to some of the arguments to support this.
def unpickle_exception(func, args, cause, tb, context=None, suppress_context=False, notes=None):
    inst = func(*args)
    inst.__cause__ = cause
    inst.__traceback__ = tb
    inst.__context__ = context
    inst.__suppress_context__ = suppress_context
    if notes is not None:
        inst.__notes__ = notes
    return inst


def pickle_exception(
    obj, builtin_reducers=(OSError.__reduce__, BaseException.__reduce__), builtin_inits=(OSError.__init__, BaseException.__init__)
):
    reduced_value = obj.__reduce__()
    if isinstance(reduced_value, str):
        raise TypeError('Did not expect {repr(obj)}.__reduce__() to return a string!')

    func = type(obj)
    # Detect busted objects: they have a custom __init__ but no __reduce__.
    # This also means the resulting exceptions may be a bit "dulled" down - the args from __reduce__ are discarded.
    if func.__reduce__ in builtin_reducers and func.__init__ not in builtin_inits:
        _, args, *optionals = reduced_value
        attrs = {
            '__dict__': obj.__dict__,
            'args': obj.args,
        }
        args = ()
        if isinstance(obj, OSError):
            # Only set OSError-specific attributes if they are not None
            # Setting them to None explicitly breaks the string representation
            if obj.errno is not None:
                attrs['errno'] = obj.errno
            if obj.strerror is not None:
                attrs['strerror'] = obj.strerror
            if (winerror := getattr(obj, 'winerror', None)) is not None:
                attrs['winerror'] = winerror
            if obj.filename is not None:
                attrs['filename'] = obj.filename
            if obj.filename2 is not None:
                attrs['filename2'] = obj.filename2
        if ExceptionGroup is not None and isinstance(obj, ExceptionGroup):
            args = (obj.message, obj.exceptions)

        return (
            unpickle_exception_with_attrs,
            (
                func,
                attrs,
                obj.__cause__,
                obj.__traceback__,
                obj.__context__,
                obj.__suppress_context__,
                # __notes__ doesn't exist prior to Python 3.11; and even on Python 3.11 it may be absent
                getattr(obj, '__notes__', None),
                args,
            ),
            *optionals,
        )
    else:
        func, args, *optionals = reduced_value

        return (
            unpickle_exception,
            (
                func,
                args,
                obj.__cause__,
                obj.__traceback__,
                obj.__context__,
                obj.__suppress_context__,
                # __notes__ doesn't exist prior to Python 3.11; and even on Python 3.11 it may be absent
                getattr(obj, '__notes__', None),
            ),
            *optionals,
        )


def _get_subclasses(cls):
    # Depth-first traversal of all direct and indirect subclasses of cls
    to_visit = [cls]
    while to_visit:
        this = to_visit.pop()
        yield this
        to_visit += list(this.__subclasses__())


def install(*exc_classes_or_instances, get_locals=None):
    """
    Args:

        get_locals (callable): A function that take a frame argument and returns a dict. See :class:`tblib.Traceback` class for example.
    """
    copyreg.pickle(TracebackType, partial(pickle_traceback, get_locals=get_locals))

    if not exc_classes_or_instances:
        for exception_cls in _get_subclasses(BaseException):
            copyreg.pickle(exception_cls, pickle_exception)
        return

    for exc in exc_classes_or_instances:
        if isinstance(exc, BaseException):
            _install_for_instance(exc, set())
        elif isinstance(exc, type) and issubclass(exc, BaseException):
            copyreg.pickle(exc, pickle_exception)
            # Allow using @install as a decorator for Exception classes
            if len(exc_classes_or_instances) == 1:
                return exc
        else:
            raise TypeError(f'Expected subclasses or instances of BaseException, got {type(exc)}')


def _install_for_instance(exc, seen):
    assert isinstance(exc, BaseException)

    # Prevent infinite recursion if we somehow get a self-referential exception. (Self-referential
    # exceptions should never normally happen, but if it did somehow happen, we want to pickle the
    # exception faithfully so the developer can troubleshoot why it happened.)
    if id(exc) in seen:
        return
    seen.add(id(exc))

    copyreg.pickle(type(exc), pickle_exception)

    if exc.__cause__ is not None:
        _install_for_instance(exc.__cause__, seen)
    if exc.__context__ is not None:
        _install_for_instance(exc.__context__, seen)

    # This case is meant to cover BaseExceptionGroup on Python 3.11 as well as backports like the
    # exceptiongroup module
    if hasattr(exc, 'exceptions') and isinstance(exc.exceptions, (tuple, list)):
        for subexc in exc.exceptions:
            if isinstance(subexc, BaseException):
                _install_for_instance(subexc, seen)
