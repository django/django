from django.conf import settings

from .. import Tags, Warning, register
from ..utils import patch_middleware_message

W003 = Warning(
    "You don't appear to be using Django's built-in "
    "cross-site request forgery protection via the middleware "
    "('django.middleware.csrf.CsrfViewMiddleware' is not in your "
    "MIDDLEWARE). Enabling the middleware is the safest approach "
    "to ensure you don't leave any holes.",
    id='security.W003',
)

W016 = Warning(
    "You have 'django.middleware.csrf.CsrfViewMiddleware' in your "
    "MIDDLEWARE, but you have not set CSRF_COOKIE_SECURE to True. "
    "Using a secure-only CSRF cookie makes it more difficult for network "
    "traffic sniffers to steal the CSRF token.",
    id='security.W016',
)

W017 = Warning(
    "You have 'django.middleware.csrf.CsrfViewMiddleware' in your "
    "MIDDLEWARE, but you have not set CSRF_COOKIE_HTTPONLY to True. "
    "Using an HttpOnly CSRF cookie makes it more difficult for cross-site "
    "scripting attacks to steal the CSRF token.",
    id='security.W017',
)


def _csrf_middleware():
    return ("django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE_CLASSES or
            settings.MIDDLEWARE and "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE)


@register(Tags.security, deploy=True)
def check_csrf_middleware(app_configs, **kwargs):
    passed_check = _csrf_middleware()
    return [] if passed_check else [patch_middleware_message(W003)]


@register(Tags.security, deploy=True)
def check_csrf_cookie_secure(app_configs, **kwargs):
    passed_check = (
        not _csrf_middleware() or
        settings.CSRF_COOKIE_SECURE
    )
    return [] if passed_check else [patch_middleware_message(W016)]


@register(Tags.security, deploy=True)
def check_csrf_cookie_httponly(app_configs, **kwargs):
    passed_check = (
        not _csrf_middleware() or
        settings.CSRF_COOKIE_HTTPONLY
    )
    return [] if passed_check else [patch_middleware_message(W017)]
