import json
from itertools import accumulate
from typing import Mapping

from django.template import Library, TemplateSyntaxError
from django.utils.html import format_html, format_html_join

register = Library()


@register.simple_tag
def importmap(app_name=None, **kwargs):
    if "type" in kwargs:
        raise TemplateSyntaxError(
            "Passing 'type' as an additionnal HTML attribute is disallowed"
        )

    from django.contrib.importmap.base import get_importmaps

    importmaps = get_importmaps()

    def merge(destination, source):
        for key, value in source.items():
            if isinstance(value, Mapping):
                # get node or create one
                node = destination.setdefault(key, {})
                merge(value, node)
            else:
                destination[key] = value

        return destination

    if app_name:
        result = importmaps.get(app_name, {})
    else:
        result = accumulate(importmaps.values(), merge, initial={})

    additionnal_parameters = format_html_join(" ", '{}="{}"', kwargs.items()).strip()
    additionnal_parameters = (
        " %s" % additionnal_parameters if additionnal_parameters else ""
    )
    return format_html(
        '<script type="importmap"{]>{}</script>',
        additionnal_parameters,
        json.dumps(result, indent=4),
    )
