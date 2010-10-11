import signal
import weakref

from django.utils.unittest.compatibility import wraps

__unittest = True


class _InterruptHandler(object):
    def __init__(self, default_handler):
        self.called = False
        self.default_handler = default_handler

    def __call__(self, signum, frame):
        installed_handler = signal.getsignal(signal.SIGINT)
        if installed_handler is not self:
            # if we aren't the installed handler, then delegate immediately
            # to the default handler
            self.default_handler(signum, frame)

        if self.called:
            self.default_handler(signum, frame)
        self.called = True
        for result in _results.keys():
            result.stop()

_results = weakref.WeakKeyDictionary()
def registerResult(result):
    _results[result] = 1

def removeResult(result):
    return bool(_results.pop(result, None))

_interrupt_handler = None
def installHandler():
    global _interrupt_handler
    if _interrupt_handler is None:
        default_handler = signal.getsignal(signal.SIGINT)
        _interrupt_handler = _InterruptHandler(default_handler)
        signal.signal(signal.SIGINT, _interrupt_handler)


def removeHandler(method=None):
    if method is not None:
        @wraps(method)
        def inner(*args, **kwargs):
            initial = signal.getsignal(signal.SIGINT)
            removeHandler()
            try:
                return method(*args, **kwargs)
            finally:
                signal.signal(signal.SIGINT, initial)
        return inner

    global _interrupt_handler
    if _interrupt_handler is not None:
        signal.signal(signal.SIGINT, _interrupt_handler.default_handler)
