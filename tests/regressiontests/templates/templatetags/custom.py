from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

def trim(value, num):
    return value[:num]
trim = stringfilter(trim)

register.filter(trim)

