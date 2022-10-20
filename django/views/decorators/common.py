from functools import wraps


def no_append_slash(view_func):
    """
    Mark a view function as excluded from CommonMiddleware's APPEND_SLASH
    redirection.
    """
    # view_func.should_append_slash = False would also work, but decorators are
    # nicer if they don't have side effects, so return a new function.
    @wraps(view_func)
    def wrapper_view(*args, **kwargs):
        return view_func(*args, **kwargs)

    wrapper_view.should_append_slash = False
    return wrapper_view
