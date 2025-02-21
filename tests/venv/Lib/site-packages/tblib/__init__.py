import re
import sys
from types import CodeType

__version__ = '3.0.0'
__all__ = 'Traceback', 'TracebackParseError', 'Frame', 'Code'

FRAME_RE = re.compile(r'^\s*File "(?P<co_filename>.+)", line (?P<tb_lineno>\d+)(, in (?P<co_name>.+))?$')


class _AttrDict(dict):
    __slots__ = ()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


# noinspection PyPep8Naming
class __traceback_maker(Exception):
    pass


class TracebackParseError(Exception):
    pass


class Code:
    """
    Class that replicates just enough of the builtin Code object to enable serialization and traceback rendering.
    """

    co_code = None

    def __init__(self, code):
        self.co_filename = code.co_filename
        self.co_name = code.co_name
        self.co_argcount = 0
        self.co_kwonlyargcount = 0
        self.co_varnames = ()
        self.co_nlocals = 0
        self.co_stacksize = 0
        self.co_flags = 64
        self.co_firstlineno = 0


class Frame:
    """
    Class that replicates just enough of the builtin Frame object to enable serialization and traceback rendering.

    Args:

        get_locals (callable): A function that take a frame argument and returns a dict.

            See :class:`Traceback` class for example.
    """

    def __init__(self, frame, *, get_locals=None):
        self.f_locals = {} if get_locals is None else get_locals(frame)
        self.f_globals = {k: v for k, v in frame.f_globals.items() if k in ('__file__', '__name__')}
        self.f_code = Code(frame.f_code)
        self.f_lineno = frame.f_lineno

    def clear(self):
        """
        For compatibility with PyPy 3.5;
        clear() was added to frame in Python 3.4
        and is called by traceback.clear_frames(), which
        in turn is called by unittest.TestCase.assertRaises
        """


class Traceback:
    """
    Class that wraps builtin Traceback objects.

    Args:
        get_locals (callable): A function that take a frame argument and returns a dict.

            Ideally you will only return exactly what you need, and only with simple types that can be json serializable.

            Example:

            .. code:: python

                def get_locals(frame):
                    if frame.f_locals.get("__tracebackhide__"):
                        return {"__tracebackhide__": True}
                    else:
                        return {}
    """

    tb_next = None

    def __init__(self, tb, *, get_locals=None):
        self.tb_frame = Frame(tb.tb_frame, get_locals=get_locals)
        self.tb_lineno = int(tb.tb_lineno)

        # Build in place to avoid exceeding the recursion limit
        tb = tb.tb_next
        prev_traceback = self
        cls = type(self)
        while tb is not None:
            traceback = object.__new__(cls)
            traceback.tb_frame = Frame(tb.tb_frame, get_locals=get_locals)
            traceback.tb_lineno = int(tb.tb_lineno)
            prev_traceback.tb_next = traceback
            prev_traceback = traceback
            tb = tb.tb_next

    def as_traceback(self):
        """
        Convert to a builtin Traceback object that is usable for raising or rendering a stacktrace.
        """
        current = self
        top_tb = None
        tb = None
        while current:
            f_code = current.tb_frame.f_code
            code = compile('\n' * (current.tb_lineno - 1) + 'raise __traceback_maker', current.tb_frame.f_code.co_filename, 'exec')
            if hasattr(code, 'replace'):
                # Python 3.8 and newer
                code = code.replace(co_argcount=0, co_filename=f_code.co_filename, co_name=f_code.co_name, co_freevars=(), co_cellvars=())
            else:
                code = CodeType(
                    0,
                    code.co_kwonlyargcount,
                    code.co_nlocals,
                    code.co_stacksize,
                    code.co_flags,
                    code.co_code,
                    code.co_consts,
                    code.co_names,
                    code.co_varnames,
                    f_code.co_filename,
                    f_code.co_name,
                    code.co_firstlineno,
                    code.co_lnotab,
                    (),
                    (),
                )

            # noinspection PyBroadException
            try:
                exec(code, dict(current.tb_frame.f_globals), dict(current.tb_frame.f_locals))  # noqa: S102
            except Exception:
                next_tb = sys.exc_info()[2].tb_next
                if top_tb is None:
                    top_tb = next_tb
                if tb is not None:
                    tb.tb_next = next_tb
                tb = next_tb
                del next_tb

            current = current.tb_next
        try:
            return top_tb
        finally:
            del top_tb
            del tb

    to_traceback = as_traceback

    def as_dict(self):
        """
        Converts to a dictionary representation. You can serialize the result to JSON as it only has
        builtin objects like dicts, lists, ints or strings.
        """
        if self.tb_next is None:
            tb_next = None
        else:
            tb_next = self.tb_next.as_dict()

        code = {
            'co_filename': self.tb_frame.f_code.co_filename,
            'co_name': self.tb_frame.f_code.co_name,
        }
        frame = {
            'f_globals': self.tb_frame.f_globals,
            'f_locals': self.tb_frame.f_locals,
            'f_code': code,
            'f_lineno': self.tb_frame.f_lineno,
        }
        return {
            'tb_frame': frame,
            'tb_lineno': self.tb_lineno,
            'tb_next': tb_next,
        }

    to_dict = as_dict

    @classmethod
    def from_dict(cls, dct):
        """
        Creates an instance from a dictionary with the same structure as ``.as_dict()`` returns.
        """
        if dct['tb_next']:
            tb_next = cls.from_dict(dct['tb_next'])
        else:
            tb_next = None

        code = _AttrDict(
            co_filename=dct['tb_frame']['f_code']['co_filename'],
            co_name=dct['tb_frame']['f_code']['co_name'],
        )
        frame = _AttrDict(
            f_globals=dct['tb_frame']['f_globals'],
            f_locals=dct['tb_frame'].get('f_locals', {}),
            f_code=code,
            f_lineno=dct['tb_frame']['f_lineno'],
        )
        tb = _AttrDict(
            tb_frame=frame,
            tb_lineno=dct['tb_lineno'],
            tb_next=tb_next,
        )
        return cls(tb, get_locals=get_all_locals)

    @classmethod
    def from_string(cls, string, strict=True):
        """
        Creates an instance by parsing a stacktrace. Strict means that parsing stops when lines are not indented by at least two spaces
        anymore.
        """
        frames = []
        header = strict

        for line in string.splitlines():
            line = line.rstrip()
            if header:
                if line == 'Traceback (most recent call last):':
                    header = False
                continue
            frame_match = FRAME_RE.match(line)
            if frame_match:
                frames.append(frame_match.groupdict())
            elif line.startswith('  '):
                pass
            elif strict:
                break  # traceback ended

        if frames:
            previous = None
            for frame in reversed(frames):
                previous = _AttrDict(
                    frame,
                    tb_frame=_AttrDict(
                        frame,
                        f_globals=_AttrDict(
                            __file__=frame['co_filename'],
                            __name__='?',
                        ),
                        f_locals={},
                        f_code=_AttrDict(frame),
                        f_lineno=int(frame['tb_lineno']),
                    ),
                    tb_next=previous,
                )
            return cls(previous)
        else:
            raise TracebackParseError('Could not find any frames in %r.' % string)


def get_all_locals(frame):
    return dict(frame.f_locals)
