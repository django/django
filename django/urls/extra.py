from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.urls.resolvers import URLPattern
from django.shortcuts import resolve_url
from django.urls import path
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt


# Group checking functions section

def user_passes_group_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME, group=None):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user, group=group):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)
        return _wrapped_view
    return decorator


def is_member(user, group):
    if isinstance(group, str):
        group = (group,)
    return user.groups.filter(name__in=group).exists()


# Handy path functions section

def login_required_path(route, view, name=None, kwargs=None):
    return path(route, login_required(view), name, kwargs)


def csrf_exempt_path(route, view, name=None, kwargs=None):
    return path(route, csrf_exempt(view), name, kwargs)


def login_required_csrf_exempt_path(route, view, name=None, kwargs=None):
    return path(route, csrf_exempt(login_required(view)), name, kwargs)


# Handy (Persmission) path functions section

def has_permission_path(permission, route, view, name=None, kwargs=None):
    return path(route, permission_required(permission)(view), name, kwargs)


def has_permission_login_required_path(permission, route, view, name=None, kwargs=None):
    return path(route, permission_required(permission)(login_required(view)), name, kwargs)


def has_permission_csrf_exempt_path(permission, route, view, name=None, kwargs=None):
    return path(route, csrf_exempt(permission_required(permission)(view)), name, kwargs)


def has_permission_login_required_csrf_exempt_path(permission, route, view, name=None, kwargs=None):
    return path(route, csrf_exempt(permission_required(permission)(login_required(view))), name, kwargs)


# Handy (Group) path functions section

def has_group_path(group, route, view, name=None, kwargs=None):
    return path(route, user_passes_group_test(is_member, group=group)(view), name, kwargs)


def has_group_login_required_path(group, route, view, name=None, kwargs=None):
    return path(route, user_passes_group_test(is_member, group=group)(login_required(view)), name, kwargs)


def has_group_csrf_exempt_path(group, route, view, name=None, kwargs=None):
    return path(route, user_passes_group_test(is_member, group=group)(csrf_exempt(view)), name, kwargs)


def has_group_login_required_csrf_exempt_path(group, route, view, name=None, kwargs=None):
    return path(route, user_passes_group_test(is_member, group=group)(csrf_exempt(login_required(view))), name, kwargs)


# Control/Ultimate path function section

def controll_path(route, view, name=None,
                  is_login_required=False, is_csrf_exempt=False, permission=None, group=None
                  , kwargs=None):
    # login_required
    if is_login_required:
        view = login_required(view)
    # csrf_exempt
    if is_csrf_exempt:
        view = csrf_exempt(view)
    # permission
    if permission:
        view = permission_required(permission)(view)
    # group
    if group:
        view = user_passes_group_test(is_member, group=group)(view)
    return path(route, view, name, kwargs)


# (Control/Ultimate) group-path function section

def group_path(urlpatterns, prefix_route='', paths=[], name='', is_login_required=False, is_csrf_exempt=False, permission=None, group=None): # ALL
    def make(path, prefix_route='', name=''):
        name = f"{name}:{path.name}" if name else path.name
        
        route = str(
                prefix_route +
                str(
                    '/' if (not prefix_route.endswith('/') and not path.pattern._route.startswith('/')) else ''
                )
                + path.pattern._route
            )
        route = route.strip('//')
        route = route.strip('/')
        route = route.replace('//', '/') + '/'
        
        path.name = name
        path.pattern._route = route
        
        # login_required
        if is_login_required:
            path.callback = login_required(path.callback)
        # csrf_exempt
        if is_csrf_exempt:
            path.callback = csrf_exempt(path.callback)
        # permission
        if permission:
            path.callback = permission_required(permission)(path.callback)
        # group
        if group:
            path.callback = user_passes_group_test(is_member, group=group)(path.callback)
        
        return path
    
    for path in paths:
        inner_paths = path.default_args.get('paths', [])
        if type(path) == URLPattern:
            urlpatterns.append(
                make(path, prefix_route, name)
            )
        if inner_paths != []:
            del path.default_args['paths'] # For Error: got an unexpected keyword.
            name = path.name
            prefix_route = path.pattern._route
            group_path(urlpatterns=urlpatterns, prefix_route=prefix_route, paths=inner_paths, name=name)
