import copy
from collections import defaultdict
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.template.backends.django import get_package_libraries

from . import Error, Tags, register

E001 = Error(
    "You have 'APP_DIRS': True in your TEMPLATES but also specify 'loaders' "
    "in OPTIONS. Either remove APP_DIRS or remove the 'loaders' option.",
    id='templates.E001',
)
E002 = Error(
    "'string_if_invalid' in TEMPLATES OPTIONS must be a string but got: {} ({}).",
    id="templates.E002",
)
E003 = Error(
    "You have multiple libraries named: '{}'. Rename one of: {}.",
    id="templates.E003",
)


@register(Tags.templates)
def check_setting_app_dirs_loaders(app_configs, **kwargs):
    return [E001] if any(
        conf.get('APP_DIRS') and 'loaders' in conf.get('OPTIONS', {})
        for conf in settings.TEMPLATES
    ) else []


@register(Tags.templates)
def check_string_if_invalid_is_string(app_configs, **kwargs):
    errors = []
    for conf in settings.TEMPLATES:
        string_if_invalid = conf.get('OPTIONS', {}).get('string_if_invalid', '')
        if not isinstance(string_if_invalid, str):
            error = copy.copy(E002)
            error.msg = error.msg.format(string_if_invalid, type(string_if_invalid).__name__)
            errors.append(error)
    return errors


@register(Tags.templates)
def check_for_mulitple_libraries_with_the_same_name(app_configs, **kwargs):
    errors = []

    libraries = defaultdict(list)
    candidates = ['django.templatetags']
    candidates.extend(f'{app.name}.templatetags' for app in apps.get_app_configs())

    for candidate in candidates:
        try:
            pkg = import_module(candidate)
        except ModuleNotFoundError:
            # No templatetags package defined. This is safe to ignore.
            continue

        if hasattr(pkg, '__path__'):
            for name in get_package_libraries(pkg):
                import_name = name[len(candidate) + 1:]
                libraries[import_name].append(name)

    for library_name, items in libraries.items():
        if len(items) > 1:
            error = copy.copy(E003)
            error.msg = error.msg.format(library_name, ', '.join(f"'{item}'" for item in items))
            errors.append(error)

    return errors
