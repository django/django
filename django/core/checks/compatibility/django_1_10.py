from __future__ import unicode_literals

from django.conf import global_settings, settings

from .. import Tags, Warning, register


@register(Tags.compatibility)
def check_duplicate_middleware_settings(app_configs, **kwargs):
    if settings.MIDDLEWARE is not None and settings.MIDDLEWARE_CLASSES != global_settings.MIDDLEWARE_CLASSES:
        return [Warning(
            "The MIDDLEWARE_CLASSES setting is deprecated in Django 1.10 "
            "and the MIDDLEWARE setting takes precedence. Since you've set "
            "MIDDLEWARE, the value of MIDDLEWARE_CLASSES is ignored.",
            id='1_10.W001',
        )]
    return []
