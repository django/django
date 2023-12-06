from urllib.parse import quote, urljoin
from django import template
from django.apps import apps
from django.utils.encoding import iri_to_uri
from django.utils.html import conditional_escape
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()

class PrefixNode(template.Node):
    """
    A template node for handling prefixes (e.g., static or media URL prefixes).
    """

    def __init__(self, varname=None, name=None):
        if name is None:
            raise template.TemplateSyntaxError("Prefix nodes must be given a name to return.")
        self.varname = varname
        self.name = name

    @classmethod
    def handle_token(cls, parser, token, name):
        """
        Class method to parse prefix node and return a Node.
        """
        tokens = token.contents.split()
        if len(tokens) > 1 and tokens[1] != "as":
            raise template.TemplateSyntaxError("First argument in '%s' must be 'as'" % tokens[0])
        varname = tokens[2] if len(tokens) > 1 else None
        return cls(varname, name)

    @classmethod
    def handle_simple(cls, name):
        """
        Handle simple prefix retrieval.
        """
        return iri_to_uri(getattr(settings, name, ""))

    def render(self, context):
        """
        Render the prefix in the template context.
        """
        prefix = self.handle_simple(self.name)
        if self.varname is None:
            return prefix
        context[self.varname] = prefix
        return ""

@register.tag
def get_static_prefix(parser, token):
    """
    Populate a template variable with the static prefix, settings.STATIC_URL.
    """
    return PrefixNode.handle_token(parser, token, "STATIC_URL")

@register.tag
def get_media_prefix(parser, token):
    """
    Populate a template variable with the media prefix, settings.MEDIA_URL.
    """
    return PrefixNode.handle_token(parser, token, "MEDIA_URL")

class StaticNode(template.Node):
    """
    A template node for handling static file URLs.
    """

    def __init__(self, varname=None, path=None):
        if path is None:
            raise template.TemplateSyntaxError("Static template nodes must be given a path to return.")
        self.path = path
        self.varname = varname

    def url(self, context):
        """
        Get the URL for the static file based on the provided path.
        """
        path = self.path.resolve(context)
        return self.handle_simple(path)

    def render(self, context):
        """
        Render the static file URL in the template context.
        """
        url = self.url(context)
        if context.autoescape:
            url = conditional_escape(url)
        if self.varname is None:
            return url
        context[self.varname] = url
        return ""

    @classmethod
    def handle_simple(cls, path):
        """
        Handle simple static URL generation.
        """
        if apps.is_installed("django.contrib.staticfiles"):
            return staticfiles_storage.url(path)
        else:
            static_url = PrefixNode.handle_simple("STATIC_URL")
            return urljoin(static_url, quote(path))

    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse static node and return a Node.
        """
        bits = token.split_contents()

        if len(bits) < 2:
            raise template.TemplateSyntaxError("'{}' takes at least one argument (path to file)".format(bits[0]))

        path = parser.compile_filter(bits[1])

        if len(bits) >= 2 and bits[-2] == "as":
            varname = bits[3]
        else:
            varname = None

        return cls(varname, path)

@register.tag("static")
def do_static(parser, token):
    """
    Join the given path with the STATIC_URL setting.
    """
    return StaticNode.handle_token(parser, token)

def static(path):
    """
    Given a relative path to a static asset, return the absolute path to the asset.
    """
    return StaticNode.handle_simple(path)


