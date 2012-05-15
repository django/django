from urlparse import urljoin
from django import template
from django.template.base import kwarg_re, Node, TemplateSyntaxError
from django.utils.encoding import iri_to_uri

register = template.Library()

class PrefixNode(template.Node):

    def __repr__(self):
        return "<PrefixNode for %r>" % self.name

    def __init__(self, varname=None, name=None):
        if name is None:
            raise template.TemplateSyntaxError(
                "Prefix nodes must be given a name to return.")
        self.varname = varname
        self.name = name

    @classmethod
    def handle_token(cls, parser, token, name):
        """
        Class method to parse prefix node and return a Node.
        """
        tokens = token.contents.split()
        if len(tokens) > 1 and tokens[1] != 'as':
            raise template.TemplateSyntaxError(
                "First argument in '%s' must be 'as'" % tokens[0])
        if len(tokens) > 1:
            varname = tokens[2]
        else:
            varname = None
        return cls(varname, name)

    @classmethod
    def handle_simple(cls, name):
        try:
            from django.conf import settings
        except ImportError:
            prefix = ''
        else:
            prefix = iri_to_uri(getattr(settings, name, ''))
        return prefix

    def render(self, context):
        prefix = self.handle_simple(self.name)
        if self.varname is None:
            return prefix
        context[self.varname] = prefix
        return ''

@register.tag
def get_static_prefix(parser, token):
    """
    Populates a template variable with the static prefix,
    ``settings.STATIC_URL``.

    Usage::

        {% get_static_prefix [as varname] %}

    Examples::

        {% get_static_prefix %}
        {% get_static_prefix as static_prefix %}

    """
    return PrefixNode.handle_token(parser, token, "STATIC_URL")

@register.tag
def get_media_prefix(parser, token):
    """
    Populates a template variable with the media prefix,
    ``settings.MEDIA_URL``.

    Usage::

        {% get_media_prefix [as varname] %}

    Examples::

        {% get_media_prefix %}
        {% get_media_prefix as media_prefix %}

    """
    return PrefixNode.handle_token(parser, token, "MEDIA_URL")


class StaticNode(Node):
    def __init__(self, path, asvar):
        self.path = path
        self.asvar = asvar

    def render(self, context):
        from django.core.urlresolvers import reverse, NoReverseMatch
        
        path = self.path.resolve(context)
        url = urljoin(PrefixNode.handle_simple("STATIC_URL"), path)

        if self.asvar:
            context[self.asvar] = url
            return ''
        
        return url


@register.tag
def static(parser, token):
    """
    Joins the given path with the STATIC_URL setting.

    Usage::

        {% static path %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static variable_with_path as varname %}

    """

    bits = token.split_contents()

    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    path = parser.compile_filter(bits[1])
    asvar = None

    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    
    if len(bits) != 2:
        raise TemplateSyntaxError("Too many arguments")

    bit = bits[-1]
    match = kwarg_re.match(bit)
    if not match:
        raise TemplateSyntaxError("Malformed arguments")
    
    name, value = match.groups()
    if name:
        raise TemplateSyntaxError("Malformed arguments, this tag not supports keyword args")
    
    path = parser.compile_filter(value)
    return StaticNode(path, asvar)
