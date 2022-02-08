import inspect

from django.conf import settings

from .. import Error, Tags, Warning, register

W003 = Warning(
    "You don't appear to be using Django's built-in "
    "cross-site request forgery protection via the middleware "
    "('django.middleware.csrf.CsrfViewMiddleware' is not in your "
    "MIDDLEWARE). Enabling the middleware is the safest approach "
    "to ensure you don't leave any holes.",
    id="security.W003",
)

W016 = Warning(
    "You have 'django.middleware.csrf.CsrfViewMiddleware' in your "
    "MIDDLEWARE, but you have not set CSRF_COOKIE_SECURE to True. "
    "Using a secure-only CSRF cookie makes it more difficult for network "
    "traffic sniffers to steal the CSRF token.",
    id="security.W016",
)


def _csrf_middleware():
    return "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


@register(Tags.security, deploy=True)
def check_csrf_middleware(app_configs, **kwargs):
    passed_check = _csrf_middleware()
    return [] if passed_check else [W003]


@register(Tags.security, deploy=True)
def check_csrf_cookie_secure(app_configs, **kwargs):
    passed_check = (
        settings.CSRF_USE_SESSIONS
        or not _csrf_middleware()
        or settings.CSRF_COOKIE_SECURE
    )
    return [] if passed_check else [W016]


@register(Tags.security)
def check_csrf_failure_view(app_configs, **kwargs):
    from django.middleware.csrf import _get_failure_view

    errors = []
    try:
        view = _get_failure_view()
    except ImportError:
        msg = (
            "The CSRF failure view '%s' could not be imported."
            % settings.CSRF_FAILURE_VIEW
        )
        errors.append(Error(msg, id="security.E102"))
    else:
        try:
            inspect.signature(view).bind(None, reason=None)
        except TypeError:
            msg = (
                "The CSRF failure view '%s' does not take the correct number of arguments."
                % settings.CSRF_FAILURE_VIEW
            )
            errors.append(Error(msg, id="security.E101"))
    return errors
