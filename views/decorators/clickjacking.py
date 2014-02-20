from functools import wraps

from django.utils.decorators import available_attrs


def xframe_options_deny(view_func):
    """
    Modifies a view function so its response has the X-Frame-Options HTTP
    header set to 'DENY' as long as the response doesn't already have that
    header set.

    e.g.

    @xframe_options_deny
    def some_view(request):
        ...

    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        if resp.get('X-Frame-Options', None) is None:
            resp['X-Frame-Options'] = 'DENY'
        return resp
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)


def xframe_options_sameorigin(view_func):
    """
    Modifies a view function so its response has the X-Frame-Options HTTP
    header set to 'SAMEORIGIN' as long as the response doesn't already have
    that header set.

    e.g.

    @xframe_options_sameorigin
    def some_view(request):
        ...

    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        if resp.get('X-Frame-Options', None) is None:
            resp['X-Frame-Options'] = 'SAMEORIGIN'
        return resp
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)


def xframe_options_exempt(view_func):
    """
    Modifies a view function by setting a response variable that instructs
    XFrameOptionsMiddleware to NOT set the X-Frame-Options HTTP header.

    e.g.

    @xframe_options_exempt
    def some_view(request):
        ...

    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        resp.xframe_options_exempt = True
        return resp
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)
