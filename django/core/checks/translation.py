from django.conf import settings
from django.utils.translation.trans_real import language_code_re

from . import Error, Tags, register

E001 = Error(
    'You have provided an invalid value for the LANGUAGE_CODE setting.',
    id='translation.E001',
)


@register(Tags.translation)
def check_setting_language_code(app_configs, **kwargs):
    """
    Errors if language code setting is invalid.
    """
    if not language_code_re.match(settings.LANGUAGE_CODE):
        return [E001]
    return []
