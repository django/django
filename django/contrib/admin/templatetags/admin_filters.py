from django import template
from django.contrib.admin.options import EMPTY_VALUE_STRING
from django.contrib.admin.utils import display_for_value
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def to_object_display_value(value):
    return display_for_value(str(value), EMPTY_VALUE_STRING)
