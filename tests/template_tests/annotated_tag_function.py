from django import template

register = template.Library()


@register.simple_tag()
def annotated_tag_function(val: int):
    return val
