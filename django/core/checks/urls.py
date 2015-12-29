from __future__ import unicode_literals

from importlib import import_module

from . import Tags, Warning, register


@register(Tags.urls)
def check_url_config(app_configs, **kwargs):
    from django.conf import settings
    if getattr(settings, 'ROOT_URLCONF', None):
        urlconf = import_module(settings.ROOT_URLCONF)
        return check_urlconf(urlconf)
    return []


def check_urlconf(urlconf):
    """
    Recursively check the URLconf.
    """
    warnings = []
    for urlpattern in urlconf.urlpatterns:
        if urlpattern.is_endpoint():
            warnings.extend(check_pattern_name(urlpattern))
        else:
            warnings.extend(check_include_trailing_dollar(urlpattern))
            # check URLconf recursively
            warnings.extend(check_urlconf(urlpattern.target))

        warnings.extend(check_pattern_startswith_slash(urlpattern))

    return warnings


def describe_pattern(urlpattern):
    """
    Format the URL pattern for display in warning messages.
    """
    from django.urls import describe_constraints

    description = "'%s'" % describe_constraints(urlpattern.constraints)
    if getattr(urlpattern.target, 'url_name', False):
        description += " [name='{}']".format(urlpattern.target.url_name)
    return description


def check_include_trailing_dollar(urlpattern):
    """
    Check that include is not used with a regex ending with a dollar.
    """
    from django.urls import RegexPattern
    warnings = []
    for constraint in urlpattern.constraints:
        if isinstance(constraint, RegexPattern):
            regex_pattern = constraint.regex.pattern
            if regex_pattern.endswith('$') and not regex_pattern.endswith('\$'):
                warning = Warning(
                    "Your URL pattern {} uses include with a regex ending with a '$'. "
                    "Remove the dollar from the regex to avoid problems including "
                    "URLs.".format(describe_pattern(urlpattern)),
                    id="urls.W001",
                )
                warnings.append(warning)
    return warnings


def check_pattern_startswith_slash(urlpattern):
    """
    Check that the pattern does not begin with a forward slash.
    """
    from django.urls import RegexPattern
    warnings = []
    for constraint in urlpattern.constraints:
        if isinstance(constraint, RegexPattern):
            regex_pattern = constraint.regex.pattern
            if regex_pattern.startswith('/') or regex_pattern.startswith('^/'):
                warning = Warning(
                    "Your URL pattern {} has a regex beginning with a '/'. "
                    "Remove this slash as it is unnecessary.".format(describe_pattern(urlpattern)),
                    id="urls.W002",
                )
                warnings.append(warning)
    return warnings


def check_pattern_name(urlpattern):
    """
    Check that the pattern name does not contain a colon.
    """
    if urlpattern.target.url_name is not None and ":" in urlpattern.target.url_name:
        warning = Warning(
            "Your URL pattern {} has a name including a ':'. Remove the colon, to "
            "avoid ambiguous namespace references.".format(describe_pattern(urlpattern)),
            id="urls.W003",
        )
        return [warning]
    else:
        return []
