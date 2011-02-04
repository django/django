from django import template

register = template.Library()

@register.tag
def badtag(parser, token):
    raise RuntimeError("I am a bad tag")
