from django.middleware.security import construct_csp_header
from django.utils.decorators import decorator_from_middleware, available_attrs
from functools import wraps


def csp_exempt(view_func):
    """
    Marks the response of a view as being exempt from the Content Security Policy
    part of the SecurityMiddleware.
    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        resp.csp_exempt = True
        return resp
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)


def csp_header(policy, report_only=False):
    """
    Set custom Content Security Policy header for view.
    """
    csp = construct_csp_header(policy, report_only)
    def _set_csp_header(viewfunc):
        @wraps(viewfunc, assigned=available_attrs(viewfunc))
        def _csp_header_set(request, *args, **kw):
            response = viewfunc(request, *args, **kw)
            if not csp['name'] in response:
                response[csp['name']] = csp['value']
            return response
        return _csp_header_set
    return _set_csp_header
