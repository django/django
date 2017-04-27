import inspect


def get_func_args(func):
    sig = inspect.signature(func)
    return [
        arg_name for arg_name, param in sig.parameters.items()
        if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]


def get_func_full_args(func):
    """
    Return a list of (argument name, default value) tuples. If the argument
    does not have a default value, omit it in the tuple. Arguments such as
    *args and **kwargs are also included.
    """
    sig = inspect.signature(func)
    args = []
    for arg_name, param in sig.parameters.items():
        name = arg_name
        # Ignore 'self'
        if name == 'self':
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            name = '*' + name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            name = '**' + name
        if param.default != inspect.Parameter.empty:
            args.append((name, param.default))
        else:
            args.append((name,))
    return args


def func_accepts_kwargs(func):
    return any(
        p for p in inspect.signature(func).parameters.values()
        if p.kind == p.VAR_KEYWORD
    )


def func_accepts_var_args(func):
    """
    Return True if function 'func' accepts positional arguments *args.
    """
    return any(
        p for p in inspect.signature(func).parameters.values()
        if p.kind == p.VAR_POSITIONAL
    )


def func_has_no_args(func):
    args = [
        p for p in inspect.signature(func).parameters.values()
        if p.kind == p.POSITIONAL_OR_KEYWORD
    ]
    return len(args) == 1


def func_supports_parameter(func, parameter):
    return parameter in inspect.signature(func).parameters
