def curry(*args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return args[0](*(args[1:]+moreargs), **dict(kwargs.items() + morekwargs.items()))
    return _curried

class NoneSoFar:
    """
    NoneSoFar is a singleton that denotes a missing value. This can be
    used instead of None - because None might be a valid return value.
    """
    pass
NoneSoFar = NoneSoFar()

def force(value):
    """
    This function forces evaluation of a promise. It recognizes a promise
    by it's magic __force__ function and just applies it and returns
    the result. If the value isn't a promise, it just returns the value.
    """

    return getattr(value, '__force__', lambda : value)()

def forced(value):
    """
    This function returns true if a value is either not a promise or
    is already forced. This uses the __forced__ magic method.
    """
    return getattr(value, '__forced__', lambda : True)()

def lazy(func, *resultclasses):

    """
    lazy turns any callable passed in into a lazy evaluated callable.
    you need to give result classes or types - at least one is needed
    so that the automatic forcing of the lazy evaluation code is
    triggered.
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
           self.__result = NoneSoFar
           self.__dispatch = {}
           for resultclass in resultclasses:
               self.__dispatch[resultclass] = {}
               for (k, v) in resultclass.__dict__.items():
                   setattr(self, k, self.__promise__(resultclass, k, v))
	
	def __force__(self):
	   """
	   This function forces the evaluation of a promise and
	   returns the value itself.
	   """
           if self.__result is NoneSoFar:
              self.__result = self.__func(*self.__args, **self.__kw)
	   return self.__result
	
	def __forced__(self):
	   """
	   This returns true if the promise is forced and false if not.
	   """
	   if self.__result is NoneSoFar: return False
	   else: return True
  
        def __promise__(self, klass, funcname, func):
        
           """
           This function builds a wrapper around some magic method and
           registers that magic method for the given type and methodname.
           """
    
           def __wrapper__(*args, **kw):
              """
              This wrapper function automatically forces the evaluation of
              a lazy value if the value isn't already forced. It then applies
              the given magic method of the result type.
              """
	      res = self.__force__()
              return self.__dispatch[type(res)][funcname](res, *args, **kw)
  
           if not self.__dispatch.has_key(klass): self.__dispatch[klass] = {}
           self.__dispatch[klass][funcname] = func
           return __wrapper__
  
    def __wrapper__(*args, **kw):
        """
        This wrapper function just creates the proxy object that is returned
        instead of the actual value.
        """
        return __proxy__(args, kw)

    return __wrapper__

if __name__ == '__main__':
    def anton(a,b):
        return a+b

    anton = lazy(anton, int, str)

    print type(anton(5,6))
    print anton(5,6)
    print anton('anton','berta')
    print type(force(anton(5,6)))
    print forced(1)
    print forced(anton(5,6))
    print forced(force(anton(5,6)))

