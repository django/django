from __future__ import unicode_literals

from django.conf import settings

from .. import Tags, Warning, register


@register(Tags.compatibility)
def check_duplicate_template_settings(app_configs, **kwargs):
    if settings.TEMPLATES:
        values = [
            'TEMPLATE_DIRS',
            'TEMPLATE_CONTEXT_PROCESSORS',
            'TEMPLATE_DEBUG',
            'TEMPLATE_LOADERS',
            'TEMPLATE_STRING_IF_INVALID',
        ]
        defined = [value for value in values if getattr(settings, value, None)]
        if defined:
            return [Warning(
                "The standalone TEMPLATE_* settings were deprecated in Django "
                "1.8 and the TEMPLATES dictionary takes precedence. You must "
                "put the values of the following settings into your default "
                "TEMPLATES dict: %s." % ", ".join(defined),
                id='1_8.W001',
            )]
    return []
