from django import template

register = template.Library()


@register.tag
def badtag(parser, token):
    parser.parse(('endbadtag',))
    parser.delete_first_token()
    return BadNode()


class BadNode(template.Node):
    def render(self, context):
        raise template.TemplateSyntaxError('error')
