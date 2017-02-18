from django import template
from django.template.defaulttags import lorem

register = template.Library()

register.tag(lorem)
