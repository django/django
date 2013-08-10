try:
    from urllib.parse import parse_qsl, urlparse, urlunparse
except ImportError:
    from urlparse import parse_qsl, urlparse, urlunparse

from django import template
from django.contrib.admin.util import quote
from django.core.urlresolvers import resolve, Resolver404
from django.utils.http import urlencode

register = template.Library()


@register.filter
def admin_urlname(value, arg):
    return 'admin:%s_%s_%s' % (value.app_label, value.model_name, arg)


@register.filter
def admin_urlquote(value):
    return quote(value)


@register.simple_tag(takes_context=True)
def add_preserved_filters(context, url, popup=False):
    opts = context.get('opts')
    preserved_filters = context.get('preserved_filters')

    parsed_url = list(urlparse(url))
    parsed_qs = dict(parse_qsl(parsed_url[4]))
    merged_qs = dict()

    if opts and preserved_filters:
        preserved_filters = dict(parse_qsl(preserved_filters))

        try:
            match = resolve(url)
        except Resolver404:
            pass
        else:
            current_url = '%s:%s' % (match.app_name, match.url_name)
            changelist_url = 'admin:%s_%s_changelist' % (opts.app_label, opts.model_name)
            if changelist_url == current_url and '_changelist_filters' in preserved_filters:
                preserved_filters = dict(parse_qsl(preserved_filters['_changelist_filters']))

        merged_qs.update(preserved_filters)

    if popup:
        from django.contrib.admin.options import IS_POPUP_VAR
        merged_qs[IS_POPUP_VAR] = 1

    merged_qs.update(parsed_qs)

    parsed_url[4] = urlencode(merged_qs)
    return urlunparse(parsed_url)
