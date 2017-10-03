from django.template import Library, Node

register = Library()


class EchoNode(Node):
    def __init__(self, contents):
        self.contents = contents

    def render(self, context):
        return ' '.join(self.contents)


@register.tag
@register.tag('other_echo')
def echo(parser, token):
    return EchoNode(token.contents.split()[1:])


@register.filter
def upper(value):
    return value.upper()
