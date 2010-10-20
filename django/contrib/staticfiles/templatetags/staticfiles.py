from django import template
from django.utils.encoding import iri_to_uri

register = template.Library()

class StaticFilesPrefixNode(template.Node):

    def __init__(self, varname=None):
        self.varname = varname

    def render(self, context):
        try:
            from django.conf import settings
        except ImportError:
            prefix = ''
        else:
            prefix = iri_to_uri(settings.STATICFILES_URL)
        if self.varname is None:
            return prefix
        context[self.varname] = prefix
        return ''

@register.tag
def get_staticfiles_prefix(parser, token):
    """
    Populates a template variable with the prefix (settings.STATICFILES_URL).

    Usage::

        {% get_staticfiles_prefix [as varname] %}

    Examples::

        {% get_staticfiles_prefix %}
        {% get_staticfiles_prefix as staticfiles_prefix %}

    """
    tokens = token.contents.split()
    if len(tokens) > 1 and tokens[1] != 'as':
        raise template.TemplateSyntaxError(
            "First argument in '%s' must be 'as'" % tokens[0])
    return StaticFilesPrefixNode(varname=(len(tokens) > 1 and tokens[2] or None))

