import re

from django.conf import settings
from django.utils.translation.trans_real import language_code_re

from . import Error, Tags, register


@register(Tags.translation)
def check_setting_language_code(app_configs, **kwargs):
    """
    Errors if language code is in the wrong format. Language codes specification outlined by
    https://en.wikipedia.org/wiki/IETF_language_tag#Syntax_of_language_tags
    """
    match_result = re.match(language_code_re, settings.LANGUAGE_CODE)
    errors = []
    if not match_result:
        errors.append(Error(
            "LANGUAGE_CODE in settings.py is {}. It should be in the form ll or ll-cc where ll is the language and cc "
            "is the country. Examples include: it, de-at, es, pt-br. The full set of language codes specifications is "
            "outlined by https://en.wikipedia.org/wiki/IETF_language_tag#Syntax_of_language_tags".format(
                settings.LANGUAGE_CODE),
            id="translation.E001",
        ))
    return errors
