from django.template import Library, Node, TemplateSyntaxError
from django.template import resolve_variable
from django.core.cache import cache
from django.utils.encoding import force_unicode

register = Library()

class CacheNode(Node):
    def __init__(self, nodelist, expire_time, fragment_name, vary_on):
        self.nodelist = nodelist
        self.expire_time = expire_time
        self.fragment_name = fragment_name
        self.vary_on = vary_on

    def render(self, context):
        # Build a unicode key for this fragment and all vary-on's.
        cache_key = u':'.join([self.fragment_name] + \
            [force_unicode(resolve_variable(var, context)) for var in self.vary_on])
        value = cache.get(cache_key)
        if value is None:
            value = self.nodelist.render(context)
            cache.set(cache_key, value, self.expire_time)
        return value

def do_cache(parser, token):
    """
    This will cache the contents of a template fragment for a given amount
    of time.

    Usage::

        {% load cache %}
        {% cache [expire_time] [fragment_name] %}
            .. some expensive processing ..
        {% endcache %}

    This tag also supports varying by a list of arguments::

        {% load cache %}
        {% cache [expire_time] [fragment_name] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endcache %}

    Each unique set of arguments will result in a unique cache entry.
    """
    nodelist = parser.parse(('endcache',))
    parser.delete_first_token()
    tokens = token.contents.split()
    if len(tokens) < 3:
        raise TemplateSyntaxError(u"'%r' tag requires at least 2 arguments." % tokens[0])
    try:
        expire_time = int(tokens[1])
    except ValueError:
        raise TemplateSyntaxError(u"First argument to '%r' must be an integer (got '%s')." % (tokens[0], tokens[1]))
    return CacheNode(nodelist, expire_time, tokens[2], tokens[3:])

register.tag('cache', do_cache)
