from django.core.urlresolvers import RegexURLMultiplePattern, RegexURLPattern

__all__ = ['handler404', 'handler500', 'include', 'patterns']

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

include = lambda urlconf_module: [urlconf_module]

def patterns(prefix, *tuples):
    pattern_list = []
    for t in tuples:
        if type(t[1]) == list:
            pattern_list.append(RegexURLMultiplePattern(t[0], t[1][0]))
        else:
            pattern_list.append(RegexURLPattern(t[0], prefix and (prefix + '.' + t[1]) or t[1], *t[2:]))
    return pattern_list
