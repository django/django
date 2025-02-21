from django.conf import settings
from django.utils.translation import get_supported_language_variant
from django.utils.translation.trans_real import language_code_re

from . import Error, Tags, register

E001 = Error(
    "You have provided an invalid value for the LANGUAGE_CODE setting: {!r}.",
    id="translation.E001",
)

E002 = Error(
    "You have provided an invalid language code in the LANGUAGES setting: {!r}.",
    id="translation.E002",
)

E003 = Error(
    "You have provided an invalid language code in the LANGUAGES_BIDI setting: {!r}.",
    id="translation.E003",
)

E004 = Error(
    "You have provided a value for the LANGUAGE_CODE setting that is not in "
    "the LANGUAGES setting.",
    id="translation.E004",
)


@register(Tags.translation)
def check_setting_language_code(app_configs, **kwargs):
    """Error if LANGUAGE_CODE setting is invalid."""
    tag = settings.LANGUAGE_CODE
    if not isinstance(tag, str) or not language_code_re.match(tag):
        return [Error(E001.msg.format(tag), id=E001.id)]
    return []


@register(Tags.translation)
def check_setting_languages(app_configs, **kwargs):
    """Error if LANGUAGES setting is invalid."""
    return [
        Error(E002.msg.format(tag), id=E002.id)
        for tag, _ in settings.LANGUAGES
        if not isinstance(tag, str) or not language_code_re.match(tag)
    ]


@register(Tags.translation)
def check_setting_languages_bidi(app_configs, **kwargs):
    """Error if LANGUAGES_BIDI setting is invalid."""
    return [
        Error(E003.msg.format(tag), id=E003.id)
        for tag in settings.LANGUAGES_BIDI
        if not isinstance(tag, str) or not language_code_re.match(tag)
    ]


@register(Tags.translation)
def check_language_settings_consistent(app_configs, **kwargs):
    """Error if language settings are not consistent with each other."""
    try:
        get_supported_language_variant(settings.LANGUAGE_CODE)
    except LookupError:
        return [E004]
    else:
        return []
