from mango import template

register = template.Library()


@register.simple_tag
def go_boom():
    raise Exception('boom')
