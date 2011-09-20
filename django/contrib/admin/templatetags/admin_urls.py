from django.core.urlresolvers import reverse, NoReverseMatch
from django import template

register = template.Library()

@register.filter
def admin_urlname(value, arg):
    return 'admin:%s_%s_%s' % (value.app_label, value.module_name, arg)
