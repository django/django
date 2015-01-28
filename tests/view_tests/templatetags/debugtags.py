from django import template

from ..views import BrokenException

register = template.Library()


@register.simple_tag
def go_boom(arg):
    raise BrokenException(arg)
