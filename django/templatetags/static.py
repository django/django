from django import template
from django.utils.encoding import iri_to_uri
from django.utils.six.moves.urllib.parse import urljoin

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
        # token.split_contents() isn't useful here because tags using this method don't accept variable as arguments
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


class StaticNode(template.Node):
    def __init__(self, varname=None, path=None):
        if path is None:
            raise template.TemplateSyntaxError(
                "Static template nodes must be given a path to return.")
        self.path = path
        self.varname = varname

    def url(self, context):
        path = self.path.resolve(context)
        return self.handle_simple(path)

    def render(self, context):
        url = self.url(context)
        if self.varname is None:
            return url
        context[self.varname] = url
        return ''

    @classmethod
    def handle_simple(cls, path):
        return urljoin(PrefixNode.handle_simple("STATIC_URL"), path)

    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse prefix node and return a Node.
        """
        bits = token.split_contents()

        if len(bits) < 2:
            raise template.TemplateSyntaxError(
                "'%s' takes at least one argument (path to file)" % bits[0])

        path = parser.compile_filter(bits[1])

        if len(bits) >= 2 and bits[-2] == 'as':
            varname = bits[3]
        else:
            varname = None

        return cls(varname, path)


@register.tag('static')
def do_static(parser, token):
    """
    Joins the given path with the STATIC_URL setting.

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """
    return StaticNode.handle_token(parser, token)


def static(path):
    return StaticNode.handle_simple(path)
