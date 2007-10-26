def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args+moreargs), **dict(kwargs, **morekwargs))
    return _curried

def memoize(func, cache, num_args):
    """
    Wrap a function so that results for any argument tuple are stored in
    'cache'. Note that the args to the function must be usable as dictionary
    keys.

    Only the first num_args are considered when creating the key.
    """
    def wrapper(*args):
        mem_args = args[:num_args]
        if mem_args in cache:
            return cache[mem_args]
        result = func(*args)
        cache[mem_args] = result
        return result
    return wrapper

class Promise(object):
    """
    This is just a base class for the proxy class created in
    the closure of the lazy function. It can be used to recognize
    promises in code.
    """
    pass

def lazy(func, *resultclasses):
    """
    Turns any callable into a lazy evaluated callable. You need to give result
    classes or types -- at least one is needed so that the automatic forcing of
    the lazy evaluation code is triggered. Results are not memoized; the
    function is evaluated on every access.
    """
    class __proxy__(Promise):
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
            self._delegate_str = str in resultclasses
            self._delegate_unicode = unicode in resultclasses
            assert not (self._delegate_str and self._delegate_unicode), "Cannot call lazy() with both str and unicode return types."
            if self._delegate_unicode:
                # Each call to lazy() makes a new __proxy__ object, so this
                # doesn't interfere with any other lazy() results.
                __proxy__.__unicode__ = __proxy__.__unicode_cast
            elif self._delegate_str:
                __proxy__.__str__ = __proxy__.__str_cast

        def __promise__(self, klass, funcname, func):
            # Builds a wrapper around some magic method and registers that magic
            # method for the given type and method name.
            def __wrapper__(*args, **kw):
                # Automatically triggers the evaluation of a lazy value and
                # applies the given magic method of the result type.
                res = self.__func(*self.__args, **self.__kw)
                return self.__dispatch[type(res)][funcname](res, *args, **kw)

            if klass not in self.__dispatch:
                self.__dispatch[klass] = {}
            self.__dispatch[klass][funcname] = func
            return __wrapper__

        def __unicode_cast(self):
            return self.__func(*self.__args, **self.__kw)

        def __str_cast(self):
            return str(self.__func(*self.__args, **self.__kw))

        def __cmp__(self, rhs):
            if self._delegate_str:
                s = str(self.__func(*self.__args, **self.__kw))
            elif self._delegate_unicode:
                s = unicode(self.__func(*self.__args, **self.__kw))
            else:
                s = self.__func(*self.__args, **self.__kw)
            if isinstance(rhs, Promise):
                return -cmp(rhs, s)
            else:
                return cmp(s, rhs)

        def __mod__(self, rhs):
            if self._delegate_str:
                return str(self) % rhs
            elif self._delegate_unicode:
                return unicode(self) % rhs
            else:
                raise AssertionError('__mod__ not supported for non-string types')

        def __deepcopy__(self, memo):
            # Instances of this class are effectively immutable. It's just a
            # collection of functions. So we don't need to do anything
            # complicated for copying.
            memo[id(self)] = self
            return self

    def __wrapper__(*args, **kw):
        # Creates the proxy object, instead of the actual value.
        return __proxy__(args, kw)

    return __wrapper__

def allow_lazy(func, *resultclasses):
    """
    A decorator that allows a function to be called with one or more lazy
    arguments. If none of the args are lazy, the function is evaluated
    immediately, otherwise a __proxy__ is returned that will evaluate the
    function when needed.
    """
    def wrapper(*args, **kwargs):
        for arg in list(args) + kwargs.values():
            if isinstance(arg, Promise):
                break
        else:
            return func(*args, **kwargs)
        return lazy(func, *resultclasses)(*args, **kwargs)
    return wrapper
