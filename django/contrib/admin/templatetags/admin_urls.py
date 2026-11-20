from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

from django import template
from django.contrib.admin.utils import quote
from django.urls import Resolver404, get_script_prefix, resolve
from django.utils.http import urlencode

register = template.Library()


@register.filter
def admin_urlname(value, arg):
    return "admin:%s_%s_%s" % (value.app_label, value.model_name, arg)


@register.filter
def admin_urlquote(value):
    return quote(value)


@register.simple_tag(takes_context=True)
def add_preserved_filters(context, url, popup=False, to_field=None):
    opts = context.get("opts")
    preserved_filters = context.get("preserved_filters")
    preserved_qsl = context.get("preserved_qsl")

    parsed_url = list(urlsplit(url))
    parsed_qsl = parse_qsl(parsed_url[3])
    merged_qsl = []

    def merge_qsl(query_pairs):
        query_pairs = list(query_pairs)
        query_keys = {key for key, _ in query_pairs}
        merged_qsl[:] = [pair for pair in merged_qsl if pair[0] not in query_keys]
        merged_qsl.extend(query_pairs)

    if preserved_qsl:
        merge_qsl(preserved_qsl)

    if opts and preserved_filters:
        preserved_qsl = parse_qsl(preserved_filters)

        match_url = "/%s" % unquote(url).partition(get_script_prefix())[2]
        try:
            match = resolve(match_url)
        except Resolver404:
            pass
        else:
            current_url = "%s:%s" % (match.app_name, match.url_name)
            changelist_url = "admin:%s_%s_changelist" % (
                opts.app_label,
                opts.model_name,
            )
            if changelist_url == current_url:
                for key, value in reversed(preserved_qsl):
                    if key == "_changelist_filters":
                        preserved_qsl = parse_qsl(value)
                        break

        merge_qsl(preserved_qsl)

    if popup:
        from django.contrib.admin.options import IS_POPUP_VAR

        merge_qsl([(IS_POPUP_VAR, 1)])
    if to_field:
        from django.contrib.admin.options import TO_FIELD_VAR

        merge_qsl([(TO_FIELD_VAR, to_field)])

    merge_qsl(parsed_qsl)

    parsed_url[3] = urlencode(merged_qsl)
    return urlunsplit(parsed_url)
