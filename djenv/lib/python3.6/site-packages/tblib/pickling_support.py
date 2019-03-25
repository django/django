try:
    import copy_reg
except ImportError:
    import copyreg as copy_reg
from types import TracebackType

from . import Frame
from . import Traceback


def unpickle_traceback(tb_frame, tb_lineno, tb_next):
    ret = object.__new__(Traceback)
    ret.tb_frame = tb_frame
    ret.tb_lineno = tb_lineno
    ret.tb_next = tb_next
    return ret.as_traceback()


def pickle_traceback(tb):
    return unpickle_traceback, (Frame(tb.tb_frame), tb.tb_lineno, tb.tb_next and Traceback(tb.tb_next))


def install():
    copy_reg.pickle(TracebackType, pickle_traceback)
