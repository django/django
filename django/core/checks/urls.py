from __future__ import unicode_literals

from django.conf import settings
from django.utils import six

from . import Error, Tags, Warning, register


@register(Tags.urls)
def check_url_config(app_configs, **kwargs):
    if getattr(settings, 'ROOT_URLCONF', None):
        from django.urls import get_resolver
        resolver = get_resolver()
        return check_resolver(resolver)
    return []


def check_resolver(resolver):
    """
    Recursively check the resolver.
    """
    from django.urls import RegexURLPattern, RegexURLResolver
    warnings = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, RegexURLResolver):
            warnings.extend(check_include_trailing_dollar(pattern))
            # Check resolver recursively
            warnings.extend(check_resolver(pattern))
        elif isinstance(pattern, RegexURLPattern):
            warnings.extend(check_pattern_name(pattern))
        else:
            # This is not a url() instance
            warnings.extend(get_warning_for_invalid_pattern(pattern))

        if not warnings:
            warnings.extend(check_pattern_startswith_slash(pattern))

    return warnings


def get_warning_for_invalid_pattern(pattern):
    """
    Return a list containing a warning that the pattern is invalid.

    describe_pattern() cannot be used here, because we cannot rely on the
    urlpattern having regex or name attributes.
    """
    if isinstance(pattern, six.string_types):
        hint = (
            "Try removing the string '{}'. The list of urlpatterns should not "
            "have a prefix string as the first element.".format(pattern)
        )
    elif isinstance(pattern, tuple):
        hint = "Try using url() instead of a tuple."
    else:
        hint = None

    return [Error(
        "Your URL pattern {!r} is invalid. Ensure that urlpatterns is a list "
        "of url() instances.".format(pattern),
        hint=hint,
        id="urls.E004",
    )]


def describe_pattern(pattern):
    """
    Format the URL pattern for display in warning messages.
    """
    description = "'{}'".format(pattern.regex.pattern)
    if getattr(pattern, 'name', False):
        description += " [name='{}']".format(pattern.name)
    return description


def check_include_trailing_dollar(pattern):
    """
    Check that include is not used with a regex ending with a dollar.
    """
    regex_pattern = pattern.regex.pattern
    if regex_pattern.endswith('$') and not regex_pattern.endswith('\$'):
        warning = Warning(
            "Your URL pattern {} uses include with a regex ending with a '$'. "
            "Remove the dollar from the regex to avoid problems including "
            "URLs.".format(describe_pattern(pattern)),
            id="urls.W001",
        )
        return [warning]
    else:
        return []


def check_pattern_startswith_slash(pattern):
    """
    Check that the pattern does not begin with a forward slash.
    """
    regex_pattern = pattern.regex.pattern
    if not settings.APPEND_SLASH:
        # Skip check as it can be useful to start a URL pattern with a slash
        # when APPEND_SLASH=False.
        return []
    if regex_pattern.startswith('/') or regex_pattern.startswith('^/'):
        warning = Warning(
            "Your URL pattern {} has a regex beginning with a '/'. Remove this "
            "slash as it is unnecessary. If this pattern is targeted in an "
            "include(), ensure the include() pattern has a trailing '/'.".format(
                describe_pattern(pattern)
            ),
            id="urls.W002",
        )
        return [warning]
    else:
        return []


def check_pattern_name(pattern):
    """
    Check that the pattern name does not contain a colon.
    """
    if pattern.name is not None and ":" in pattern.name:
        warning = Warning(
            "Your URL pattern {} has a name including a ':'. Remove the colon, to "
            "avoid ambiguous namespace references.".format(describe_pattern(pattern)),
            id="urls.W003",
        )
        return [warning]
    else:
        return []
