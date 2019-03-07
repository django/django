from django.conf import settings
from django.utils.translation.trans_real import language_code_re

from . import Error, Tags, register

E001 = Error(
    'You have provided an invalid value for the LANGUAGE_CODE setting: {}.',
    id='translation.E001',
)


@register(Tags.translation)
def check_setting_language_code(app_configs, **kwargs):
    """Error if LANGUAGE_CODE setting is invalid."""
    tag = settings.LANGUAGE_CODE
    if not isinstance(tag, str) or not language_code_re.match(tag):
        return [Error(E001.msg.format(tag), id=E001.id)]
    return []
