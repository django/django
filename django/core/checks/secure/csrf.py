from django.conf import settings
from django.core import checks


def check_csrf_middleware(app_configs):
    passed_check = "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE_CLASSES
    return [] if passed_check else [checks.Warning(
        "You don't appear to be using Django's built-in "
        "cross-site request forgery protection via the middleware "
        "('django.middleware.csrf.CsrfViewMiddleware' is not in your "
        "MIDDLEWARE_CLASSES). Enabling the middleware is the safest approach "
        "to ensure you don't leave any holes.",
        hint=None,
        id='secure.W003',
    )]
