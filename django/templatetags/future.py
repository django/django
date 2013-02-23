from django.template import Library
from django.template.defaulttags import (url as default_url, ssi as default_ssi,
    firstof as default_firstof, cycle as default_cycle)

register = Library()


@register.tag
def ssi(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return default_ssi(parser, token)


@register.tag
def url(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return default_url(parser, token)


@register.tag
def cycle(parser, token):
    """
    This is alternative version of default `cycle` with auto-escaping

    By default all strings are escaped

    ...

    If you want to disable auto-escaping of variables you can use

        {% autoescape off %}
            {% cycle var1 var2 var3 as somecycle %}
        {% autoescape %}

    Or if only some variables should be escaped, you can use

        {% cycle var1 var2|safe var3|safe  as somecycle %}

    """

    return default_cycle(parser, token, escape=True)


@register.tag
def firstof(parser, token):
    """
    This is alternative version of default `cycle` with auto-escaping

    Outputs the first variable passed that is not False, with escaping if
    autoescape is on and variable is not marked as safe already.

    ...

    This is equivalent to:

       {% if var1 %}
           {{ var1 }}
       {% else %}{% if var2 %}
           {{ var2 }}
       {% else %}{% if var3 %}
           {{ var3 }}
       {% endif %}{% endif %}{% endif %}

    ...

    If you want to disable auto-escaping of variables you can use

        {% autoescape off %}
            {% firstof var1 var2 var3 "<strong>fallback value</strong>" %}
        {% autoescape %}

    Or if only some variables should be escaped, you can use

        {% firstof var1 var2|safe var3 "<strong>fallback value</strong>"|safe %}

    """

    return default_firstof(parser, token, escape=True)
