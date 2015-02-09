from __future__ import unicode_literals

from .. import Tags, Warning, register


@register(Tags.compatibility)
def check_1_7_compatibility(**kwargs):
    errors = []
    errors.extend(_check_middleware_classes(**kwargs))
    return errors


def _check_middleware_classes(app_configs=None, **kwargs):
    """
    Checks if the user has *not* overridden the ``MIDDLEWARE_CLASSES`` setting &
    warns them about the global default changes.
    """
    from django.conf import settings

    # MIDDLEWARE_CLASSES is overridden by default by startproject. If users
    # have removed this override then we'll warn them about the default changes.
    if not settings.is_overridden('MIDDLEWARE_CLASSES'):
        return [
            Warning(
                "MIDDLEWARE_CLASSES is not set.",
                hint=("Django 1.7 changed the global defaults for the MIDDLEWARE_CLASSES. "
                      "django.contrib.sessions.middleware.SessionMiddleware, "
                      "django.contrib.auth.middleware.AuthenticationMiddleware, and "
                      "django.contrib.messages.middleware.MessageMiddleware were removed from the defaults. "
                      "If your project needs these middleware then you should configure this setting."),
                obj=None,
                id='1_7.W001',
            )
        ]
    else:
        return []
