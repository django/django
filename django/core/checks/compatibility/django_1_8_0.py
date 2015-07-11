from __future__ import unicode_literals

from django.conf import global_settings, settings

from .. import Tags, Warning, register


@register(Tags.compatibility)
def check_duplicate_template_settings(app_configs, **kwargs):
    if settings.TEMPLATES:
        values = [
            'TEMPLATE_DIRS',
            'ALLOWED_INCLUDE_ROOTS',
            'TEMPLATE_CONTEXT_PROCESSORS',
            'TEMPLATE_DEBUG',
            'TEMPLATE_LOADERS',
            'TEMPLATE_STRING_IF_INVALID',
        ]
        duplicates = [
            value for value in values
            if getattr(settings, value) != getattr(global_settings, value)
        ]
        if duplicates:
            return [Warning(
                "The standalone TEMPLATE_* settings were deprecated in Django "
                "1.8 and the TEMPLATES dictionary takes precedence. You must "
                "put the values of the following settings into your default "
                "TEMPLATES dict: %s." % ", ".join(duplicates),
                id='1_8.W001',
            )]
    return []
