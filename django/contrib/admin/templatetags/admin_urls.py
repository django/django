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
def get_change_url(context, model_admin, object_id):
    if not object_id or model_admin is None:
        return ""
    request = context.get("request")
    return add_preserved_filters(
        context, model_admin.get_change_url(object_id, request=request)
    )


@register.simple_tag(takes_context=True)
def get_delete_url(context, model_admin, object_id):
    if not object_id or model_admin is None:
        return ""
    request = context.get("request")
    return add_preserved_filters(
        context, model_admin.get_delete_url(object_id, request=request)
    )


@register.simple_tag(takes_context=True)
def get_history_url(context, model_admin, object_id):
    if not object_id or model_admin is None:
        return ""
    request = context.get("request")
    return add_preserved_filters(
        context, model_admin.get_history_url(object_id, request=request)
    )


@register.simple_tag(takes_context=True)
def add_preserved_filters(context, url, popup=False, to_field=None):
    opts = context.get("opts")
    preserved_filters = context.get("preserved_filters")
    preserved_qsl = context.get("preserved_qsl")

    parsed_url = list(urlsplit(url))
    parsed_qs = dict(parse_qsl(parsed_url[3]))
    merged_qs = {}

    if preserved_qsl:
        merged_qs.update(preserved_qsl)

    if opts and preserved_filters:
        preserved_filters = dict(parse_qsl(preserved_filters))

        match_url = "/%s" % unquote(url).partition(get_script_prefix())[2]
        try:
            match = resolve(match_url)
        except Resolver404:
            pass
        else:
            current_url = "%s:%s" % (match.app_name, match.url_name)
            changelist_url_name = "admin:%s_%s_changelist" % (
                opts.app_label,
                opts.model_name,
            )
            model_admin = context.get("model_admin") or (
                context.get("cl").model_admin if context.get("cl") else None
            )
            if model_admin:
                request = context.get("request")
                changelist_path = model_admin.get_changelist_url(request=request)
            else:
                changelist_path = None

            is_changelist = (
                current_url == changelist_url_name
                or match.url_name.endswith("_changelist")
                or (changelist_path and unquote(url) == unquote(changelist_path))
            )
            if is_changelist and "_changelist_filters" in preserved_filters:
                preserved_filters = dict(
                    parse_qsl(preserved_filters["_changelist_filters"])
                )

        merged_qs.update(preserved_filters)

    if popup:
        from django.contrib.admin.options import IS_POPUP_VAR

        merged_qs[IS_POPUP_VAR] = 1
    if to_field:
        from django.contrib.admin.options import TO_FIELD_VAR

        merged_qs[TO_FIELD_VAR] = to_field

    merged_qs.update(parsed_qs)

    parsed_url[3] = urlencode(merged_qs)
    return urlunsplit(parsed_url)
