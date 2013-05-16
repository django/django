from django import template
from django.contrib.admin.util import quote

register = template.Library()

@register.filter
def admin_urlname(value, arg):
    return 'admin:%s_%s_%s' % (value.app_label, value.model_name, arg)


@register.filter
def admin_urlquote(value):
    return quote(value)
