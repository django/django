from django.template import Library
from django.template import defaulttags

register = Library()


@register.tag
def ssi(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return defaulttags.ssi(parser, token)


@register.tag
def url(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return defaulttags.url(parser, token)


@register.tag
def cycle(parser, token):
    """
    This is the future version of `cycle` with auto-escaping.

    By default all strings are escaped.

    If you want to disable auto-escaping of variables you can use::

        {% autoescape off %}
            {% cycle var1 var2 var3 as somecycle %}
        {% autoescape %}

    Or if only some variables should be escaped, you can use::

        {% cycle var1 var2|safe var3|safe  as somecycle %}
    """
    return defaulttags.cycle(parser, token, escape=True)


@register.tag
def firstof(parser, token):
    """
    This is the future version of `firstof` with auto-escaping.

    This is equivalent to::

        {% if var1 %}
            {{ var1 }}
        {% elif var2 %}
            {{ var2 }}
        {% elif var3 %}
            {{ var3 }}
        {% endif %}

    If you want to disable auto-escaping of variables you can use::

        {% autoescape off %}
            {% firstof var1 var2 var3 "<strong>fallback value</strong>" %}
        {% autoescape %}

    Or if only some variables should be escaped, you can use::

        {% firstof var1 var2|safe var3 "<strong>fallback value</strong>"|safe %}

    """
    return defaulttags.firstof(parser, token, escape=True)
