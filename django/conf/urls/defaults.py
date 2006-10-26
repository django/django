from django.core.urlresolvers import RegexURLPattern, RegexURLResolver

__all__ = ['handler404', 'handler500', 'include', 'patterns']

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

include = lambda urlconf_module: [urlconf_module]

def patterns(prefix, *tuples):
    pattern_list = []
    for t in tuples:
        regex, view_or_include = t[:2]
        default_kwargs = t[2:]
        if type(view_or_include) == list:
            pattern_list.append(RegexURLResolver(regex, view_or_include[0], *default_kwargs))
        else:
            pattern_list.append(RegexURLPattern(regex, prefix and (prefix + '.' + view_or_include) or view_or_include, *default_kwargs))
    return pattern_list
