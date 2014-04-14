from django import template
from django.templatetags.static import StaticNode
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


def static(path):
    return staticfiles_storage.url(path)


class StaticFilesNode(StaticNode):

    def url(self, context):
        path = self.path.resolve(context)
        return static(path)


@register.tag('static')
def do_static(parser, token):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """
    return StaticFilesNode.handle_token(parser, token)
