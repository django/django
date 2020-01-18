import re
import warnings

from django.conf import settings
from django.utils.translation.trans_real import (
    activate, deactivate, get_language, get_supported_language_variant,
    language_code_re, reset_translations_cache,
)

from . import Error, Tags, Warning, register

E001 = Error(
    'You have provided an invalid value for the LANGUAGE_CODE setting: {!r}.',
    id='translation.E001',
)

E002 = Error(
    'You have provided an invalid language code in the LANGUAGES setting: {!r}.',
    id='translation.E002',
)

E003 = Error(
    'You have provided an invalid language code in the LANGUAGES_BIDI setting: {!r}.',
    id='translation.E003',
)

E004 = Error(
    'You have provided a value for the LANGUAGE_CODE setting that is not in '
    'the LANGUAGES setting.',
    id='translation.E004',
)

W005 = Warning(
    'Inconsistent plural forms across catalogs for language {!r}.',
    id='translation.W005',
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
        for tag, _ in settings.LANGUAGES if not isinstance(tag, str) or not language_code_re.match(tag)
    ]


@register(Tags.translation)
def check_setting_languages_bidi(app_configs, **kwargs):
    """Error if LANGUAGES_BIDI setting is invalid."""
    return [
        Error(E003.msg.format(tag), id=E003.id)
        for tag in settings.LANGUAGES_BIDI if not isinstance(tag, str) or not language_code_re.match(tag)
    ]


@register(Tags.translation)
def check_language_settings_consistent(app_configs, **kwargs):
    """Error if language settings are not consistent with each other."""
    try:
        get_supported_language_variant(settings.LANGUAGE_CODE)
    except LookupError:
        return [E004]
    return []


@register(Tags.translation)
def check_plural_forms_consistency(app_configs, **kwargs):
    """
    Warns if plural forms are not consistent for languages in the LANGUAGES setting.
    """
    if settings.USE_I18N and settings.PLURAL_FORMS_CONSISTENCY:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            saved_locale = get_language()
            try:
                warns = []
                deactivate()
                reset_translations_cache()
                if settings.LANGUAGES:
                    for lang, _ in settings.LANGUAGES:
                        activate(lang)
                else:
                    activate(settings.LANGUAGE_CODE)
                if len(ws) > 0:
                    for warn in ws:
                        m = re.search(r'(?<=Locale: )(.*)(?=\n)', str(warn.message))
                        if m:
                            tag = m.group(0)
                            warns.append(Warning(W005.msg.format(tag), id=W005.id))
                    return warns
            finally:
                reset_translations_cache()
                if saved_locale:
                    activate(saved_locale)
    return []
