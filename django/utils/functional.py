def curry(*args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return args[0](*(args[1:]+moreargs), **dict(kwargs.items() + morekwargs.items()))
    return _curried

def lazy(func, *resultclasses):
    """
    Turns any callable into a lazy evaluated callable. You need to give result
    classes or types -- at least one is needed so that the automatic forcing of
    the lazy evaluation code is triggered. Results are not memoized; the
    function is evaluated on every access.
    """
    class __proxy__:
        # This inner class encapsulates the code that should be evaluated
        # lazily. On calling of one of the magic methods it will force
        # the evaluation and store the result. Afterwards, the result
        # is delivered directly. So the result is memoized.
        def __init__(self, args, kw):
           self.__func = func
           self.__args = args
           self.__kw = kw
           self.__dispatch = {}
           for resultclass in resultclasses:
               self.__dispatch[resultclass] = {}
               for (k, v) in resultclass.__dict__.items():
                   setattr(self, k, self.__promise__(resultclass, k, v))

        def __promise__(self, klass, funcname, func):
            # Builds a wrapper around some magic method and registers that magic
            # method for the given type and method name.
            def __wrapper__(*args, **kw):
                # Automatically triggers the evaluation of a lazy value and
                # applies the given magic method of the result type.
                res = self.__func(*self.__args, **self.__kw)
                return self.__dispatch[type(res)][funcname](res, *args, **kw)

            if not self.__dispatch.has_key(klass):
                self.__dispatch[klass] = {}
            self.__dispatch[klass][funcname] = func
            return __wrapper__

    def __wrapper__(*args, **kw):
        # Creates the proxy object, instead of the actual value.
        return __proxy__(args, kw)

    return __wrapper__
