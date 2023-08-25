from django import template

register = template.Library()


@register.simple_tag
def register_link(registered_links, location):
    return registered_links.get(location, [])
