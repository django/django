def curry(*args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return args[0](*(args[1:]+moreargs), **dict(kwargs.items() + morekwargs.items()))
    return _curried

def lazy(func, *resultclasses):

    """
    lazy turns any callable passed in into a lazy evaluated callable.
    you need to give result classes or types - at least one is needed
    so that the automatic forcing of the lazy evaluation code is
    triggered. Results are not memoized - the function is evaluated
    on every access.
    """

    class __proxy__:
    
        """
        This inner class encapsulates the code that should be evaluated
        lazyly. On calling of one of the magic methods it will force
        the evaluation and store the result - afterwards the result
        is delivered directly. So the result is memoized.
        """

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
        
            """
            This function builds a wrapper around some magic method and
            registers that magic method for the given type and methodname.
            """
    
            def __wrapper__(*args, **kw):
                """
                This wrapper function automatically triggers the evaluation of
                a lazy value. It then applies the given magic method of the
                result type.
                """
                res = self.__func(*self.__args, **self.__kw)
                return self.__dispatch[type(res)][funcname](res, *args, **kw)
  
            if not self.__dispatch.has_key(klass):
                self.__dispatch[klass] = {}
            self.__dispatch[klass][funcname] = func
            return __wrapper__
  
    def __wrapper__(*args, **kw):
        """
        This wrapper function just creates the proxy object that is returned
        instead of the actual value.
        """
        return __proxy__(args, kw)

    return __wrapper__


