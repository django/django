from django.conf import settings

from .. import Error, Tags, register


@register(Tags.compatibility)
def check_csrf_trusted_origins(app_configs, **kwargs):
    return [
        Error(
            f"As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme (usually http:// or https://) but found {origin}. See the release notes for details.",
            id="4_0.E001",
        )
        for origin in settings.CSRF_TRUSTED_ORIGINS
        if "://" not in origin
    ]
