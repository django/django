from django.conf import settings

from .utils import boolean_check


@boolean_check("CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED")
def check_csrf_middleware():
    return ("django.middleware.csrf.CsrfViewMiddleware"
            in settings.MIDDLEWARE_CLASSES)

check_csrf_middleware.messages = {
    "CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED": (
        "You don't appear to be using Django's built-in "
        "cross-site request forgery protection via the middleware "
        "('django.middleware.csrf.CsrfViewMiddleware' "
        "is not in your MIDDLEWARE_CLASSES). "
        "Enabling the middleware is the safest approach to ensure you "
        "don't leave any holes; see "
        "https://docs.djangoproject.com/en/dev/ref/contrib/csrf/."
        )
    }
