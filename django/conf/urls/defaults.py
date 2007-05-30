from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.core.exceptions import ImproperlyConfigured

__all__ = ['handler404', 'handler500', 'include', 'patterns', 'url']

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

include = lambda urlconf_module: [urlconf_module]

def patterns(prefix, *args):
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)
        pattern_list.append(t)
    return pattern_list

def url(regex, view, kwargs=None, name=None, prefix=''):
    if type(view) == list:
        # For include(...) processing.
        return RegexURLResolver(regex, view[0], kwargs)
    else:
        if isinstance(view, basestring):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return RegexURLPattern(regex, view, kwargs, name)

