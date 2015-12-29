from __future__ import unicode_literals

from . import Tags, Warning, register


@register(Tags.urls)
def check_url_config(app_configs, **kwargs):
    from django.urls import get_resolver
    resolver = get_resolver()
    return check_resolver(resolver)


def check_resolver(resolver):
    """
    Recursively check the resolver.
    """
    from django.urls import Resolver, ResolverEndpoint

    warnings = []
    # We only check when we're using a built-in resolver
    if isinstance(resolver, Resolver):
        for sub_resolver in resolver.resolvers:
            if isinstance(sub_resolver, Resolver):
                warnings.extend(check_include_trailing_dollar(sub_resolver))
                # Check resolver recursively
                warnings.extend(check_resolver(sub_resolver))
            elif isinstance(sub_resolver, ResolverEndpoint):
                warnings.extend(check_pattern_name(sub_resolver))

            warnings.extend(check_pattern_startswith_slash(sub_resolver))

    return warnings


def describe_pattern(pattern):
    """
    Format the URL pattern for display in warning messages.
    """
    description = "'%s'" % pattern.describe()
    if getattr(pattern, 'url_name', False):
        description += " [name='{}']".format(pattern.url_name)
    return description


def check_include_trailing_dollar(pattern):
    """
    Check that include is not used with a regex ending with a dollar.
    """
    from django.urls import RegexPattern
    warnings = []
    for constraint in pattern.constraints:
        if isinstance(constraint, RegexPattern):
            regex_pattern = constraint.regex.pattern
            if regex_pattern.endswith('$') and not regex_pattern.endswith('\$'):
                warning = Warning(
                    "Your URL pattern {} uses include with a regex ending with a '$'. "
                    "Remove the dollar from the regex to avoid problems including "
                    "URLs.".format(describe_pattern(pattern)),
                    id="urls.W001",
                )
                warnings.append(warning)
    return warnings


def check_pattern_startswith_slash(pattern):
    """
    Check that the pattern does not begin with a forward slash.
    """
    from django.urls import RegexPattern
    warnings = []
    for constraint in pattern.constraints:
        if isinstance(constraint, RegexPattern):
            regex_pattern = constraint.regex.pattern
            if regex_pattern.startswith('/') or regex_pattern.startswith('^/'):
                warning = Warning(
                    "Your URL pattern {} has a regex beginning with a '/'. "
                    "Remove this slash as it is unnecessary.".format(describe_pattern(pattern)),
                    id="urls.W002",
                )
                warnings.append(warning)
    return warnings


def check_pattern_name(pattern):
    """
    Check that the pattern name does not contain a colon.
    """
    if pattern.url_name is not None and ":" in pattern.url_name:
        warning = Warning(
            "Your URL pattern {} has a name including a ':'. Remove the colon, to "
            "avoid ambiguous namespace references.".format(describe_pattern(pattern)),
            id="urls.W003",
        )
        return [warning]
    else:
        return []
