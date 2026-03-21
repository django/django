from django import template
from django.contrib.admin.options import EMPTY_VALUE_STRING
from django.contrib.admin.utils import display_for_value
from django.template.defaultfilters import _walk_items, stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ngettext

register = template.Library()


@register.filter
@stringfilter
def to_object_display_value(value):
    return display_for_value(str(value), EMPTY_VALUE_STRING)


@register.filter(is_safe=True, needs_autoescape=True)
def truncated_unordered_list(value, max_items, autoescape=True):
    """
    Render an unordered list, showing at most ``max_items`` items and a
    "...and N more." item at the end.

    Usage::

        {{ deleted_objects|truncated_unordered_list:100 }}
    """

    if max_items is not None:
        max_items = int(max_items)

    if autoescape:
        escaper = conditional_escape
    else:

        def escaper(x):
            return x

    def list_formatter(item_list, tabs=1):
        indent = "\t" * tabs
        output = []
        truncated_count = 0
        for item, children in _walk_items(item_list):
            sublist = ""
            if children:
                sublist = "\n%s<ul>\n%s\n%s</ul>\n%s" % (
                    indent,
                    list_formatter(children, tabs + 1),
                    indent,
                    indent,
                )
            if max_items is not None and len(output) >= max_items:
                truncated_count += 1
            else:
                output.append("%s<li>%s%s</li>" % (indent, escaper(item), sublist))

        if truncated_count > 0:
            msg = ngettext(
                "…and %(count)d more.",
                "…and %(count)d more.",
                truncated_count,
            ) % {"count": truncated_count}
            output.append("%s<li>%s</li>" % (indent, msg))

        return "\n".join(output)

    return mark_safe(list_formatter(value))
