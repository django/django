def curry(*args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return args[0](*(args[1:]+moreargs), **dict(kwargs.items() + morekwargs.items()))
    return _curried
